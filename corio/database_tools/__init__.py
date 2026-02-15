from corio.import_tools import MissingExtraMockModule

try:
    from corio.database_tools import document
except ModuleNotFoundError as exception:
    document = MissingExtraMockModule('db.document', exception)
