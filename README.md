# cmake-language-server
[![GitHub Actions (Tests)](https://github.com/regen100/cmake-language-server/workflows/Tests/badge.svg)](https://github.com/regen100/cmake-language-server/actions)

CMake LSP Implementation.

Alpha Stage, work in progress.

## Features
- [x] Builtin command completion
- [x] Documentation for commands and variables on hover
- [x] Formatting

## Commands

- cmake-language-server: LSP server
- cmake-format: CLI frontend for formatting

## Installation

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
