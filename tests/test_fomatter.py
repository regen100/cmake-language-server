import sys
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Callable, Iterator

from cmake_language_server.formatter import Formatter, main
from cmake_language_server.parser import ListParser
from pytest import CaptureFixture


def make_formatter_test(liststr: str, expect: str) -> Callable[[], None]:
    def test() -> None:
        tokens, remain = ListParser().parse(liststr)
        actual = Formatter().format(tokens)
        assert actual == expect

    return test


test_command = make_formatter_test("a()", "a()\n")
test_command_tolower = make_formatter_test("A()", "a()\n")
test_remove_space = make_formatter_test(
    """
  #a
  b ( c )  # d
""",
    """\
#a
b(c)  # d
""",
)
test_indent_if = make_formatter_test(
    """
if()
a()  # a
 else()
# b
b()
endif()
""",
    """\
if()
  a()  # a
else()
  # b
  b()
endif()
""",
)
test_indent_if_nested = make_formatter_test(
    """
if()
if()
a()
b()
endif()
endif()
""",
    """\
if()
  if()
    a()
    b()
  endif()
endif()
""",
)
test_argument = make_formatter_test("a( b c  d)", "a(b c d)\n")
test_argument_multiline = make_formatter_test(
    """
if()
a(b c
d  # e
f
# g
)  # h
endif()
""",
    """\
if()
  a(
    b c
    d  # e
    f
    # g
  )  # h
endif()
""",
)


@contextmanager
def mock_stdin(buf: str) -> Iterator[None]:
    stdin = sys.stdin
    sys.stdin = StringIO(buf)
    yield
    sys.stdin = stdin


def test_main_stdin(capsys: CaptureFixture[str]) -> None:
    with mock_stdin(" a()"):
        main([])
    captured = capsys.readouterr()
    assert captured.out == "a()\n"
    assert captured.err == ""


def test_main_stdin_diff(capsys: CaptureFixture[str]) -> None:
    with mock_stdin(" a()"):
        main(["-d"])
    captured = capsys.readouterr()
    assert "- a()" in captured.out
    assert "+a()" in captured.out
    assert captured.err == ""


def test_main_file_1(capsys: CaptureFixture[str], tmp_path: Path) -> None:
    testfile1 = tmp_path / "list1.cmake"
    with testfile1.open("w") as fp:
        fp.write(" a()")

    main([str(testfile1)])
    captured = capsys.readouterr()
    assert captured.out == "a()\n"
    assert captured.err == ""


def test_main_file_2(capsys: CaptureFixture[str], tmp_path: Path) -> None:
    testfile1 = tmp_path / "list1.cmake"
    with testfile1.open("w") as fp:
        fp.write(" a()")
    testfile2 = tmp_path / "list2.cmake"
    with testfile2.open("w") as fp:
        fp.write(" b()")

    main([str(testfile1), str(testfile2)])
    captured = capsys.readouterr()
    assert captured.out == "a()\nb()\n"
    assert captured.err == ""


def test_main_inplace(capsys: CaptureFixture[str], tmp_path: Path) -> None:
    testfile1 = tmp_path / "list1.cmake"
    with testfile1.open("w") as fp:
        fp.write(" a()")

    main(["-i", str(testfile1)])
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    with testfile1.open() as fp:
        content = fp.read()
    assert content == "a()\n"


def test_main_diff(capsys: CaptureFixture[str], tmp_path: Path) -> None:
    testfile1 = tmp_path / "list1.cmake"
    with testfile1.open("w") as fp:
        fp.write(" a()")

    main(["-d", str(testfile1)])
    captured = capsys.readouterr()
    assert str(testfile1) in captured.out
    assert "- a()" in captured.out
    assert "+a()" in captured.out
    assert captured.err == ""
