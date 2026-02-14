from fmtr.tools import Setup

DEPENDENCIES = {
    'dev': ['logging', 'version.dev', 'debug', 'sets', 'yaml', 'db.document'],

    'install': [],
    'test': ['pytest-cov'],
    'yaml': ['yamlscript', 'pyyaml'],
    'logging': ['logfire', 'version'],
    'parallel': ['dask[bag]', 'distributed', 'bokeh'],
    'tokenization': ['tokenizers'],
    'augmentation': ['faker', 'sre_yield'],
    'process': ['logging'],
    'profiling': ['contexttimer'],
    'docker.client': ['python-on-whales'],
    'unicode': ['Unidecode'],
    'version': [],
    'version.dev': ['semver'],
    'spaces': ['netrc'],
    'netrc': ['tinynetrc'],
    'hfh': ['huggingface_hub'],
    'merging': ['deepmerge'],
    'api': ['fastapi', 'uvicorn[standard]', 'logging', 'dm', 'logfire[fastapi]'],
    'ai': ['peft', 'transformers[sentencepiece]', 'torchvision', 'torchaudio', 'dm'],
    'dm': ['pydantic', 'pydantic-extra-types', 'pycountry'],
    'openai.api': ['openai'],
    'ai.client': ['logging', 'dm', 'openai.api', 'pydantic-ai[logfire,openai]', 'ollama'],
    'json-fix': ['json_repair'],
    'semantic': ['sentence_transformers', 'metric'],
    'metric': ['tabular'],
    'tabular': ['pandas', 'tabulate', 'openpyxl', 'odfpy', 'deepdiff'],
    'html': ['html2text'],
    'interface': ['flet[all] <0.80.0', 'flet-video', 'flet-webview'],
    'google.api': ['google-auth', 'google-auth-oauthlib', 'google-auth-httplib2', 'google-api-python-client'],
    'caching': ['diskcache', 'cachetools'],
    'pdf': ['pymupdf', 'dm', 'pymupdf4llm'],
    'debug': ['pydevd-pycharm~=251.25410.159'],
    'sets': ['pydantic-settings', 'dm', 'yaml'],
    'path.app': ['appdirs'],
    'path.type': ['filetype'],
    'dns': ['dnspython[doh]', 'http'],
    'patterns': ['regex'],
    'http': ['httpx', 'httpx_retries', 'logging', 'logfire[httpx]'],
    'setup': ['setuptools'],
    'webhook': ['http'],
    'browsers': ['playwright'],
    'db': [],
    'db.document': ['beanie[odm]'],
    'mqtt': ['aiomqtt'],
    'av': ['av'],
    'ha': ['dotenv'],
    'ha.api': ['ha', 'homeassistant_api', 'aiohasupervisor'],
    'doc': ['mkdocs', 'mkdocs-material', 'mkdocstrings[python]', 'mike', 'mkdocs-include-dir-to-nav'],
    'youtube': ['pytubefix'],
    'infra': ['version.dev', 'logging', 'setup', 'doc', 'sets', 'build', 'twine', 'packaging', 'vcs', 'docker.client', 'merging', 'http', 'api'],
    'deploy': ['infra'],  # todo: remove alias
    'vcs': ['pygit2'],


}

setup = Setup(
    dependencies=DEPENDENCIES,
)

setup
