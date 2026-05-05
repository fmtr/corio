import importlib.metadata


def get_version(module):
    """

    Retrieve the version of a specified module.

    """

    if type(module) is not str:
        module = module.__name__
    version = importlib.metadata.version(module)
    return version
