from corio.import_tools import MissingExtraMockModule

try:
    from corio.dns_tools import server, client, dm, proxy
    import dns
except ModuleNotFoundError as exception:
    dns = server = client = dm = proxy = MissingExtraMockModule('dns', exception)
