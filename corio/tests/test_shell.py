from types import SimpleNamespace

from corio.shell import Argument, Expression, Shell, Subcommand, Value


def test_argument_prefixes_and_rendering_examples():
    arg = Argument()

    assert (-+-+-+-++-++++----arg).prefixes == "-+-+-+-++-++++----"
    assert str(arg.verbose) == "verbose"
    assert str(--arg.verbose) == "--verbose"
    assert str(--arg.verbose + "my_val") == "--verbose my_val"
    assert str(--arg.verbose + "my_val" + "val2") == "--verbose my_val val2"
    assert str(--arg.verbose == "eq_val") == "--verbose=eq_val"
    assert str(--arg.verbose == arg.other_val) == "--verbose=other-val"
    assert str(arg.up(--arg.detach, --arg.recreate)) == "up --detach --recreate"


def test_shell_command_chaining_examples():
    arg = Argument()
    val = Value()
    shell = Shell()

    assert type(shell.docker) is Expression
    assert type(shell.docker.run) is Expression
    assert type(shell.corio.secrets.encrypt) is Expression
    assert type(shell.corio.secrets.encrypt.active) is Subcommand

    assert str(shell.ls(-arg.h, "/")) == "ls -h /"
    assert str(shell.docker.run(-arg.it, "python:debian", arg.bash)) == "docker run -it python:debian bash"
    assert str(shell.corio.secrets.encrypt(--arg.contexts == val.web)) == "corio secrets encrypt --contexts=web"


def test_shell_context_is_propagated_to_commands():
    shell = Shell("ssh://remote.lan")
    cmd = shell.docker.run("-it")

    assert shell.context == "ssh://remote.lan"
    assert cmd.shell is shell
    assert cmd.shell.context == "ssh://remote.lan"


def test_command_call_casts_raw_strings_to_arguments():
    shell = Shell()
    command = shell.echo("hello", "world")

    assert all(isinstance(part, Argument) for part in command.children)


def test_repr_is_readable():
    arg = Argument()
    shell = Shell("ssh://remote.lan")
    command = shell.ls(-arg.h, "/")

    assert repr(arg.verbose) == "Argument('verbose')"
    assert repr(command) == "Expression('ls -h /')"
    assert repr(shell) == "Shell('ssh://remote.lan')"


def test_shell_generates_uvx_tox_command_string():
    arg = Argument()
    val = Value()
    shell = Shell()
    paths = SimpleNamespace(
        repo="/repo",
        pyproject_repo="/repo/pyproject.toml",
    )

    command = shell.uvx(
        --arg.with_ + val.tox_uv + val.tox + "two words",
        -arg.c + str(paths.pyproject_repo),
        --arg.root + str(paths.repo),
        --arg.workdir + str(f"{paths.repo}/.tox"),
    ).run()

    assert str(command) == (
        "uvx --with tox-uv tox 'two words' -c /repo/pyproject.toml "
        "--root /repo --workdir /repo/.tox run"
    )
    assert command.tokens() == [
        "uvx",
        "--with",
        "tox-uv",
        "tox",
        "'two words'",
        "-c",
        "/repo/pyproject.toml",
        "--root",
        "/repo",
        "--workdir",
        "/repo/.tox",
        "run",
    ]


def test_expression_tree_shape_examples():
    arg = Argument()
    val = Value()
    shell = Shell()

    docker = shell.docker
    assert docker.name == "docker"
    assert docker.children == []

    docker_run = shell.docker.run
    assert docker_run.active is not None
    assert docker_run.active.name == "run"
    assert docker_run.active.children == []

    encrypt = shell.corio.secrets.encrypt(--arg.context == val.web)
    assert encrypt.active is not None
    assert encrypt.active.name == "encrypt"
    assert len(encrypt.active.children) == 1
    assert str(encrypt.active.children[0]) == "--context=web"

    with_values = shell.uvx(--arg.with_ + val.tox_uv + val.tox + "two words")
    argument = with_values.children[0]
    assert isinstance(argument, Argument)
    assert argument.name == "with"
    assert argument.prefixes == "--"
    assert [type(node) for node in argument.children] == [Value, Value, Value]
    assert [node.name for node in argument.children] == ["tox-uv", "tox", "two words"]


