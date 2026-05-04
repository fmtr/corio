# Modules Overview

This table maps friendly imports from `corio.__init__` to docs pages and required extras.

`Extra(s)` refers to `tool.corio.dependencies` in `pyproject.toml`.

| Friendly import | Extra(s) | Reference |
| --- | --- | --- |
| `from corio import ai` | `ai` | [ai](ai.md) |
| `from corio import aio` | - | [aio](aio.md) |
| `from corio import api` | `api` | [api](api.md) |
| `from corio import augmentation` | `augmentation` | [augmentation](augmentation.md) |
| `from corio import av` | `av` | [av](av.md) |
| `from corio import caching` | `caching` | [caching](caching.md) |
| `from corio import dataclass` | - | [dataclass](dataclass.md) |
| `from corio import datatype` | - | [datatype](datatype.md) |
| `from corio import db` | `db` / `db.document` | [db](db.md) |
| `from corio import debug` | `debug` | [debug](debug.md) |
| `from corio import dm` | `dm` | [dm](dm.md) |
| `from corio import dns` | `dns` | [dns](dns.md) |
| `from corio import docker` | `docker.client` | [docker](docker.md) |
| `from corio import dt` | - | [dt](dt.md) |
| `from corio import encrypt` | `encrypt` | [encrypt](encrypt.md) |
| `from corio import env` | - (`env.io` for dotenv helpers) | [env](env.md) |
| `from corio import environment` | - (`env.io` for dotenv helpers) | [env](env.md) |
| `from corio import function` | - | [function](function.md) |
| `from corio import google_api` | `google.api` | [google_api](google_api.md) |
| `from corio import ha` | `ha` (`ha.api` for API/supervisor extras) | [ha](ha.md) |
| `from corio import hash` | - | [hash](hash.md) |
| `from corio import hfh` | `hfh` | [hfh](hfh.md) |
| `from corio import html` | `html` | [html](html.md) |
| `from corio import http` | `http` | [http](http.md) |
| `from corio import import_` | - | [import](import.md) |
| `from corio import infra` | `infra` | [infra](infra.md) |
| `from corio import inherit` | - | [inherit](inherit.md) |
| `from corio import interface` | `interface` | [interface](interface.md) |
| `from corio import iterator` | - | [iterator](iterator.md) |
| `from corio import json` | - | [json](json.md) |
| `from corio import json_fix` | `json-fix` | [json_fix](json_fix.md) |
| `from corio import logging` | `logging` | [logging](logging.md) |
| `from corio import merging` | `merging` | [merging](merging.md) |
| `from corio import metric` | `metric` | [metric](metric.md) |
| `from corio import mqtt` | `mqtt` | [mqtt](mqtt.md) |
| `from corio import name` | - | [name](name.md) |
| `from corio import net` | - | [net](net.md) |
| `from corio import netrc` | `netrc` | [netrc](netrc.md) |
| `from corio import openai` | `openai.api` | [openai](openai.md) |
| `from corio import packaging` | - | [packaging](packaging.md) |
| `from corio import parallel` | `parallel` | [parallel](parallel.md) |
| `from corio import path` | - (`path.app`, `path.type` for extras) | [path](path.md) |
| `from corio import patterns` | `patterns` | [patterns](patterns.md) |
| `from corio import pdf` | `pdf` | [pdf](pdf.md) |
| `from corio import platform` | - | [platform](platform.md) |
| `from corio import process` | `process` | [process](process.md) |
| `from corio import profiling` | `profiling` | [profiling](profiling.md) |
| `from corio import random` | - | [random](random.md) |
| `from corio import secrets` | `secrets` | [secrets](secrets.md) |
| `from corio import semantic` | `semantic` | [semantic](semantic.md) |
| `from corio import sets` | `sets` | [sets](sets.md) |
| `from corio import setup` | `setup` | [setup](setup.md) |
| `from corio import spaces` | `spaces` | [spaces](spaces.md) |
| `from corio import string` | - | [string](string.md) |
| `from corio import tabular` | `tabular` | [tabular](tabular.md) |
| `from corio import toml` | - | [toml](toml.md) |
| `from corio import tokenization` | `tokenization` | [tokenization](tokenization.md) |
| `from corio import unicode` | `unicode` | [unicode](unicode.md) |
| `from corio import vcs` | `vcs` | [vcs](vcs.md) |
| `from corio import version` | `version` / `version.dev` | [version](version.md) |
| `from corio import webhook` | `webhook` | [webhook](webhook.md) |
| `from corio import yaml` | `yaml` | [yaml](yaml.md) |
| `from corio import youtube` | `youtube` | [youtube](youtube.md) |

## Shared Top-Level Exports

- `from corio import Path, PackagePaths, AppPaths` -> [path](path.md)
- `from corio import logger` -> [logging](logging.md)
- `from corio import Constants` -> [path](path.md)
- `from corio import Client` -> [http](http.md)
- `from corio import Timer` -> [profiling](profiling.md)
- `from corio import ContextProcess` -> [process](process.md)
- `from corio import merge` -> [merging](merging.md)

