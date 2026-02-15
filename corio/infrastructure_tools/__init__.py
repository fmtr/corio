from fmtr.tools.import_tools import MissingExtraMockModule

try:
    from fmtr.tools.infrastructure_tools.project import Project
except ModuleNotFoundError as exception:
    Project = MissingExtraMockModule('infra', exception)

try:
    from fmtr.tools.infrastructure_tools.api import Api
except ModuleNotFoundError as exception:
    Api = MissingExtraMockModule('infra', exception)