def test_structure_examples_are_exact():
    arg = Argument()
    val = Value()
    shell = Shell()

    docker = shell.docker
    assert isinstance(docker, Expression)
    assert docker.name == "docker"
    assert docker.children == []
    assert docker.active is docker

    docker_run = shell.docker.run
    assert isinstance(docker_run, Expression)
    assert docker_run.name == "docker"
    assert len(docker_run.children) == 1
    first = docker_run.children[0]
    assert first.name == "run"
    assert first.children == []

    with_values = --arg.with_ + val.tox_uv + val.tox + "two words"
    assert isinstance(with_values, Argument)
    assert with_values.name == "with"
    assert [type(node) for node in with_values.children] == [Value, Value, Value]
    assert [node.name for node in with_values.children] == ["tox-uv", "tox", "two words"]
    assert [node.children for node in with_values.children] == [[], [], []]


def test_subcommand_chain_returns_same_expression():
    shell = Shell()

    expression = shell.corio
    chained = expression.secrets.encrypt.rotate

    assert chained is expression
    assert isinstance(chained, Expression)
    assert str(chained) == "corio secrets encrypt rotate"


def test_deep_subcommand_chain_builds_nested_tree():
    shell = Shell()

    command = shell.corio.secrets.encrypt.rotate.prune

    assert str(command) == "corio secrets encrypt rotate prune"
    assert command.active is not None
    assert command.active.name == "prune"
    secrets = command.children[0]
    encrypt = secrets.children[0]
    rotate = encrypt.children[0]
    prune = rotate.children[0]
    assert secrets.name == "secrets"
    assert encrypt.name == "encrypt"
    assert rotate.name == "rotate"
    assert prune.name == "prune"


def test_subcommand_calls_attach_under_active_subcommand():
    arg = Argument()
    val = Value()
    shell = Shell()

    command = shell.corio.secrets(--arg.context == val.web).encrypt(--arg.force).rotate(--arg.days + val.thirty)

    assert str(command) == "corio secrets --context=web encrypt --force rotate --days thirty"
    assert command.active is not None
    assert command.active.name == "rotate"
    assert [str(node) for node in command.active.children] == ["--days thirty"]


def test_expression_does_not_accept_nested_expressions_as_children():
    arg = Argument()
    val = Value()
    shell = Shell()

    command = shell.corio("secrets", "encrypt", --arg.context == val.web, --arg.verbose)

    assert str(command) == "corio secrets encrypt --context=web --verbose"
    assert command.tokens() == ["corio", "secrets", "encrypt", "--context=web", "--verbose"]


def test_plus_command_runs_with_popen_and_streams_lines(monkeypatch):
    shell = Shell()
    cmd = shell.echo("a", "b")
    calls = {}

    class _Process:
        args = ["echo", "a", "b"]

        def __init__(self):
            self.stdout = iter(["line1\n", "line2\n"])

        @staticmethod
        def wait():
            return 0

    def _popen(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return _Process()

    monkeypatch.setattr("corio.shell.dsl.subprocess.Popen", _popen)
    lines = list(+cmd)
    iter_lines = list(cmd)

    assert lines == ["line1", "line2"]
    assert iter_lines == ["line1", "line2"]
    assert calls["args"] == (["echo", "a", "b"],)
    assert calls["kwargs"]["stdout"] is not None
    assert calls["kwargs"]["stderr"] is not None
    assert calls["kwargs"]["text"] is True
    assert calls["kwargs"]["bufsize"] == 1


def test_subcommand_has_name_not_command_field():
    subcommand = Shell().docker.run.children[0]
    assert subcommand.name == "run"
    assert not hasattr(subcommand, "command")


def test_expression_children_never_hold_values():
    shell = Shell()
    expr = shell.echo("hello", Value().world)
    assert [type(node) for node in expr.children] == [Argument, Argument]
    assert [node.name for node in expr.children] == ["hello", "world"]


def test_subcommand_children_never_hold_values():
    shell = Shell()
    expr = shell.docker.run("hello", Value().world)
    children = expr.active.children
    assert [type(node) for node in children] == [Argument, Argument]
    assert [node.name for node in children] == ["hello", "world"]


def test_argument_call_coerces_raw_strings_to_argument_children():
    arg = Argument()
    coerced = arg.items("one", "two")
    assert [type(node) for node in coerced.children] == [Argument, Argument]
    assert [node.name for node in coerced.children] == ["one", "two"]


def test_argument_eq_uses_sep_field_for_serialization():
    arg = Argument()
    built = --arg.context == "web"
    assert built.sep == "="
    assert str(built) == "--context=web"
    assert built.tokens() == ["--context=web"]


def test_argument_non_space_sep_joins_name_and_first_child():
    custom = Argument(name="opt", prefixes="--", children=[Value(name="x"), Value(name="y")], sep=":")
    assert str(custom) == "--opt:x y"
    assert custom.tokens() == ["--opt:x", "y"]
