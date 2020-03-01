from typing import List

from .parser import TokenList


class Formatter(object):
    indnt: str
    lower_identifier: bool

    def __init__(self, indent='  ', lower_identifier=True):
        self.indent = indent
        self.lower_identifier = lower_identifier

    def format(self, tokens: TokenList) -> str:
        cmds: List[str] = ['']
        indnet_level = 0
        for token in tokens:
            if isinstance(token, tuple):
                raw_identifier = token[0]
                identifier = raw_identifier.lower()
                if identifier in ('elseif', 'else', 'endif', 'endforeach',
                                  'endwhile', 'endmacro', 'endfunction'):
                    if indnet_level > 0:
                        indnet_level -= 1
                cmds[-1] = self.indent * indnet_level
                cmds[-1] += (identifier
                             if self.lower_identifier else raw_identifier)
                args = self._format_args(token[1])
                if len(args) < 2:
                    cmds[-1] += '(' + ''.join(args) + ')'
                else:
                    cmds[-1] += '(\n'
                    for arg in args:
                        cmds[-1] += self.indent * (indnet_level +
                                                   1) + arg + '\n'
                    cmds[-1] += self.indent * indnet_level + ')'
                if identifier in ('if', 'elseif', 'else', 'foreach', 'while',
                                  'macro', 'function'):
                    indnet_level += 1
            elif token == '\n':
                cmds.append('')
            elif token[0] == '#':
                if cmds[-1]:
                    cmds[-1] += token
                else:
                    cmds[-1] = self.indent * indnet_level + token
            elif cmds[-1]:
                cmds[-1] += token

        cmds = self._strip_line(cmds)
        return '\n'.join(cmds) + '\n'

    def _format_args(self, args: List[str]) -> List[str]:
        lines = ['']
        for i in range(len(args)):
            arg = args[i]
            if arg[0] == '#':
                lines[-1] += arg
            elif arg[0] == '\n':
                lines.append('')
            elif arg.isspace():
                if lines[-1]:
                    if i + 1 < len(args) and args[i + 1][0] == '#':
                        lines[-1] += arg
                    else:
                        lines[-1] += ' '
            else:
                lines[-1] += arg

        return self._strip_line(lines)

    def _strip_line(self, lines: List[str]) -> List[str]:
        '''Delete empty lines at the start/end of the input'''

        ret: List[str] = []
        for line in lines:
            line = line.rstrip()
            if line != '' or len(ret) > 0:
                ret.append(line)
        while ret and ret[-1] == '':
            del ret[-1]
        return ret


def main(args: List[str] = None):
    from argparse import ArgumentParser
    from difflib import unified_diff
    from pathlib import Path
    import sys
    from . import __version__
    from .parser import ListParser

    parser = ArgumentParser(
        description='Format CMake list files.',
        epilog='''
            If no arguments are specified, it formats the code from
            standard input and writes the result to the standard output.''',
    )
    parser.add_argument('lists', type=Path, nargs='*', help='CMake list files')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-i',
                       '--inplace',
                       action='store_true',
                       help='inplace edit')
    group.add_argument('-d', '--diff', action='store_true', help='show diff')
    parser.add_argument('--version',
                        action='version',
                        version=f'%(prog)s {__version__}')

    args = parser.parse_args(args)

    if not args.lists and args.inplace:
        print('error: cannot use -i when no arguments are specified.',
              file=sys.stderr)
        return
    if not args.lists:
        args.lists.append(None)

    list_parser = ListParser()
    formatter = Formatter()
    for listpath in args.lists:
        if listpath is None:
            listpath = '(stdin)'
            content = sys.stdin.read()
        else:
            with listpath.open() as fp:
                content = fp.read()
        tokens, remain = list_parser.parse(content)
        formatted = content if remain else formatter.format(tokens)

        if args.inplace:
            if not remain:
                with listpath.open('w') as fp:
                    fp.write(formatted)
        elif args.diff:
            diff = unified_diff(content.splitlines(True),
                                formatted.splitlines(True), str(listpath),
                                str(listpath), '(before formatting)',
                                '(after formatting)')
            diffstr = ''.join(diff)
            print(diffstr, end='')
        else:
            print(formatted, end='')
