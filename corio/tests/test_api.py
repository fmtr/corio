from __future__ import annotations

import asyncio
import inspect
from contextlib import asynccontextmanager
from functools import cached_property

from corio import api


class Child(api.Base):
    TITLE = 'Sandbox Child API'

    @property
    def ENDPOINTS(self):
        return [Pong, ChildTool]


class SandboxApi(api.Base):
    TITLE = 'Sandbox API'
    PORT = 8001

    @property
    def ENDPOINTS(self):
        return [Ping, ParentTool]

    @cached_property
    def children(self):
        """

        Immediate sandbox child APIs.

        """
        return [Child()]


class Pong(api.endpoint.API):
    """

    Child ping variant.

    """

    PATH = "/pong"
    TAGS = "sandbox"

    async def run(self, value: str = "ok"):
        return dict(child=value)


class Ping(api.endpoint.API):
    """

    Parent ping endpoint.

    """

    PATH = "/ping"
    TAGS = "sandbox"

    async def run(self, name: str = "world"):
        return dict(message=f"hello {name}")


class ChildTool(api.endpoint.Tool):
    async def run(self):
        return dict(child="ok")


class ParentTool(api.endpoint.Tool):
    async def run(self):
        return dict(parent="ok")


def test_api_package_exports_base_symbols():
    assert api.Base.__module__ == "corio.api.api"
    assert api.endpoint.Base.__module__ == "corio.api.endpoint"
    assert api.endpoint.API.__module__ == "corio.api.endpoint"
    assert api.endpoint.MCP.__module__ == "corio.api.endpoint"


def test_base_url_prefix_default_and_override():
    class DefaultApi(api.Base):
        pass

    class PrefixedApi(api.Base):
        URL_PREFIX = "/custom"

    assert DefaultApi().url_prefix == "/defaultapi"
    assert PrefixedApi().url_prefix == "/custom"


def test_base_description_uses_immediate_children():
    class ChildApi(api.Base):
        TITLE = "Child API"
        URL_PREFIX = "/child"

    class ParentApi(api.Base):
        @cached_property
        def children(self):
            return [ChildApi()]

    description = ParentApi().description
    assert description == "### APIs\n\n- [Child API](/child)"


def test_base_description_is_none_without_children():
    class NoChildrenApi(api.Base):
        pass

    assert NoChildrenApi().description is None


def test_endpoint_registration_sets_openapi_summary_and_operation_id():
    class HealthApi(api.Base):
        @property
        def ENDPOINTS(self):
            return [Health]

    class Health(api.endpoint.API):
        """Service health."""

        PATH = "/health"

        async def run(self):
            return {"ok": True}

    schema = HealthApi().app.openapi()
    operation = schema["paths"]["/health"]["get"]

    assert operation["summary"] == "Service health."
    assert operation["operationId"] == "health"


def test_mcp_description_uses_endpoint_class_docstring():
    class DummyApi:
        pass

    class DemoTool(api.endpoint.Tool):
        """

        Demo tool docs.

        """

        async def run(self):
            return "ok"

    assert DemoTool(DummyApi()).description == "Demo tool docs."


def test_mcp_import_is_local_to_mcp_property():
    source = inspect.getsource(api.Base.mcp.func)
    assert "from fastmcp import FastMCP" in source


def test_mcp_transforms_are_added_from_base_property():
    calls = []

    class DummyHttpApp:
        @staticmethod
        @asynccontextmanager
        async def lifespan(_app):
            yield

        async def __call__(self, _scope, _receive, _send):
            return None

    class DummyMCP:
        def tool(self, **_kwargs):
            def register(func):
                return func
            return register

        def add_transform(self, transform):
            calls.append(transform)

        def http_app(self, path='/'):
            assert path == '/'
            return DummyHttpApp()

    class DemoTool(api.endpoint.Tool):
        async def run(self):
            return "ok"

    class TransformA:
        def __init__(self, mcp):
            self.mcp = mcp

    class TransformB:
        def __init__(self, mcp):
            self.mcp = mcp

    class TransformApi(api.Base):
        @cached_property
        def ENDPOINTS(self):
            return [DemoTool]

        @cached_property
        def TRANSFORMS(self):
            return [TransformA, TransformB]

        @cached_property
        def mcp(self):
            return DummyMCP()

    instance = TransformApi()
    assert len(calls) == 2
    assert isinstance(calls[0], TransformA)
    assert isinstance(calls[1], TransformB)
    assert calls[0].mcp is instance.mcp
    assert calls[1].mcp is instance.mcp


