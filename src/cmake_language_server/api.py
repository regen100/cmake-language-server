import json
import logging
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Pattern

logger = logging.getLogger(__name__)


def _tidy_doc(doc: str) -> str:
    doc = doc.strip()
    doc = re.sub(r':.+?:`(.+?)`', r'\1', doc)
    doc = re.sub(r'``([^`]+)``', r'`\1`', doc)
    doc = doc.replace('\n', ' ')
    doc = doc.replace('.  ', '. ')
    return doc


class API(object):
    _cmake: str
    _build: Path
    _uuid: uuid.UUID
    _builtin_commands: Dict[str, str]
    _builtin_variables: Dict[str, str]
    _builtin_variable_template: Dict[Pattern, str]
    _builtin_modules: Dict[str, str]
    _targets: List[str]
    _cached_variables: Dict[str, str]
    _generated_list_parsed: bool

    def __init__(self, cmake: str, build: Path):
        self._cmake = cmake
        self._build = Path(build)
        self._uuid = uuid.uuid4()

        self._builtin_commands = {}
        self._builtin_variables = {}
        self._builtin_variable_template = {}
        self._builtin_modules = {}
        self._targets = []
        self._cached_variables = {}
        self._generated_list_parsed = False

    def query(self) -> bool:
        if not self.cmake_cache.exists():
            return False

        self.query_json.parent.mkdir(parents=True, exist_ok=True)
        with self.query_json.open('w') as fp:
            fp.write('''\
{
  "requests": [
    {"kind": "codemodel", "version": 2},
    {"kind": "cache", "version": 2},
    {"kind": "cmakeFiles", "version": 1}
  ]
}''')

        proc = subprocess.run([self._cmake, str(self._build)],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              encoding='utf-8',
                              universal_newlines=True)
        self.query_json.unlink()
        self.query_json.parent.rmdir()
        if proc.returncode != 0:
            logging.error(
                f'cmake exited with {proc.returncode}: {proc.stderr}')
            return False

        return True

    def read_reply(self) -> bool:
        reply = self._build / '.cmake' / 'api' / 'v1' / 'reply'
        indices = sorted(reply.glob('index-*.json'))
        if not indices:
            logger.error('no reply')
            return False
        with indices[-1].open() as fp:
            index = json.load(fp)
        try:
            responses = index['reply'][f'client-{self._uuid}']['query.json'][
                'responses']
        except KeyError:
            logger.error('no rensponse')
            return False
        for response in responses:
            if response['kind'] == 'codemodel':
                self._read_codemodel(reply / response['jsonFile'])
            elif response['kind'] == 'cache':
                self._read_cache(reply / response['jsonFile'])
            elif response['kind'] == 'cmakeFiles':
                self._read_cmake_files(reply / response['jsonFile'])

        return True

    def _read_codemodel(self, codemodelpath: Path):
        with (codemodelpath).open() as fp:
            codemodel = json.load(fp)
        config = codemodel['configurations'][0]
        self._targets[:] = [x['name'] for x in config['targets']]

    def _read_cache(self, cachepath: Path):
        with cachepath.open() as fp:
            cache = json.load(fp)
        self._cached_variables.clear()
        for entry in cache['entries']:
            name = entry['name']
            value = self._truncate_variable(entry['value'])
            properties = {x['name']: x['value'] for x in entry['properties']}
            helpstring = properties.get('HELPSTRING', '')
            doc = []
            if helpstring:
                doc.append(helpstring)
            if value:
                doc.append(f'`{value}`')
            self._cached_variables[name] = '\n\n'.join(doc)

    def _read_cmake_files(self, jsonpath: Path):
        '''inspect generated list files'''

        if not self._builtin_variables or self._generated_list_parsed:
            return

        with jsonpath.open() as fp:
            cmake_files = json.load(fp)

        # inspect generated list files
        with tempfile.TemporaryDirectory() as tmpdirname:
            tmplist = Path(tmpdirname) / 'dump.cmake'
            with tmplist.open('w') as fp:
                for listfile in cmake_files['inputs']:
                    if not listfile.get('isGenerated', False):
                        continue
                    path = listfile['path']
                    fp.write(f'include({path})\n')
                fp.write('''
get_cmake_property(variables VARIABLES)
foreach (variable ${variables})
  message("${variable}=${${variable}}")
endforeach()
''')
            p = subprocess.run(
                [self._cmake, '-P', str(tmplist)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cmake_files['paths']['source'],
                encoding='utf-8',
                universal_newlines=True)
            if p.returncode != 0:
                return

            for line in p.stderr.split('\n'):
                line = line.strip()
                if not line:
                    continue
                k, v = line.split('=', 1)
                if k.startswith('CMAKE_ARG'):
                    continue
                v = self._truncate_variable(v)
                if k in self._builtin_variables:
                    self._builtin_variables[k] += f'\n\n`{v}`'
                else:
                    for pattern, doc in self._builtin_variable_template.items(
                    ):
                        if pattern.fullmatch(k):
                            self._builtin_variables[k] = f'{doc}\n\n`{v}`'
                            break
                    else:
                        # ignore variable with no document
                        pass

        self._generated_list_parsed = True

    @property
    def query_json(self) -> Path:
        return (self._build / '.cmake' / 'api' / 'v1' / 'query' /
                f'client-{self._uuid}' / 'query.json')

    @property
    def cmake_cache(self) -> Path:
        return self._build / 'CMakeCache.txt'

    def parse_doc(self) -> None:
        self._parse_commands()
        self._parse_variables()
        self._parse_modules()

    def _parse_commands(self) -> None:
        p = subprocess.run([self._cmake, '--help-commands'],
                           stdout=subprocess.PIPE,
                           encoding='utf-8',
                           universal_newlines=True)

        if p.returncode != 0:
            return

        matches = re.finditer(
            r'''
(?P<command>.+)\n
-+\n+?
[\s\S]*?
(?P<signature>(?P=command)\s*\([^)]*\))
''', p.stdout, re.VERBOSE)
        self._builtin_commands.clear()
        for match in matches:
            command = match.group('command')
            signature = match.group('signature')
            signature = re.sub(r'^ ', r'', signature, flags=re.MULTILINE)
            self._builtin_commands[
                command] = '```cmake\n' + signature + '\n```'

    def _parse_variables(self) -> None:
        p = subprocess.run([self._cmake, '--help-variables'],
                           stdout=subprocess.PIPE,
                           encoding='utf-8',
                           universal_newlines=True)

        if p.returncode != 0:
            return

        matches = re.finditer(
            r'''
(?P<variable>.+)\n
-+\n\n
(?P<doc>[\s\S]+?)(?:\n\n|$)
''', p.stdout, re.VERBOSE)
        self._builtin_variables.clear()
        for match in matches:
            variable = match.group('variable')
            doc = _tidy_doc(match.group('doc'))
            if variable == 'CMAKE_MATCH_<n>':
                for i in range(10):
                    self._builtin_variables[f'CMAKE_MATCH_{i}'] = doc
            elif '<' in variable:
                variable = re.sub(r'<[^>]+>', r'[^_]+', variable)
                pattern = re.compile(variable)
                self._builtin_variable_template[pattern] = doc
            else:
                self._builtin_variables[variable] = doc

    def _parse_modules(self) -> None:
        p = subprocess.run([self._cmake, '--help-modules'],
                           stdout=subprocess.PIPE,
                           encoding='utf-8',
                           universal_newlines=True)

        if p.returncode != 0:
            return

        matches = re.finditer(
            r'''
(?P<module>.+)\n
-+\n+?
(?:(?P<header>\w[\w\s]+)\n\^+\n+?)?
(?P<doc>.(?:.|\n)+?\n\n)
''', p.stdout + '\n\n', re.VERBOSE)
        self._builtin_modules.clear()
        for match in matches:
            module = match.group('module')
            header = match.group('header')
            doc = _tidy_doc(match.group('doc'))
            if header is not None and header != 'Overview':
                doc = ''
            self._builtin_modules[module] = doc

    def get_command_doc(self, command: str) -> Optional[str]:
        return self._builtin_commands.get(command)

    def search_command(self, command: str) -> List[str]:
        command = command.lower()
        return [x for x in self._builtin_commands if x.startswith(command)]

    def get_variable_doc(self, variable: str) -> Optional[str]:
        doc = self._cached_variables.get(variable)
        if doc:
            return doc
        return self._builtin_variables.get(variable)

    def search_variable(self, variable: str) -> List[str]:
        cached = frozenset(x for x in self._cached_variables
                           if x.startswith(variable))
        builtin = frozenset(x for x in self._builtin_variables
                            if x.startswith(variable))
        return list(cached | builtin)

    def get_module_doc(self, module: str, package: bool) -> Optional[str]:
        if package:
            return self._builtin_modules.get('Find' + module)

        return self._builtin_modules.get(module)

    def search_module(self, module: str, package: bool) -> List[str]:
        if package:
            module = 'Find' + module
            return [
                x[4:] for x in self._builtin_modules if x.startswith(module)
            ]

        return [
            x for x in self._builtin_modules
            if x.startswith(module) and not x.startswith('Find')
        ]

    def search_target(self, target: str) -> List[str]:
        return [x for x in self._targets if x.startswith(target)]

    def _truncate_variable(self, v: str) -> str:
        width = 70
        return v[:width] + (v[width:] and '...')
