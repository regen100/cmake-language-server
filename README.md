# cmake-language-server
[![PyPI](https://img.shields.io/pypi/v/cmake-language-server)](https://pypi.org/project/cmake-language-server)
[![AUR version](https://img.shields.io/aur/version/cmake-language-server)](https://aur.archlinux.org/packages/cmake-language-server/)
[![GitHub Actions (Tests)](https://github.com/regen100/cmake-language-server/workflows/Tests/badge.svg)](https://github.com/regen100/cmake-language-server/actions)
[![codecov](https://codecov.io/gh/regen100/cmake-language-server/branch/master/graph/badge.svg)](https://codecov.io/gh/regen100/cmake-language-server)
[![GitHub](https://img.shields.io/github/license/regen100/cmake-language-server)](https://github.com/regen100/cmake-language-server/blob/master/LICENSE)

CMake LSP Implementation.

Alpha Stage, work in progress.

## Features
- [x] Builtin command completion
- [x] Documentation for commands and variables on hover
- [x] Formatting

## Commands

- `cmake-language-server`: LSP server
- `cmake-format`: CLI frontend for formatting

## Installation

```bash
$ pip install cmake-language-server
```

### Tested Clients

- Neovim ([neoclide/coc.nvim][coc.nvim], [prabirshrestha/vim-lsp][vim-lsp])

#### Neovim

##### coc.nvim

```jsonc
  "languageserver": {
    "cmake": {
      "command": "cmake-language-server",
      "filetypes": ["cmake"],
      "rootPatterns": [
        "build/"
      ],
      "initializationOptions": {
        "buildDirectory": "build"
      }
    }
  }
```

##### vim-lsp

```vim
if executable('cmake-language-server')
  au User lsp_setup call lsp#register_server({
  \ 'name': 'cmake',
  \ 'cmd': {server_info->['cmake-language-server']},
  \ 'root_uri': {server_info->lsp#utils#path_to_uri(lsp#utils#find_nearest_parent_file_directory(lsp#utils#get_buffer_path(), 'build/'))},
  \ 'whitelist': ['cmake'],
  \ 'initialization_options': {
  \   'buildDirectory': 'build',
  \ }
  \})
endif
```

[coc.nvim]: https://github.com/neoclide/coc.nvim
[vim-lsp]: https://github.com/prabirshrestha/vim-lsp
