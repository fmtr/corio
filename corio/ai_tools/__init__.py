from fmtr.tools.import_tools import MissingExtraMockModule

try:
    from fmtr.tools.ai_tools import inference_tools as infer
except ModuleNotFoundError as exception:
    infer = MissingExtraMockModule('ai', exception)

try:
    from fmtr.tools.ai_tools import agentic_tools as agentic
except ModuleNotFoundError as exception:
    agentic = MissingExtraMockModule('ai.client', exception)
