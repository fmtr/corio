from corio import ai_tools as ai
from corio import datetime_tools as dt
from corio import dns_tools as dns
from corio import docker_tools as docker
from corio import ha_tools as ha
from corio import infrastructure_tools as infra
from corio import interface_tools as interface
from corio import version_tools as version
from corio.constants import Constants
from corio.import_tools import MissingExtraMockModule
from corio.logging_tools import logger
# Submodules
from corio.path_tools import Path, PackagePaths, AppPaths
from corio.paths import paths
from corio.setup_tools import Setup, Dependencies, Tools

try:
    from corio import augmentation_tools as augmentation
except ModuleNotFoundError as exception:
    augmentation = MissingExtraMockModule('augmentation', exception)

try:
    from corio import yaml_tools as yaml
except ModuleNotFoundError as exception:
    yaml = MissingExtraMockModule('yaml', exception)


try:
    from corio import parallel_tools as parallel
except ModuleNotFoundError as exception:
    parallel = MissingExtraMockModule('parallel', exception)

try:
    from corio import profiling_tools as profiling
    from corio.profiling_tools import Timer
except ModuleNotFoundError as exception:
    profiling = Timer = MissingExtraMockModule('profiling', exception)

try:
    import corio.process_tools as process
    from corio.process_tools import ContextProcess
except ModuleNotFoundError as exception:
    process = ContextProcess = MissingExtraMockModule('process', exception)

try:
    from corio import tokenization_tools as tokenization
except ModuleNotFoundError as exception:
    tokenization = MissingExtraMockModule('tokenization', exception)

try:
    from corio import unicode_tools as unicode
except ModuleNotFoundError as exception:
    unicode = MissingExtraMockModule('unicode', exception)

try:
    from corio import netrc_tools as netrc
except ModuleNotFoundError as exception:
    netrc = MissingExtraMockModule('netrc', exception)

try:
    from corio import spaces_tools as spaces
except ModuleNotFoundError as exception:
    spaces = MissingExtraMockModule('spaces', exception)

try:
    from corio import hfh_tools as hfh
except ModuleNotFoundError as exception:
    hfh = MissingExtraMockModule('hfh', exception)

try:
    from corio import merging_tools as merging
    from corio.merging_tools import merge
except ModuleNotFoundError as exception:
    merging = merge = MissingExtraMockModule('merging', exception)

try:
    from corio import api_tools as api
except ModuleNotFoundError as exception:
    api = MissingExtraMockModule('api', exception)

try:
    from corio import data_modelling_tools as dm
except ModuleNotFoundError as exception:
    dm = MissingExtraMockModule('dm', exception)

try:
    from corio import json_fix_tools as json_fix
except ModuleNotFoundError as exception:
    json_fix = MissingExtraMockModule('json_fix', exception)

try:
    from corio import semantic_tools as semantic
except ModuleNotFoundError as exception:
    semantic = MissingExtraMockModule('semantic', exception)

try:
    from corio import metric_tools as metric
except ModuleNotFoundError as exception:
    metric = MissingExtraMockModule('metric', exception)

try:
    from corio import html_tools as html
except ModuleNotFoundError as exception:
    html = MissingExtraMockModule('html', exception)

try:
    from corio import openai_tools as openai
except ModuleNotFoundError as exception:
    openai = MissingExtraMockModule('openai', exception)

try:
    from corio import google_api_tools as google_api
except ModuleNotFoundError as exception:
    google_api = MissingExtraMockModule('google.api', exception)

try:
    from corio import caching_tools as caching
except ModuleNotFoundError as exception:
    caching = MissingExtraMockModule('caching', exception)

try:
    from corio import pdf_tools as pdf
except ModuleNotFoundError as exception:
    pdf = MissingExtraMockModule('pdf', exception)

try:
    from corio import tabular_tools as tabular
except ModuleNotFoundError as exception:
    tabular = MissingExtraMockModule('tabular', exception)

try:
    from corio import debugging_tools as debug
except ModuleNotFoundError as exception:
    debug = MissingExtraMockModule('debug', exception)

try:
    from corio import settings_tools as sets
except ModuleNotFoundError as exception:
    sets = MissingExtraMockModule('sets', exception)

try:
    from corio import pattern_tools as patterns
except ModuleNotFoundError as exception:
    patterns = MissingExtraMockModule('patterns', exception)

try:
    from corio import http_tools as http
    from corio.http_tools import Client
except ModuleNotFoundError as exception:
    http = Client = MissingExtraMockModule('http', exception)

try:
    from corio import webhook_tools as webhook
except ModuleNotFoundError as exception:
    webhook = MissingExtraMockModule('webhook', exception)

try:
    from corio import mqtt_tools as mqtt
except ModuleNotFoundError as exception:
    mqtt = MissingExtraMockModule('mqtt', exception)

try:
    from corio import av_tools as av
except ModuleNotFoundError as exception:
    av = MissingExtraMockModule('av', exception)

try:
    from corio import youtube_tools as youtube
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
