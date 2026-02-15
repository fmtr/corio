import flet as ft
import os
from flet.core.control_event import ControlEvent
from flet.core.types import AppView
from flet.core.view import View
from typing import TypeVar, Generic, Type

from corio import environment_tools
from corio.constants import Constants
from corio.function_tools import MethodDecorator
from corio.interface_tools.context import Context
from corio.logging_tools import logger


class update(MethodDecorator):
    """

    Update the page after the decorated function is called.

    """

    def stop(self, instance, *args, **kwargs):
        instance.page.update()


class progress(update):
    """

    Run the function while a progress indicator (e.g. spinner) is and within the object-defined context (e.g. logging span).

    """

    def start(self, instance, *args, **kwargs):
        """

        Make progress visible and update.

        """
        instance.progress.visible = True
        instance.page.update()

    def stop(self, instance, *args, **kwargs):
        """

         Make progress not visible and update.

        """
        instance.progress.visible = False
        super().stop(instance)


T = TypeVar('T', bound=Context)


class Base(Generic[T], ft.Column):
    """

    Simple interface base class.

    """
    TITLE = 'Base Interface'
    HOST = '0.0.0.0'
    PORT = 8080
    URL = Constants.FMTR_DEV_INTERFACE_URL if environment_tools.IS_DEV else None
    APPVIEW = AppView.WEB_BROWSER
    PATH_ASSETS = None
    PATH_UPLOADS = None
    SCROLL = ft.ScrollMode.AUTO

    SECRET_KEY_KEY = 'FLET_SECRET_KEY'
    ROUTE_ROOT = '/'

    TypeContext: Type[T] = Context

    @classmethod
    async def new(cls, page: ft.Page):
        """

        Interface entry point/async constructor. Set relevant callbacks, and add instantiated self to page views.

        Override this to work with `Context`, do async setup. Otherwise, override __init__ (which is regular Column __init__) for a simple interface.

        """
        page.scroll = cls.SCROLL
        page.title = cls.TITLE
        page.on_connect = cls.on_connect
        page.on_disconnect = cls.on_disconnect
        page.on_route_change = cls.route
        page.on_view_pop = cls.pop
        page.theme = cls.get_theme()

        context = cls.TypeContext(page=page)
        self = cls()
        self.context = context

        page.controls.append(self)
        page.update()

        return self

    @classmethod
    def route(cls, event: ft.RouteChangeEvent):
        """

        Overridable router.

        """
        logger.debug(f'Route change: {event=}')

    @classmethod
    def pop(cls, view: View, page: ft.Page):
        """

        Overridable view pop.

        """
        logger.debug(f'View popped: {page.route=} {len(page.views)=} {view=}')

    @classmethod
    def on_connect(cls, event: ControlEvent):
        """

        Log connections

        """
        page = event.control
        logger.warning(f'Connect: {page.client_user_agent=} {page.platform.name=}')

    @classmethod
    def on_disconnect(cls, event: ControlEvent):
        """

        Log disconnections

        """
        page = event.control
        logger.warning(f'Disconnect {page.client_user_agent=} {page.platform.name=}')


    @classmethod
    def get_theme(self):
        """

        Overridable theme definition

        """
        text_style = ft.TextStyle(size=20)
        theme = ft.Theme(
            text_theme=ft.TextTheme(body_large=text_style),
        )
        return theme

    @classmethod
    def launch(cls):
        """

        Launch via async constructor method

        """

        if cls.URL:
            url = cls.URL
        else:
            url = f'http://{cls.HOST}:{cls.PORT}'

        if not environment_tools.get(cls.SECRET_KEY_KEY, default=None):
            os.environ["FLET_SECRET_KEY"] = os.urandom(12).hex()

        logger.info(f"Launching {cls.TITLE} at {url}")
        ft.app(cls.new, view=cls.APPVIEW, host=cls.HOST, port=cls.PORT, assets_dir=cls.PATH_ASSETS, upload_dir=cls.PATH_UPLOADS)


class Test(Base[Context]):
    """

    Simple test interface, showing typing example.

    """
    TypeContext: Type[Context] = Context

    TITLE = 'Test Interface'

    def __init__(self):
        controls = [ft.Text(self.TITLE)]
        super().__init__(controls=controls)

if __name__ == "__main__":
    Test.launch()
