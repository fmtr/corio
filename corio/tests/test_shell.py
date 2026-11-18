import inspect
import shlex
import subprocess
from abc import ABC
from types import SimpleNamespace

from corio.shell import arg, ex, shell, val
from corio.shell.dsl import (
    And,
    Argument,
    Expression,
    Expressions,
    Or,
    Pipe,
    Subcommand,
    Value,
    _normalize,
)


def test_normalize_distinguishes_hyphens_and_underscores():
    assert _normalize("some_name") == "some-name"
    assert _normalize("some__name") == "some_name"
    assert _normalize("_if") == "if"
    assert _normalize("name_") == "name"


def test_shell_alias_is_the_expression_builder():
    assert shell is ex


def test_argument_and_value_helpers_are_public():
    assert str(-arg.sample) == "-sample"
    assert str(val.sample) == "sample"


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


def test_dsl_objects_can_be_class_attributes_without_making_class_abstract():
    objects = (
        Argument().restore_file,
        Value().restore_file,
        ex.decode_config,
        ex.decode_config.restore,
    )

    for obj in objects:
        class Command(ABC):
            dsl_object = obj

        assert not inspect.isabstract(Command)


def test_shell_command_chaining_examples():
    arg = Argument()
    val = Value()

    assert type(ex.docker) is Expression
    assert type(ex.docker.run_) is Expression
    assert type(ex.corio.secrets.encrypt) is Expression
    assert type(ex.corio.secrets.encrypt.active) is Subcommand

    assert str(ex.ls(-arg.h, "/")) == "ls -h /"
    assert str(ex("qemu-system-x86_64")(-arg.enable_kvm)) == "qemu-system-x86_64 -enable-kvm"

    assert str(ex.docker.run_(-arg.it, "python:debian", arg.bash)) == "docker run -it python:debian bash"
    assert str(ex.corio.secrets.encrypt(--arg.contexts == val.web)) == "corio secrets encrypt --contexts=web"


def test_command_call_casts_raw_strings_to_arguments():
    command = ex.echo("hello", "world")

    assert all(isinstance(part, Argument) for part in command.children)


def test_repr_is_readable():
    arg = Argument()
    command = ex.ls(-arg.h, "/")

    assert repr(arg.verbose) == "Argument('verbose')"
    assert repr(command) == "Expression('ls -h /')"


def test_shell_generates_uvx_tox_command_string():
    arg = Argument()
    val = Value()
    paths = SimpleNamespace(
        repo="/repo",
        pyproject_repo="/repo/pyproject.toml",
        tox_workdir="/tmp/corio/tox",
    )

    command = ex.uvx(
        --arg.with_ + val.tox_uv + val.tox + "two words",
        -arg.c + str(paths.pyproject_repo),
        --arg.root + str(paths.repo),
        --arg.workdir + paths.tox_workdir,
    ).run_

    assert str(command) == (
        "uvx --with tox-uv tox 'two words' -c /repo/pyproject.toml "
        "--root /repo --workdir /tmp/corio/tox run"
    )
    assert command.tokens() == [
        "uvx",
        "--with",
        "tox-uv",
        "tox",
        "two words",
        "-c",
        "/repo/pyproject.toml",
        "--root",
        "/repo",
        "--workdir",
        "/tmp/corio/tox",
        "run",
    ]


def test_expression_tree_shape_examples():
    arg = Argument()
    val = Value()

    docker = ex.docker
    assert docker.name == "docker"
    assert docker.children == []

    docker_run = ex.docker.run_
    assert docker_run.active is not None
    assert docker_run.active.name == "run"
    assert docker_run.active.children == []

    encrypt = ex.corio.secrets.encrypt(--arg.context == val.web)
    assert encrypt.active is not None
    assert encrypt.active.name == "encrypt"
    assert len(encrypt.active.children) == 1
    assert str(encrypt.active.children[0]) == "--context=web"

    with_values = ex.uvx(--arg.with_ + val.tox_uv + val.tox + "two words")
    argument = with_values.children[0]
    assert isinstance(argument, Argument)
    assert argument.name == "with"
    assert argument.prefixes == "--"
    assert [type(node) for node in argument.children] == [Value, Value, Value]
    assert [node.name for node in argument.children] == ["tox-uv", "tox", "two words"]


def test_structure_examples_are_exact():
    arg = Argument()
    val = Value()

    docker = ex.docker
    assert isinstance(docker, Expression)
    assert docker.name == "docker"
    assert docker.children == []
    assert docker.active is docker

    docker_run = ex.docker.run_
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

    expression = ex.corio
    chained = expression.secrets.encrypt.rotate

    assert chained is expression
    assert isinstance(chained, Expression)
    assert str(chained) == "corio secrets encrypt rotate"


def test_deep_subcommand_chain_builds_nested_tree():

    command = ex.corio.secrets.encrypt.rotate.prune

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

    command = ex.corio.secrets(--arg.context == val.web).encrypt(--arg.force).rotate(--arg.days + val.thirty)

    assert str(command) == "corio secrets --context=web encrypt --force rotate --days thirty"
    assert command.active is not None
    assert command.active.name == "rotate"
    assert [str(node) for node in command.active.children] == ["--days thirty"]


def test_expression_accepts_composite_expressions_as_children():
    composite = ex.probe("one") | ex.collect()
    command = ex.launcher(--Argument().script + composite)
    nested_command = ex.inspect(composite)

    assert isinstance(composite, Pipe)
    assert isinstance(composite, Expressions)
    assert command.tokens() == ["launcher", "--script", "probe one | collect"]
    assert command.children[0].children[0] is composite
    assert nested_command.children == [composite]
    assert shlex.split(str(command)) == command.tokens()
    assert shlex.split(str(nested_command)) == nested_command.tokens()


