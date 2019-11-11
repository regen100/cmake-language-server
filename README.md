# cmake-language-server

CMake LSP Implementation.

Alpha Stage, work in progress.

## Features
- [x] Builtin command completion
- [x] Documentation for commands and variables on hover
- [x] Formatting

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
