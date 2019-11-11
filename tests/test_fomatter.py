from cmake_language_server.formatter import Formatter
from cmake_language_server.parser import ListParser


def make_formatter_test(liststr: str, expect: str):
    def test():
        tokens, remain = ListParser().parse(liststr)
        actual = Formatter().format(tokens)
        assert actual == expect

    return test


test_command = make_formatter_test('a()', 'a()\n')
test_command_tolower = make_formatter_test('A()', 'a()\n')
test_remove_space = make_formatter_test('''
  #a
  b ( c )  # d
''', '''\
#a
b(c)  # d
''')
test_indent_if = make_formatter_test(
    '''
if()
a()  # a
 else()
# b
b()
endif()
''', '''\
if()
  a()  # a
else()
  # b
  b()
endif()
''')
test_indent_if_nested = make_formatter_test(
    '''
if()
if()
a()
b()
endif()
endif()
''', '''\
if()
  if()
    a()
    b()
  endif()
endif()
''')
test_argument = make_formatter_test('a( b c  d)', 'a(b c d)\n')
test_argument_multiline = make_formatter_test(
    '''
if()
a(b c
d  # e
f
# g
)  # h
endif()
''', '''\
if()
  a(
    b c
    d  # e
    f
    # g
  )  # h
endif()
''')