def test_expression_operators_keep_shell_precedence():
    first = ex.probe("first")
    second = ex.collect("second")
    third = ex.archive()

    and_expression = first & (second | third)
    pipe_expression = (first & second) | third
    or_expression = first ^ (second & third)
    mixed_expression = first & (second ^ third)
    left_mixed_expression = (first & second) ^ third

    assert isinstance(and_expression, And)
    assert isinstance(and_expression.children[1], Pipe)
    assert isinstance(or_expression, Or)
    assert str(and_expression) == "probe first && collect second | archive"
    assert str(pipe_expression) == "(probe first && collect second) | archive"
    assert str(first ^ second) == "probe first || collect second"
    assert str(or_expression) == "probe first || (collect second && archive)"
    assert str(mixed_expression) == "probe first && (collect second || archive)"
    assert str(left_mixed_expression) == "probe first && collect second || archive"


def test_expressions_are_single_escaped_argument_tokens():
    expression = ex.probe("two words")
    command = ex.audit.invoke_(expression)
    argument_command = ex.launcher(--Argument().script + expression)
    call_argument = Argument().items(expression)

    assert command.tokens() == ["audit", "invoke", "probe 'two words'"]
    assert command.active.children[0] is expression
    assert shlex.split(str(command)) == command.tokens()
    assert argument_command.tokens() == ["launcher", "--script", "probe 'two words'"]
    assert argument_command.children[0].children[0] is expression
    assert call_argument.children[0] is expression
    assert call_argument.tokens() == ["items", "probe 'two words'"]


def test_nested_bash_commands_round_trip_shell_quoting():
    left = ex.bash(-Argument().c + ex.probe("alpha beta"))
    right = ex.bash(-Argument().c + ex.collect("gamma delta"))
    command = ex.bash(-Argument().c + (left & right))

    outer_tokens = command.tokens()

    assert outer_tokens[:2] == ["bash", "-c"]
    assert len(outer_tokens) == 3
    assert outer_tokens[2].startswith("bash -c ")
    assert " && bash -c " in outer_tokens[2]
    assert shlex.split(str(command)) == outer_tokens
    assert shlex.split(outer_tokens[2]) == [
        "bash",
        "-c",
        "probe 'alpha beta'",
        "&&",
        "bash",
        "-c",
        "collect 'gamma delta'",
    ]


def test_run_passes_composite_shell_syntax_to_an_explicit_command(monkeypatch):
    calls = []
    command = ex.launcher(--Argument().script + (ex.probe("one") & ex.collect()))

    def _run(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr("corio.shell.dsl.subprocess.run", _run)

    command.run()

    assert calls == [
        ((["launcher", "--script", "probe one && collect"],), {"check": True, "shell": False}),
    ]


def test_run_and_plus_forward_to_subprocess_with_streaming_defaults(monkeypatch):
    cmd = ex.echo("a", "b")
    calls = []
    completed = object()

    def _run(*args, **kwargs):
        calls.append((args, kwargs))
        return completed

    monkeypatch.setattr("corio.shell.dsl.subprocess.run", _run)

    assert cmd.run(check=False, cwd="/tmp") is completed
    assert +cmd is completed
    assert calls == [
        ((["echo", "a", "b"],), {"check": False, "shell": False, "cwd": "/tmp"}),
        ((["echo", "a", "b"],), {"check": True, "shell": False}),
    ]


def test_run_renders_a_command_string_for_shell_mode(monkeypatch):
    calls = []

    def _run(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr("corio.shell.dsl.subprocess.run", _run)

    ex.echo("two words").run(shell=True)

    assert calls == [
        (("echo 'two words'",), {"check": True, "shell": True}),
    ]


def test_iter_expression_yields_stdout_lines(monkeypatch):
    cmd = ex.echo("a", "b")
    calls = {}

    class _Process:
        stdout = iter(["line1\n", "line2\n"])

        @staticmethod
        def wait():
            return 0

    def _popen(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return _Process()

    monkeypatch.setattr("corio.shell.dsl.subprocess.Popen", _popen)

    assert list(cmd) == ["line1", "line2"]
    assert calls["args"] == (["echo", "a", "b"],)
    assert calls["kwargs"] == {"stdout": subprocess.PIPE, "text": True, "bufsize": 1}


def test_exec_supports_a_custom_exec_method():
    calls = []

    def method(name, tokens):
        calls.append((name, tokens))

    ex.echo("two words").exec(method=method)

    assert calls == [("echo", ["echo", "two words"])]


def test_run_and_exec_log_the_rendered_command(monkeypatch):
    messages = []
    monkeypatch.setattr("corio.shell.dsl.logger.info", messages.append)
    monkeypatch.setattr("corio.shell.dsl.subprocess.run", lambda *args, **kwargs: None)

    command = ex.echo("two words")
    command.run()
    command.exec(method=lambda name, tokens: None)

    assert messages == ["echo 'two words'", "echo 'two words'"]


def test_subcommand_has_name_not_command_field():
    subcommand = ex.docker.run_.children[0]
    assert subcommand.name == "run"
    assert not hasattr(subcommand, "command")


def test_expression_children_never_hold_values():
    expr = ex.echo("hello", Value().world)
    assert [type(node) for node in expr.children] == [Argument, Argument]
    assert [node.name for node in expr.children] == ["hello", "world"]


def test_subcommand_children_never_hold_values():
    expr = ex.docker.run_("hello", Value().world)
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
