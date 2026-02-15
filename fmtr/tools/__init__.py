import fmtr.tools.async_tools as aio
import fmtr.tools.database_tools as db
import fmtr.tools.dataclass_tools as dataclass
import fmtr.tools.datatype_tools as datatype
import fmtr.tools.environment_tools as env
import fmtr.tools.environment_tools as environment
import fmtr.tools.function_tools as function
import fmtr.tools.hash_tools as hash
import fmtr.tools.import_tools as import_
import fmtr.tools.inherit_tools as inherit
import fmtr.tools.iterator_tools as iterator
import fmtr.tools.json_tools as json
import fmtr.tools.logging_tools as logging
import fmtr.tools.name_tools as name
import fmtr.tools.networking_tools as net
import fmtr.tools.packaging_tools as packaging
import fmtr.tools.path_tools as path
import fmtr.tools.platform_tools as platform
import fmtr.tools.random_tools as random
import fmtr.tools.setup_tools as setup
import fmtr.tools.string_tools as string
from fmtr.tools import ai_tools as ai
from fmtr.tools import datetime_tools as dt
from fmtr.tools import dns_tools as dns
from fmtr.tools import docker_tools as docker
from fmtr.tools import ha_tools as ha
from fmtr.tools import infrastructure_tools as infra
from fmtr.tools import interface_tools as interface
from fmtr.tools import version_tools as version
from fmtr.tools.constants import Constants
from fmtr.tools.import_tools import MissingExtraMockModule
from fmtr.tools.logging_tools import logger
# Submodules
from fmtr.tools.path_tools import Path, PackagePaths, AppPaths
from fmtr.tools.paths import paths
from fmtr.tools.setup_tools import Setup, Dependencies, Tools

try:
    from fmtr.tools import augmentation_tools as augmentation
except ModuleNotFoundError as exception:
    augmentation = MissingExtraMockModule('augmentation', exception)

try:
    from fmtr.tools import yaml_tools as yaml
except ModuleNotFoundError as exception:
    yaml = MissingExtraMockModule('yaml', exception)


try:
    from fmtr.tools import parallel_tools as parallel
except ModuleNotFoundError as exception:
    parallel = MissingExtraMockModule('parallel', exception)

try:
    from fmtr.tools import profiling_tools as profiling
    from fmtr.tools.profiling_tools import Timer
except ModuleNotFoundError as exception:
    profiling = Timer = MissingExtraMockModule('profiling', exception)

try:
    import fmtr.tools.process_tools as process
    from fmtr.tools.process_tools import ContextProcess
except ModuleNotFoundError as exception:
    process = ContextProcess = MissingExtraMockModule('process', exception)

try:
    from fmtr.tools import tokenization_tools as tokenization
except ModuleNotFoundError as exception:
    tokenization = MissingExtraMockModule('tokenization', exception)

try:
    from fmtr.tools import unicode_tools as unicode
except ModuleNotFoundError as exception:
    unicode = MissingExtraMockModule('unicode', exception)

try:
    from fmtr.tools import netrc_tools as netrc
except ModuleNotFoundError as exception:
    netrc = MissingExtraMockModule('netrc', exception)

try:
    from fmtr.tools import spaces_tools as spaces
except ModuleNotFoundError as exception:
    spaces = MissingExtraMockModule('spaces', exception)

try:
    from fmtr.tools import hfh_tools as hfh
except ModuleNotFoundError as exception:
    hfh = MissingExtraMockModule('hfh', exception)

try:
    from fmtr.tools import merging_tools as merging
    from fmtr.tools.merging_tools import merge
except ModuleNotFoundError as exception:
    merging = merge = MissingExtraMockModule('merging', exception)

try:
    from fmtr.tools import api_tools as api
except ModuleNotFoundError as exception:
    api = MissingExtraMockModule('api', exception)

try:
    from fmtr.tools import data_modelling_tools as dm
except ModuleNotFoundError as exception:
    dm = MissingExtraMockModule('dm', exception)

try:
    from fmtr.tools import json_fix_tools as json_fix
except ModuleNotFoundError as exception:
    json_fix = MissingExtraMockModule('json_fix', exception)

try:
    from fmtr.tools import semantic_tools as semantic
except ModuleNotFoundError as exception:
    semantic = MissingExtraMockModule('semantic', exception)

try:
    from fmtr.tools import metric_tools as metric
except ModuleNotFoundError as exception:
    metric = MissingExtraMockModule('metric', exception)

try:
    from fmtr.tools import html_tools as html
except ModuleNotFoundError as exception:
    html = MissingExtraMockModule('html', exception)

try:
    from fmtr.tools import openai_tools as openai
except ModuleNotFoundError as exception:
    openai = MissingExtraMockModule('openai', exception)

try:
    from fmtr.tools import google_api_tools as google_api
except ModuleNotFoundError as exception:
    google_api = MissingExtraMockModule('google.api', exception)

try:
    from fmtr.tools import caching_tools as caching
except ModuleNotFoundError as exception:
    caching = MissingExtraMockModule('caching', exception)

try:
    from fmtr.tools import pdf_tools as pdf
except ModuleNotFoundError as exception:
    pdf = MissingExtraMockModule('pdf', exception)

try:
    from fmtr.tools import tabular_tools as tabular
except ModuleNotFoundError as exception:
    tabular = MissingExtraMockModule('tabular', exception)

try:
    from fmtr.tools import debugging_tools as debug
except ModuleNotFoundError as exception:
    debug = MissingExtraMockModule('debug', exception)

try:
    from fmtr.tools import settings_tools as sets
except ModuleNotFoundError as exception:
    sets = MissingExtraMockModule('sets', exception)

try:
    from fmtr.tools import pattern_tools as patterns
except ModuleNotFoundError as exception:
    patterns = MissingExtraMockModule('patterns', exception)

try:
    from fmtr.tools import http_tools as http
    from fmtr.tools.http_tools import Client
except ModuleNotFoundError as exception:
    http = Client = MissingExtraMockModule('http', exception)

try:
    from fmtr.tools import webhook_tools as webhook
except ModuleNotFoundError as exception:
    webhook = MissingExtraMockModule('webhook', exception)

try:
    from fmtr.tools import mqtt_tools as mqtt
except ModuleNotFoundError as exception:
    mqtt = MissingExtraMockModule('mqtt', exception)

try:
    from fmtr.tools import av_tools as av
except ModuleNotFoundError as exception:
    av = MissingExtraMockModule('av', exception)

try:
    from fmtr.tools import youtube_tools as youtube
except ModuleNotFoundError as exception:
    youtube = MissingExtraMockModule('youtube', exception)

try:
    import pygit2 as vcs
except ModuleNotFoundError as exception:
    vcs = MissingExtraMockModule('vcs', exception)



def get_version():
    """

    Defer reading version

    """
    return paths.metadata.version
