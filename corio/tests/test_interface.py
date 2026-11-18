import os
import struct
import zlib
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

import flet as ft
import pytest
from pydantic import ValidationError
from flet.fastapi import FletStaticFiles
from starlette.applications import Starlette
from starlette.testclient import TestClient

from corio import function, interface, path
from corio.paths import paths
from corio.interface import interface as interface_module


@dataclass
class SyntheticContext(interface.Context):
    marker: str = "synthetic-context"


@pytest.fixture
def synthetic_png():
    def chunk(kind, data):
        chunk_type = kind.encode()
        checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", checksum)
        )

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    pixels = zlib.compress(bytes((0, 34, 68, 102, 255)))
    image = b"\x89PNG\r\n\x1a\n"
    image += chunk("IHDR", header)
    image += chunk("IDAT", pixels)
    image += chunk("IEND", b"")
    return image


@pytest.mark.asyncio
async def test_base_new_applies_declarative_settings_context_and_single_root():
    theme = ft.Theme()
    calls = {"route": [], "pop": [], "connect": [], "disconnect": []}

    class ConfiguredInterface(interface.Base[SyntheticContext]):
        HOST = "127.0.0.9"
        PORT = 9234
        SCROLL = ft.ScrollMode.AUTO
        TypeContext = SyntheticContext

        @function.ccp
        def metadata(cls):
            return interface.Metadata(
                name="Synthetic Interface",
                short_name="Synthetic",
            )

        @classmethod
        def get_theme(cls):
            return theme

        @classmethod
        def route(cls, event):
            calls["route"].append(event)

        @classmethod
        def pop(cls, event):
            calls["pop"].append(event)

        @classmethod
        def on_connect(cls, event):
            calls["connect"].append(event)

        @classmethod
        def on_disconnect(cls, event):
            calls["disconnect"].append(event)

        def __init__(self):
            super().__init__(controls=[ft.Text("synthetic root child")])

    existing_control = object()
    page = SimpleNamespace(controls=[existing_control], update=Mock())

    root = await ConfiguredInterface.new(page)

    assert isinstance(root, ConfiguredInterface)
    assert isinstance(root, ft.Column)
    assert isinstance(root.context, SyntheticContext)
    assert root.context.page is page
    assert root.context.marker == "synthetic-context"
    assert root.controls[0].value == "synthetic root child"
    assert page.controls == [existing_control, root]
    assert page.scroll is ConfiguredInterface.SCROLL
    assert page.title == ConfiguredInterface.metadata.name
    assert page.theme is theme
    assert page.on_route_change == ConfiguredInterface.route
    assert page.on_view_pop == ConfiguredInterface.pop
    assert page.on_connect == ConfiguredInterface.on_connect
    assert page.on_disconnect == ConfiguredInterface.on_disconnect
    page.update.assert_called_once_with()

    route_event = object()
    popped_view = object()
    pop_event = SimpleNamespace(route="/synthetic", view=popped_view, page=page)
    connect_event = object()
    disconnect_event = object()
    page.on_route_change(route_event)
    page.on_view_pop(pop_event)
    page.on_connect(connect_event)
    page.on_disconnect(disconnect_event)

    assert calls == {
        "route": [route_event],
        "pop": [pop_event],
        "connect": [connect_event],
        "disconnect": [disconnect_event],
    }


def test_base_pop_accepts_a_flet_view_pop_event(monkeypatch):
    monkeypatch.setattr(interface_module.logger, "debug", Mock())
    page = SimpleNamespace(route="/synthetic-current", views=[object()])
    event = SimpleNamespace(
        route="/synthetic-popped",
        view=object(),
        page=page,
    )

    interface.Base.pop(event)

    interface_module.logger.debug.assert_called_once()


def test_metadata_requires_a_full_name():
    with pytest.raises(ValidationError):
        interface.Metadata()


