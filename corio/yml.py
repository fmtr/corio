from functools import lru_cache
from typing import Any
from yaml import CDumper as Dumper
from yaml import dump

import yamlscript


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

    kwargs = dict(allow_unicode=True, Dumper=Dumper, sort_keys=False) | kwargs
    yaml_str = dump(obj, **kwargs)
    return yaml_str


def from_yaml(yaml_str: str) -> Any:
    """

    Deserialize from YAML

    """
    obj = get_interpreter().load(yaml_str)
    return obj
