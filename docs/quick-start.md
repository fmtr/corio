# Quick Start

## Install Base Package

```bash
pip install corio
```

## Install Extras

`corio` keeps optional dependencies behind extras:

```bash
pip install "corio[dm,http,api]" --upgrade
```

You can mix as many extras as needed for your project.

## Basic Usage

```python
import corio
from corio import Path

port = corio.env.get_int("APP_PORT", default=8080)
Path("runtime.json").write_json({"port": port})
```

## Missing Extra Errors

If a module needs an extra that is not installed, the import surfaces a clear guidance message with the required extra name.

Use the [Modules Overview](modules/index.md) table to see import names and extras.

