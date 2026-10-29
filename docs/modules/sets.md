# sets
`from corio import sets`

Settings management built on `pydantic-settings`.

Install: `pip install "corio[sets]" --upgrade`

## Settings models

`sets.Base` reads settings from initialization values, the CLI, environment variables, dotenv files, and YAML files.
Use `sets.BaseCLI` for models that should read CLI arguments and environment variables only.

## CLI subcommands

`sets.SubCommand` adds command execution to a `dm.Base` model. Use it for models that dispatch nested CLI subcommands; ordinary data models can continue to inherit directly from `dm.Base`. `sets.Base` already includes this behavior for the CLI entrypoint.

```python
from pydantic_settings import CliSubCommand

from corio import sets


class Status(sets.SubCommand):
    def run(self):
        return 0


class CLI(sets.Base, cli_parse_args=True):
    status: CliSubCommand[Status]


CLI().launch()
```
