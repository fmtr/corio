from functools import lru_cache
from typing import Any
from yaml import CDumper as Dumper
from yaml import dump

try:
    import yamlscript
except ImportError:
    raise  # Raise if even the package isn't installed, to trigger the regular missing extra exception.
except Exception as exception:
    pass  # Allow missing binary, so we can install on-demand


def install():
    """

    Installs the YAML Script runtime binary of the specified version.

    """
    import subprocess
    from corio import logger, packaging

    version = packaging.get_version('yamlscript')
    logger.warning(f"Installing YAML Script runtime binary version {version}...")
    result = subprocess.run(f"curl https://yamlscript.org/install | VERSION={version} LIB=1 bash", shell=True, check=True)
    return result


@lru_cache
def get_module(is_auto=True):
    """

    Get the YAML Script runtime module, installing the runtime if specified

    """
    try:
        import yamlscript
    except Exception as exception:
        if not is_auto:
            raise ImportError(f'YAML Script runtime missing and {is_auto=}. Set to {True} to install.') from exception
        install()
        import yamlscript
    return yamlscript


@lru_cache
def get_interpreter():
    """

    Fetches and returns a cached instance of the YAMLScript interpreter.

    """
    module = get_module()
    interpreter = module.YAMLScript()
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


if __name__ == '__main__':
    data = dict(a=1, c=2, b=3)
    yaml_str = to_yaml(data)
    yaml_str
