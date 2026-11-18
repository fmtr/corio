import os
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

import flet as ft
import pytest

from corio import interface
from corio.interface import interface as interface_module


@dataclass
class SyntheticContext(interface.Context):
    marker: str = "synthetic-context"


@pytest.mark.asyncio
async def test_base_new_applies_declarative_settings_context_and_single_root():
    theme = ft.Theme()
    calls = {"route": [], "pop": [], "connect": [], "disconnect": []}

    class ConfiguredInterface(interface.Base[SyntheticContext]):
        TITLE = "Synthetic Interface"
        HOST = "127.0.0.9"
        PORT = 9234
        SCROLL = ft.ScrollMode.AUTO
        TypeContext = SyntheticContext

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
    assert page.title == ConfiguredInterface.TITLE
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


def test_base_defaults_are_inherited_and_subclass_values_override_them():
    class DefaultInterface(interface.Base):
        pass

    class SpecializedInterface(DefaultInterface):
        TITLE = "Synthetic Specialized Interface"
        PORT = 9317

    assert DefaultInterface.TITLE
    assert DefaultInterface.HOST
    assert DefaultInterface.PORT
    assert DefaultInterface.APPVIEW is ft.AppView.WEB_BROWSER
    assert DefaultInterface.SCROLL is ft.ScrollMode.AUTO
    assert SpecializedInterface.TITLE == "Synthetic Specialized Interface"
    assert SpecializedInterface.HOST == DefaultInterface.HOST
    assert SpecializedInterface.PORT == 9317
    assert SpecializedInterface.APPVIEW is DefaultInterface.APPVIEW


def test_base_launch_uses_overridden_runtime_settings_and_creates_secret(monkeypatch):
    app_runner = Mock()
    monkeypatch.setattr(ft, "run", app_runner)
    monkeypatch.delenv("FLET_SECRET_KEY", raising=False)

    class LaunchInterface(interface.Base):
        TITLE = "Synthetic Launch Interface"
        HOST = "127.0.0.8"
        PORT = 9431
        PATH_ASSETS = "synthetic-assets"
        PATH_UPLOADS = "synthetic-uploads"
        APPVIEW = ft.AppView.WEB_BROWSER

    LaunchInterface.launch()

    secret = os.environ["FLET_SECRET_KEY"]
    assert len(secret) == 24
    assert all(character in "0123456789abcdef" for character in secret)
    app_runner.assert_called_once_with(
        LaunchInterface.new,
        view=LaunchInterface.APPVIEW,
        host=LaunchInterface.HOST,
        port=LaunchInterface.PORT,
        assets_dir=LaunchInterface.PATH_ASSETS,
        upload_dir=LaunchInterface.PATH_UPLOADS,
    )


def test_base_launch_preserves_an_existing_secret(monkeypatch):
    app_runner = Mock()
    monkeypatch.setattr(ft, "run", app_runner)
    monkeypatch.setenv("FLET_SECRET_KEY", "synthetic-existing-secret")

    interface.Base.launch()

    assert os.environ["FLET_SECRET_KEY"] == "synthetic-existing-secret"
    app_runner.assert_called_once_with(
        interface.Base.new,
        view=interface.Base.APPVIEW,
        host=interface.Base.HOST,
        port=interface.Base.PORT,
        assets_dir=interface.Base.PATH_ASSETS,
        upload_dir=interface.Base.PATH_UPLOADS,
    )


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
