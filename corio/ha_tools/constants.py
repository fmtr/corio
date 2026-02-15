from fmtr.tools.path_tools.path_tools import root

SUPERVISOR_TOKEN_KEY = 'SUPERVISOR_TOKEN'
URL_SUPERVISOR_ADDON = "http://supervisor"
URL_CORE_ADDON = F"{URL_SUPERVISOR_ADDON}/core/api"
PATH_ADDON_ENV = root / 'addon.env'
PATH_ADDON_OPTIONS = root / 'data' / 'options.json'
PATH_ADDON_CONFIG = root / 'config'
PATH_ADDON_MEDIA = root / 'media'
