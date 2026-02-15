from fmtr.tools.import_tools import MissingExtraMockModule

try:
    from fmtr.tools.database_tools import document
except ModuleNotFoundError as exception:
    document = MissingExtraMockModule('db.document', exception)
