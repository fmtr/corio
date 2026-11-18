# Shell commands

`corio.shell` provides a small DSL for building command arguments and shell expressions. It is a separate package rather than a `corio.__init__` export.

## Build a command

```python
from corio.shell import arg, ex, val

command = ex.git.status(--arg.short)
print(str(command))  # git status --short
print(command.tokens())  # ['git', 'status', '--short']
```

Use `ex` (or its alias, `shell`) to start a command. Attribute names form command and subcommand names; underscores become hyphens, so `ex.some_tool.run_` builds `some-tool run`. Pass positional strings or expressions to add arguments.

Use `arg` to build options. A single `-` or `+` prefix is added with unary minus or plus; repeat it to build long options. Add a separated value with `+`, or an equals value with `==`. Use `val` when you want to explicitly represent a value:

```python
output = ex.tool(--arg.output + val.report_file)
mode = ex.tool(--arg.mode == "quiet")
```

Values are kept as individual tokens. `str(command)` renders a shell-quoted representation for display, while `command.tokens()` returns the argument list suitable for process APIs.

## Combine commands

Use `&`, `^`, and `|` to build AND, OR, and pipe expressions, respectively. Parenthesize combinations when you need to make the intended grouping explicit:

```python
workflow = ex.prepare() & (ex.verify() | ex.recover())
print(str(workflow))  # prepare && (verify || recover)
```

Operator expressions render shell syntax. Command expressions can run locally with `.run()`, which invokes the command using its token list without asking a shell to interpret syntax. A leading `+` on a command expression is shorthand for `.run()`. To run a command expression through a shell, pass `shell=True`; to run a composed operator expression on systems with `sh`, pass its rendered form to the shell:

```python
ex.sh("-c", str(workflow)).run()
```
