import logging

import pytest


@pytest.fixture()
def cmake_build(shared_datadir):
    from subprocess import run
    source = shared_datadir / 'cmake'
    build = source / 'build'
    build.mkdir()
    p = run(['cmake', '-S', source, '-B', build],
            check=True,
            capture_output=True,
            universal_newlines=True)
    logging.debug(p.stdout)
    logging.debug(p.stderr)
    yield build
