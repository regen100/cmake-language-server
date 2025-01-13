import subprocess
from pathlib import Path

from cmake_language_server.api import API


def test_query_with_cache(cmake_build: Path) -> None:
    api = API("cmake", cmake_build, "cmake-format", [])
    assert api.query()

    query = cmake_build / ".cmake" / "api" / "v1" / "query"
    assert query.exists()

    reply = cmake_build / ".cmake" / "api" / "v1" / "reply"
    assert reply.exists()


def test_query_without_cache(cmake_build: Path) -> None:
    api = API("cmake", cmake_build, "cmake-format", [])
    (cmake_build / "CMakeCache.txt").unlink()

    assert not api.query()


def test_read_variable(cmake_build: Path) -> None:
    api = API("cmake", cmake_build, "cmake-format", [])
    assert api.query()
    assert api.read_reply()

    assert api.get_variable_doc("testproject_BINARY_DIR")


def test_read_cmake_files(cmake_build: Path) -> None:
    api = API("cmake", cmake_build, "cmake-format", [])
    api.parse_doc()
    assert api.query()
    api.read_reply()

    import platform

    system = platform.system()
    cxx = api.get_variable_doc("CMAKE_CXX_COMPILER_ID")
    assert cxx is not None
    if system == "Linux":
        assert "GNU" in cxx
    elif system == "Windows":
        assert "MSVC" in cxx
    elif system == "Darwin":
        assert "Clang" in cxx
    else:
        raise RuntimeError("Unexpected system")


def test_parse_commands(cmake_build: Path) -> None:
    api = API("cmake", cmake_build, "cmake-format", [])
    api.parse_doc()

    p = subprocess.run(
        ["cmake", "--help-command-list"],
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    commands = p.stdout.strip().split("\n")

    for command in commands:
        assert api.get_command_doc(command) is not None, f"{command} not found"

    break_doc = api.get_command_doc("break")
    assert break_doc is not None and "break()" in break_doc
    assert api.get_command_doc("not_existing_command") is None


def test_parse_variables(cmake_build: Path) -> None:
    api = API("cmake", cmake_build, "cmake-format", [])
    api.parse_doc()

    p = subprocess.run(
        ["cmake", "--help-variable-list"],
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    variables = p.stdout.strip().split("\n")

    for variable in variables:
        if "<" in variable:
            continue
        assert api.get_variable_doc(variable) is not None, f"{variable} not found"

    assert api.get_variable_doc("BUILD_SHARED_LIBS") is not None
    assert api.get_variable_doc("not_existing_variable") is None


def test_parse_modules(cmake_build: Path) -> None:
    api = API("cmake", cmake_build, "cmake-format", [])
    api.parse_doc()

    p = subprocess.run(
        ["cmake", "--help-module-list"],
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    modules = p.stdout.strip().split("\n")

    for module in modules:
        if module.startswith("Find"):
            assert (
                api.get_module_doc(module[4:], True) is not None
            ), f"{module} not found"
        else:
            assert api.get_module_doc(module, False) is not None, f"{module} not found"

    assert api.get_module_doc("GoogleTest", False) is not None
    assert api.get_module_doc("GoogleTest", True) is None
    assert api.search_module("GoogleTest", False) == ["GoogleTest"]
    assert api.search_module("GoogleTest", True) == []
    assert api.get_module_doc("Boost", False) is None
    assert api.get_module_doc("Boost", True) is not None
    assert api.search_module("Boost", False) == []
    assert api.search_module("Boost", True) == ["Boost"]
