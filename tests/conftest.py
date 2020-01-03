import asyncio
import logging
import os
import pprint
from subprocess import PIPE, run
from threading import Thread

import pytest
from pygls import features
from pygls.server import LanguageServer

from cmake_language_server.server import CMakeLanguageServer


@pytest.fixture()
def cmake_build(shared_datadir):
    source = shared_datadir / 'cmake'
    build = source / 'build'
    build.mkdir()
    p = run(['cmake', str(source)],
            cwd=build,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True)
    if p.returncode != 0:
        logging.error('env:\n' + pprint.pformat(os.environ))
        logging.error('stdout:\n' + p.stdout)
        logging.error('stderr:\n' + p.stderr)
        raise RuntimeError("CMake failed")
    yield build


@pytest.fixture()
def client_server():
    c2s_r, c2s_w = os.pipe()
    s2c_r, s2c_w = os.pipe()

    def start(ls: LanguageServer, fdr, fdw):
        # TODO: better patch is needed
        # disable `close()` to avoid error messages
        close = ls.loop.close
        ls.loop.close = lambda: None
        ls.start_io(os.fdopen(fdr, 'rb'), os.fdopen(fdw, 'wb'))
        ls.loop.close = close

    server = CMakeLanguageServer(asyncio.new_event_loop())
    server_thread = Thread(target=start, args=(server, c2s_r, s2c_w))
    server_thread.start()

    client = LanguageServer(asyncio.new_event_loop())
    client_thread = Thread(target=start, args=(client, s2c_r, c2s_w))
    client_thread.start()

    yield client, server

    client.send_notification(features.EXIT)
    server.send_notification(features.EXIT)
    server_thread.join()
    client_thread.join()
