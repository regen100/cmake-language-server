import pytest


@pytest.fixture()
def cmake_build(shared_datadir):
    from subprocess import run, PIPE
    source = shared_datadir / 'cmake'
    build = source / 'build'
    build.mkdir()
    p = run(['cmake', str(source)],
            cwd=build,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True)
    if p.returncode != 0:
        import logging
        import os
        import pprint
        logging.error('env:\n' + pprint.pformat(os.environ))
        logging.error('stdout:\n' + p.stdout)
        logging.error('stderr:\n' + p.stderr)
        raise RuntimeError("CMake failed")
    yield build
