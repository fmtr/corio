from corio.import_tools import MissingExtraMockModule

try:
    from corio.infrastructure_tools.project import Project
except ModuleNotFoundError as exception:
    Project = MissingExtraMockModule('infra', exception)

try:
    from corio.infrastructure_tools.api import Api
except ModuleNotFoundError as exception:
    Api = MissingExtraMockModule('infra', exception)