def test_mcp_mounts_for_parent_and_child():
    sandbox = SandboxApi()
    routes = {route.path for route in sandbox.app.routes if hasattr(route, "path")}

    assert "/mcp" in routes
    assert "/child" in routes
    assert callable(sandbox.app.router.lifespan_context)


def test_mcp_lifespan_wiring_includes_parent_and_child():
    sandbox = SandboxApi()
    assert len(sandbox.mcp_lifespans_flat) == 2

    parent_lifespan, _parent_mcp_app = sandbox.mcp_lifespans_flat[0]
    child_lifespan, _child_mcp_app = sandbox.mcp_lifespans_flat[1]

    assert callable(parent_lifespan)
    assert callable(child_lifespan)


def test_root_lifespan_context_can_be_entered_for_mcp():
    sandbox = SandboxApi()

    async def run():
        async with sandbox.app.router.lifespan_context(sandbox.app):
            return True

    assert asyncio.run(run()) is True


def test_mcp_endpoint_tool_register_uses_named_tool():
    calls = []

    class DummyMCP:
        def tool(self, **kwargs):
            calls.append(("tool", kwargs))

            def register(func):
                calls.append(("tool_register", func.__name__))
                return func

            return register

    class DemoTool(api.endpoint.Tool):
        async def run(self):
            return "ok"

    class DummyApi:
        def __init__(self):
            self.mcp = DummyMCP()

    endpoint = DemoTool(DummyApi())
    endpoint.register()

    assert calls[0] == ("tool", {"name": "demo_tool", "description": None, "app": False})
    assert calls[1] == ("tool_register", "run")


def test_mcp_endpoint_ui_registers_as_app_tool():
    calls = []

    class DummyMCP:
        def tool(self, **kwargs):
            calls.append(("tool", kwargs))

            def register(func):
                calls.append(("tool_register", func.__name__))
                return func

            return register

    class DemoUI(api.endpoint.UI):
        async def run(self):
            return "ok"

    class DummyApi:
        def __init__(self):
            self.mcp = DummyMCP()

    endpoint = DemoUI(DummyApi())
    endpoint.register()

    assert calls[0] == ("tool", {"name": "demo_ui", "description": None, "app": True})
    assert calls[1] == ("tool_register", "run")


def test_mcp_endpoint_prompt_register_uses_named_prompt():
    calls = []

    class DummyMCP:
        def prompt(self, **kwargs):
            calls.append(("prompt", kwargs))

            def register(func):
                calls.append(("prompt_register", func.__name__))
                return func

            return register

    class DemoPrompt(api.endpoint.Prompt):
        async def run(self):
            return "ok"

    class DummyApi:
        def __init__(self):
            self.mcp = DummyMCP()

    endpoint = DemoPrompt(DummyApi())
    endpoint.register()

    assert calls[0] == ("prompt", {"name": "demo_prompt"})
    assert calls[1] == ("prompt_register", "run")


def test_mcp_endpoint_resource_register_uses_uri():
    calls = []

    class DummyMCP:
        def resource(self, **kwargs):
            calls.append(("resource", kwargs))

            def register(func):
                calls.append(("resource_register", func.__name__))
                return func

            return register

    class DemoResource(api.endpoint.Resource):
        URI = "resource://demo/{id}"

        async def run(self, id: str):
            return id

    class DummyApi:
        def __init__(self):
            self.mcp = DummyMCP()

    endpoint = DemoResource(DummyApi())
    endpoint.register()

    assert calls[0] == ("resource", {"uri": "resource://demo/{id}"})
    assert calls[1] == ("resource_register", "run")
