# cmake-language-server
[![PyPI](https://img.shields.io/pypi/v/cmake-language-server)](https://pypi.org/project/cmake-language-server)
[![GitHub Actions (Tests)](https://github.com/regen100/cmake-language-server/workflows/Tests/badge.svg)](https://github.com/regen100/cmake-language-server/actions)
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

### Clients

- Neovim ([neoclide/coc.nvim][coc.nvim])

#### Neovim

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


[coc.nvim]: https://github.com/neoclide/coc.nvim
