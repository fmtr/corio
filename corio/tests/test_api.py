import asyncio
import inspect
from corio import api
from functools import cached_property


class Child(api.Base):
    TITLE = 'Sandbox Child API'
    IS_MCP = True


    def get_endpoints(self):
        """

        Sandbox child endpoints.

        """
        endpoints = [
            api.Endpoint(method_http=self.app.get, path='/pong', method=self.pong, tags='sandbox'),
        ]
        return endpoints

    async def pong(self, value: str = 'ok'):
        """

        Child ping variant.

        """
        return dict(child=value)


class SandboxApi(api.Base):
    TITLE = 'Sandbox API'
    PORT = 8001
    IS_MCP = True

    def get_endpoints(self):
        """

        Sandbox parent endpoints.

        """
        endpoints = [
            api.Endpoint(method_http=self.app.get, path='/ping', method=self.ping, tags='sandbox'),
        ]
        return endpoints

    async def ping(self, name: str = 'world'):
        """

        Parent ping endpoint.

        """
        return dict(message=f'hello {name}')

    @cached_property
    def children(self):
        """

        Immediate sandbox child APIs.

        """
        return [Child()]

def test_api_package_exports_base_symbols():
    assert api.Base.__module__ == "corio.api.api"
    assert api.Endpoint.__module__ == "corio.api.api"


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
        def get_endpoints(self):
            return [api.Endpoint(method_http=self.app.get, path="/health", method=self.health)]

        async def health(self):
            """Service health."""
            return {"ok": True}

    schema = HealthApi().app.openapi()
    operation = schema["paths"]["/health"]["get"]

    assert operation["summary"] == "Service health."
    assert operation["operationId"] == "health"


def test_mcp_import_is_local_to_mcp_property():
    source = inspect.getsource(api.Base.mcp.func)
    assert "from corio.api.mcp import FastMCP" in source


def test_mcp_mounts_for_parent_and_child():
    sandbox = SandboxApi()
    routes = {route.path for route in sandbox.app.routes if hasattr(route, "path")}

    assert "/mcp" in routes
    assert "/child" in routes
    assert callable(sandbox.app.router.lifespan_context)


def test_mcp_lifespan_wiring_includes_parent_and_child():
    sandbox = SandboxApi()
    assert len(sandbox.mcp_lifespans_flat) == 2

    parent_lifespan, parent_mcp_app = sandbox.mcp_lifespans_flat[0]
    child_lifespan, child_mcp_app = sandbox.mcp_lifespans_flat[1]

    assert callable(parent_lifespan)
    assert callable(child_lifespan)
    assert parent_mcp_app is sandbox.mcp_app
    assert child_mcp_app is sandbox.children[0].mcp_app


def test_root_lifespan_context_can_be_entered_for_mcp():
    sandbox = SandboxApi()

    async def run():
        async with sandbox.app.router.lifespan_context(sandbox.app):
            return True

    assert asyncio.run(run()) is True
