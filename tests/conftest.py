import pytest


@pytest.fixture()
def cmake_build(shared_datadir):
    from subprocess import run, PIPE
    source = shared_datadir / 'cmake'
    build = source / 'build'
    build.mkdir()
    run(['cmake', source],
        check=True,
        cwd=build,
        stdout=PIPE,
        stderr=PIPE,
        universal_newlines=True)
    yield build
