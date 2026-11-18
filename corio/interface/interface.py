import os
from typing import Generic, Type, TypeVar

import flet as ft

from corio import dm, env, function, path
from corio.paths import paths
from corio.constants import Constants
from corio.interface.context import Context
from corio.logs import logger


class update(function.MethodDecorator):
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


class ManifestIcon(dm.Base):
    src: str
    sizes: str
    type: str = 'image/png'
    purpose: str | None = None


class Metadata(dm.Base):
    name: str
    short_name: str | None = None
    start_url: str = '.'
    display: str = 'standalone'
    background_color: str = '#FFFFFF'
    theme_color: str = '#FF005F'
    description: str | None = None
    orientation: str = 'natural'
    prefer_related_applications: bool = False
    icons: list[ManifestIcon] = [
        ManifestIcon(src='icons/icon-192.png', sizes='192x192'),
        ManifestIcon(src='icons/icon-512.png', sizes='512x512'),
        ManifestIcon(
            src='icons/icon-maskable-192.png',
            sizes='192x192',
            purpose='maskable',
        ),
        ManifestIcon(
            src='icons/icon-maskable-512.png',
            sizes='512x512',
            purpose='maskable',
        ),
    ]


class Base(Generic[T], ft.Column):
    """

    Simple interface base class with Flet web identity and asset defaults.

    """
    HOST = '0.0.0.0'
    PORT = 8000
    URL = Constants.FMTR_DEV_INTERFACE_URL if env.IS_DEV else None
    APPVIEW = ft.AppView.WEB_BROWSER
    PATH_ASSETS: path.Path = paths.assets / 'interface'
    PATH_UPLOADS = None
    SCROLL = ft.ScrollMode.AUTO

    SECRET_KEY_KEY = 'FLET_SECRET_KEY'
    ROUTE_ROOT = '/'

    TypeContext: Type[T] = Context

    @function.ccp
    def metadata(cls) -> Metadata:
        """

        Return the default manifest metadata for this interface.

        """
        return Metadata(name=cls.__name__)

    @classmethod
    def prep_assets(cls) -> None:
        """

        Create the configured assets directory and write its manifest.

        """
        cls.PATH_ASSETS.mkdirf()
        manifest_path = cls.PATH_ASSETS / 'manifest.json'
        manifest_path.write_json(
            cls.metadata.model_dump(mode='json', exclude_none=True)
        )

    @classmethod
    async def new(cls, page: ft.Page):
        """

        Interface entry point/async constructor. Set relevant callbacks, and add instantiated self to page views.

        Override this to work with `Context`, do async setup. Otherwise, override __init__ (which is regular Column __init__) for a simple interface.

        """
        page.scroll = cls.SCROLL
        page.title = cls.metadata.name
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
    def pop(cls, event: ft.ViewPopEvent):
        """

        Overridable view pop.

        """
        logger.debug(f'View popped: {event.route=} {len(event.page.views)=} {event.view=}')

    @classmethod
    def on_connect(cls, event: ft.ControlEvent):
        """

        Log connections

        """
        page = event.control
        logger.warning(f'Connect: {page.client_user_agent=} {page.platform.name=}')

    @classmethod
    def on_disconnect(cls, event: ft.ControlEvent):
        """

        Log disconnections

        """
        page = event.control
        logger.warning(f'Disconnect {page.client_user_agent=} {page.platform.name=}')


    @classmethod
    def get_theme(cls):
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

        if not env.get(cls.SECRET_KEY_KEY, default=None):
            os.environ["FLET_SECRET_KEY"] = os.urandom(12).hex()

        logger.info(f"Launching {cls.metadata.name} at {url}")
        cls.prep_assets()
        ft.run(
            cls.new,
            view=cls.APPVIEW,
            host=cls.HOST,
            port=cls.PORT,
            assets_dir=str(cls.PATH_ASSETS),
            upload_dir=cls.PATH_UPLOADS,
        )


class Test(Base[Context]):
    """

    Simple test interface, showing typing example.

    """
    TypeContext: Type[Context] = Context

    def __init__(self):
        controls = [ft.Text(self.metadata.name)]
        super().__init__(controls=controls)
