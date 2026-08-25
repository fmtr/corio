from functools import lru_cache
from typing import Any

import yamlscript
from yaml import CDumper as Dumper
from yaml import dump


class MultilineDumper(Dumper):
    """

    Represent multiline strings as literal blocks.

    """
    pass


def _represent_string(dumper: Dumper, value: str):
    style = None
    is_multi = "\n" in value
    if is_multi:
        style = '|'
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


MultilineDumper.add_representer(str, _represent_string)


@lru_cache
def get_interpreter():
    """

    Fetches and returns a cached instance of the YAMLScript interpreter.

    """
    interpreter = yamlscript.YAMLScript()
    return interpreter


def to_yaml(obj: Any, **kwargs) -> str:
    """

    Serialize to YAML

    """

    kwargs = dict(allow_unicode=True, Dumper=MultilineDumper, sort_keys=False) | kwargs
    yaml_str = dump(obj, **kwargs)
    return yaml_str


def from_yaml(yaml_str: str) -> Any:
    """

    Deserialize from YAML

    """
    obj = get_interpreter().load(yaml_str)
    return obj
