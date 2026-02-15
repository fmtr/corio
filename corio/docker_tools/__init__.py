from fmtr.tools.import_tools import MissingExtraMockModule

try:
    from python_on_whales import DockerClient
except ModuleNotFoundError as exception:
    DockerClient = MissingExtraMockModule('docker.client', exception)
