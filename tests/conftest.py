import logging
import os
from pathlib import Path
from subprocess import PIPE, run
from threading import Thread
from typing import Iterable, Tuple

import pytest
from lsprotocol.types import EXIT, SHUTDOWN
from pygls.lsp.server import LanguageServer

from cmake_language_server.server import CMakeLanguageServer


@pytest.fixture()
def cmake_build(shared_datadir: Path) -> Iterable[Path]:
    source = shared_datadir / "cmake"
    build = source / "build"
    build.mkdir()
    p = run(
        ["cmake", str(source)],
        cwd=build,
        stdout=PIPE,
        stderr=PIPE,
        universal_newlines=True,
    )
    if p.returncode != 0:
        logging.error("stdout:\n" + p.stdout)
        logging.error("stderr:\n" + p.stderr)
        raise RuntimeError("CMake failed")
    yield build


@pytest.fixture()
def client_server() -> Iterable[Tuple[LanguageServer, CMakeLanguageServer]]:
    c2s_r, c2s_w = os.pipe()
    s2c_r, s2c_w = os.pipe()

    def start(ls: LanguageServer, fdr: int, fdw: int) -> None:
        # start_io type hints seem to be wrong?
        ls.start_io(os.fdopen(fdr, "rb"), os.fdopen(fdw, "wb"))  # type:ignore[arg-type]

    server = CMakeLanguageServer("server", "v1")
    server_thread = Thread(target=start, args=(server, c2s_r, s2c_w))
    server_thread.start()

    client = LanguageServer("client", "v1")
    client_thread = Thread(target=start, args=(client, s2c_r, c2s_w))
    client_thread.start()

    yield client, server

    # fix bug on python 3.7
    if hasattr(client.loop, "_signal_handlers"):
        client.loop._signal_handlers.clear()

    client.lsp.send_request(SHUTDOWN)  # type:ignore[no-untyped-call]
    client.lsp.notify(EXIT)
    client_thread.join()
    server_thread.join()