def test_base_metadata_defaults_and_class_property_override():
    class DefaultInterface(interface.Base):
        pass

    class SpecializedInterface(DefaultInterface):
        PORT = 9317

        @function.ccp
        def metadata(cls):
            return interface.Metadata(
                name="Synthetic Specialized Interface",
                short_name="Synthetic",
            )

    assert DefaultInterface.metadata.name == "DefaultInterface"
    assert DefaultInterface.metadata.short_name is None
    assert DefaultInterface.metadata.theme_color == "#FF005F"
    assert DefaultInterface.metadata.background_color == "#FFFFFF"
    assert DefaultInterface.metadata.start_url == "."
    assert DefaultInterface.metadata.display == "standalone"
    assert [icon.src for icon in DefaultInterface.metadata.icons] == [
        "icons/icon-192.png",
        "icons/icon-512.png",
        "icons/icon-maskable-192.png",
        "icons/icon-maskable-512.png",
    ]
    assert DefaultInterface.HOST
    assert DefaultInterface.PORT
    assert DefaultInterface.APPVIEW is ft.AppView.WEB_BROWSER
    assert DefaultInterface.PATH_ASSETS == paths.assets / "interface"
    assert SpecializedInterface.metadata.name == "Synthetic Specialized Interface"
    assert SpecializedInterface.metadata.short_name == "Synthetic"
    assert SpecializedInterface.HOST == DefaultInterface.HOST
    assert SpecializedInterface.PORT == 9317
    assert SpecializedInterface.APPVIEW is DefaultInterface.APPVIEW


def test_base_launch_uses_overridden_runtime_settings_and_creates_manifest(
    monkeypatch, tmp_path
):
    app_runner = Mock()
    monkeypatch.setattr(ft, "run", app_runner)
    monkeypatch.delenv("FLET_SECRET_KEY", raising=False)

    class LaunchInterface(interface.Base):
        HOST = "127.0.0.8"
        PORT = 9431
        PATH_ASSETS = path.Path(tmp_path) / "synthetic-assets"
        PATH_UPLOADS = "synthetic-uploads"
        APPVIEW = ft.AppView.WEB_BROWSER

        @function.ccp
        def metadata(cls):
            return interface.Metadata(
                name="Synthetic Launch Interface",
                short_name="Synthetic Launch",
                description="A synthetic Flet app.",
                theme_color="#123456",
                background_color="#ABCDEF",
            )

    LaunchInterface.launch()

    secret = os.environ["FLET_SECRET_KEY"]
    manifest_path = LaunchInterface.PATH_ASSETS / "manifest.json"
    manifest = manifest_path.read_json()
    assert len(secret) == 24
    assert all(character in "0123456789abcdef" for character in secret)
    assert manifest["name"] == LaunchInterface.metadata.name
    assert manifest["short_name"] == LaunchInterface.metadata.short_name
    assert manifest["description"] == LaunchInterface.metadata.description
    assert manifest["theme_color"] == LaunchInterface.metadata.theme_color
    assert manifest["background_color"] == LaunchInterface.metadata.background_color
    assert manifest["icons"]
    app_runner.assert_called_once_with(
        LaunchInterface.new,
        view=LaunchInterface.APPVIEW,
        host=LaunchInterface.HOST,
        port=LaunchInterface.PORT,
        assets_dir=str(LaunchInterface.PATH_ASSETS),
        upload_dir=LaunchInterface.PATH_UPLOADS,
    )


def test_base_launch_preserves_an_existing_secret(monkeypatch, tmp_path):
    app_runner = Mock()
    monkeypatch.setattr(ft, "run", app_runner)
    monkeypatch.setenv("FLET_SECRET_KEY", "synthetic-existing-secret")
    monkeypatch.setattr(interface.Base, "PATH_ASSETS", path.Path(tmp_path) / "assets")

    interface.Base.launch()

    manifest = (interface.Base.PATH_ASSETS / "manifest.json").read_json()
    assert manifest["name"] == "Base"
    assert "short_name" not in manifest
    assert os.environ["FLET_SECRET_KEY"] == "synthetic-existing-secret"
    app_runner.assert_called_once_with(
        interface.Base.new,
        view=interface.Base.APPVIEW,
        host=interface.Base.HOST,
        port=interface.Base.PORT,
        assets_dir=str(interface.Base.PATH_ASSETS),
        upload_dir=interface.Base.PATH_UPLOADS,
    )


