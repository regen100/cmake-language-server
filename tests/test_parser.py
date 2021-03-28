from typing import Callable, List

from cmake_language_server.parser import ListParser, TokenType


def make_parser_test(
    liststr: str, expect_token: List[TokenType], expect_remain: str = ""
) -> Callable[[], None]:
    def test() -> None:
        actual_token, actual_remain = ListParser().parse(liststr)
        assert actual_token == expect_token
        assert actual_remain == expect_remain

    return test


test_command_no_args = make_parser_test("a()", [("a", [])])
test_command_space = make_parser_test(" a ()", [" ", ("a", [])])
test_command_arg = make_parser_test("a(b)", [("a", ["b"])])
test_command_arg_space = make_parser_test("a ( b )", [("a", ["b"])])
test_command_arg_escape = make_parser_test(r"a(\n\")", [("a", [r"\n\""])])
test_command_arg_paren = make_parser_test("a((b))", [("a", ["(", "b", ")"])])
test_command_arg_paren_paren = make_parser_test(
    "a(((b)))", [("a", ["(", "(", "b", ")", ")"])]
)
test_command_arg_quote = make_parser_test(r'a("b\"")', [("a", [r'"b\""'])])
test_command_arg_quote_cont = make_parser_test('a("\\\n")', [("a", ['"\\\n"'])])
test_command_arg_quo_multiline = make_parser_test(
    """a("b
c
")""",
    [("a", ['"b\nc\n"'])],
)
test_command_arg_bracket_0 = make_parser_test("a([[b]])", [("a", ["[[b]]"])])
test_command_arg_bracket_1 = make_parser_test("a([=[b]=])", [("a", ["[=[b]=]"])])
test_command_arg_space = make_parser_test("a ( b )", [("a", [" ", "b", " "])])
test_command_arg_multi = make_parser_test("a(b c)", [("a", ["b", " ", "c"])])
test_command_multielement = make_parser_test(
    """a(
  b
  c  # c
)""",
    [("a", ["\n", "  ", "b", "\n", "  ", "c", "  ", "# c", "\n"])],
)
test_line_comment = make_parser_test("a() # b # c", [("a", []), " ", "# b # c"])
test_bracket_comment = make_parser_test("#[[a]]#[[b]]", ["#[[a]]", "#[[b]]"])
test_bracket_comment_nested = make_parser_test("#[=[[[a]]]=]", ["#[=[[[a]]]=]"])
test_bracket_comment_multiline = make_parser_test(
    "#[[\na\nb\nc\n]]", ["#[[\na\nb\nc\n]]"]
)
test_if_block = make_parser_test(
    """if()
  a()
else()
  b()
endif()""",
    [
        ("if", []),
        "\n",
        "  ",
        ("a", []),
        "\n",
        ("else", []),
        "\n",
        "  ",
        ("b", []),
        "\n",
        ("endif", []),
    ],
)
test_comment_multi_linecomment = make_parser_test(
    """a()# a
b() # b
c()  # c""",
    [("a", []), "# a", "\n", ("b", []), " ", "# b", "\n", ("c", []), "  ", "# c"],
)

test_incomplete_id = make_parser_test("a", [], "a")
test_incomplete_command = make_parser_test("a(", [], "a(")
test_incomplete_id_after_command = make_parser_test("a()\nb", [("a", []), "\n"], "b")
test_incomplete_command_after_command = make_parser_test(
    "a()\nb(c", [("a", []), "\n"], "b(c"
)