def test_flet_static_files_serve_custom_assets_from_metadata_model(
    tmp_path, synthetic_png
):
    assets_dir = tmp_path / "assets"
    icons_dir = assets_dir / "icons"
    icons_dir.mkdir(parents=True)
    manifest_path = assets_dir / "manifest.json"
    manifest_path.write_text('{"name": "stale manifest"}', encoding="utf-8")
    png = synthetic_png
    asset_paths = [
        "favicon.png",
        "icons/apple-touch-icon-192.png",
        "icons/icon-192.png",
        "icons/icon-512.png",
        "icons/icon-maskable-192.png",
        "icons/icon-maskable-512.png",
        "icons/loading-animation.png",
    ]
    for asset_path in asset_paths:
        (assets_dir / asset_path).write_bytes(png)

    class BrandedMetadata(interface.Metadata):
        custom_metadata: str

    class BrandedInterface(interface.Base):
        PATH_ASSETS = path.Path(assets_dir)

        @function.ccp
        def metadata(cls):
            return BrandedMetadata(
                name="Synthetic Product",
                short_name="Synth",
                description="A synthetic product description.",
                theme_color="#224466",
                background_color="#F0F2F4",
                start_url="/custom-start",
                display="fullscreen",
                custom_metadata="model-defined metadata",
                icons=[
                    interface.ManifestIcon(
                        src="icons/icon-192.png",
                        sizes="192x192",
                    )
                ],
            )

    assert BrandedInterface.prep_assets() is None
    app = Starlette()
    app.mount("/", FletStaticFiles(assets_dir=str(BrandedInterface.PATH_ASSETS)))

    with TestClient(app) as client:
        index = client.get("/")
        manifest = client.get("/manifest.json").json()
        served_assets = {
            asset_path: client.get(f"/{asset_path}")
            for asset_path in asset_paths
        }

    assert "favicon.png" in index.text
    assert "icons/loading-animation.png" in index.text
    assert manifest["name"] == BrandedInterface.metadata.name
    assert manifest["short_name"] == BrandedInterface.metadata.short_name
    assert manifest["description"] == BrandedInterface.metadata.description
    assert manifest["theme_color"] == BrandedInterface.metadata.theme_color
    assert manifest["background_color"] == BrandedInterface.metadata.background_color
    assert manifest["start_url"] == BrandedInterface.metadata.start_url
    assert manifest["display"] == BrandedInterface.metadata.display
    assert manifest["custom_metadata"] == BrandedInterface.metadata.custom_metadata
    assert manifest["icons"] == [
        {
            "src": "icons/icon-192.png",
            "sizes": "192x192",
            "type": "image/png",
        }
    ]
    assert all(response.status_code == 200 for response in served_assets.values())
    assert all(response.content == png for response in served_assets.values())


def test_update_decorator_preserves_result_and_updates_page_once():
    class Target:
        def __init__(self):
            self.page = SimpleNamespace(update=Mock())

        @interface.update()
        def perform(self, value):
            return f"result:{value}"

    target = Target()

    assert target.perform("synthetic") == "result:synthetic"
    target.page.update.assert_called_once_with()


def test_slider_steps_maps_step_size_to_flet_divisions():
    slider = interface.controls.SliderSteps(min=20, max=80, step=15, value=35)

    assert slider.min == 20
    assert slider.max == 80
    assert slider.divisions == 4
    assert slider.step == 15


def test_notification_bar_uses_the_current_page_dialog_api():
    page = SimpleNamespace(show_dialog=Mock())
    notification = interface.controls.NotificationBar("Synthetic notification")

    notification.show(page)

    page.show_dialog.assert_called_once_with(notification)


def test_progress_decorator_brackets_work_with_visible_state_and_page_updates():
    class Target:
        def __init__(self):
            self.page = SimpleNamespace(update=Mock())
            self.progress = SimpleNamespace(visible=False)

        @interface.progress()
        def perform(self):
            assert self.progress.visible
            return "synthetic result"

    target = Target()

    assert target.perform() == "synthetic result"
    assert target.progress.visible is False
    assert target.page.update.call_count == 2
