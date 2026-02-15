import flet as ft
from dataclasses import dataclass
from flet.core.gesture_detector import TapEvent
from flet.core.page import Page
from flet.core.types import ColorValue, IconValue
from functools import cached_property
from typing import Optional

from corio.logging_tools import logger


class SliderSteps(ft.Slider):
    """

    Slider control using step instead of divisions

    """

    def __init__(self, *args, min=10, max=100, step=10, **kwargs):
        self.step = step
        divisions = (max - min) // step
        super().__init__(*args, min=min, max=max, divisions=divisions, **kwargs)


class Cell(ft.DataCell):
    """

    Context-aware, clickable data cell.

    """

    def __init__(self, series, column):
        """

        Store context

        """
        self.series = series
        self.column = column
        self.value = series[column]

        super().__init__(self.gesture_detector)

    @cached_property
    def text(self):
        """

        Cell contents text

        """

        return ft.Text(str(self.value), color=self.color, bgcolor=self.bgcolor)

    @property
    def color(self):
        """

        Basic conditional formatting

        """
        if self.value is None:
            return ft.Colors.GREY
        else:
            return None

    @property
    def bgcolor(self):
        """

        Basic conditional formatting

        """
        return None

    @cached_property
    def gesture_detector(self):
        """

        Make arbitrary content clickable

        """
        return ft.GestureDetector(content=self.text, on_tap=self.click_tap, on_double_tap=self.click_double_tap)

    async def click_tap(self, event: TapEvent):
        """

        Default cell click behavior — override in subclass if needed

        """
        value = await self.click(event=event)
        event.page.update()
        return value

    async def click(self, event: Optional[TapEvent] = None):
        """

        Default cell click behavior — override in subclass if needed

        """
        logger.info(f"Clicked {self.column=} {self.series.name=} {self.value=}")

    async def click_double_tap(self, event: TapEvent):
        """

        Default cell click behavior — override in subclass if needed

        """
        value = await self.double_click(event=event)
        event.page.update()
        return value

    async def double_click(self, event: Optional[TapEvent] = None):
        """

        Default cell double click behavior — override in subclass if needed

        """
        logger.info(f"Double-clicked {self.column=} {self.series.id=} {self.value=}")


class Row(ft.DataRow):
    """

    Instantiate a row from a series

    """

    TypesCells = {None: Cell}

    def __init__(self, series):
        self.series = series
        super().__init__(self.cells_controls, color=self.row_color)

    @cached_property
    def cells_data(self) -> dict[str, list[Cell]]:
        """

        Cell controls lookup

        """
        data = {}
        for col in self.series.index:
            default = self.TypesCells[None]
            TypeCell = self.TypesCells.get(col, default)
            data.setdefault(col, []).append(TypeCell(self.series, col))
        return data

    @cached_property
    def cells_controls(self) -> list[Cell]:
        """

        Flat list of controls

        """
        controls = []
        for cells in self.cells_data.values():
            for cell in cells:
                controls.append(cell)
        return controls

    def __getitem__(self, item) -> list[Cell]:
        """

        Get cells by column name

        """
        return self.cells_data[item]

    @property
    def row_color(self):
        """

        Basic conditional formatting

        """
        return None


class Column(ft.DataColumn):
    """

    Column stub

    """

    def __init__(self, col_name: str):
        """

        Store context

        """

        self.col_name = col_name

        super().__init__(label=self.text)

    @cached_property
    def text(self):
        """

        Cell contents text

        """
        return ft.Text(str(self.col_name), weight=self.weight)

    @property
    def weight(self):
        """

        Default bold headers

        """
        return ft.FontWeight.BOLD


class Table(ft.DataTable):
    """

    Dataframe with clickable cells

    """

    TypesRows = {None: Row}
    TypesColumns = {None: Column}

    def __init__(self, df):  # todo move to submodule with tabular deps
        """

        Set columns/rows using relevant types

        """
        self.df = df
        super().__init__(columns=self.columns_controls, rows=self.rows_controls)

    @cached_property
    def columns_data(self) -> dict[str, list[Column]]:
        """

        Columns controls lookup

        """
        data = {}
        for col in self.df.columns:
            default = self.TypesColumns[None]
            TypeColumn = self.TypesColumns.get(col, default)
            data.setdefault(col, []).append(TypeColumn(col))
        return data

    @cached_property
    def columns_controls(self) -> list[Column]:
        """

        Flat list of controls

        """
        controls = []
        for columns in self.columns_data.values():
            for column in columns:
                controls.append(column)
        return controls

    @cached_property
    def rows_data(self) -> dict[str, list[Row]]:
        """

        Row controls lookup

        """
        data = {}
        for index, row in self.df.iterrows():
            default = self.TypesRows[None]
            TypeRow = self.TypesRows.get(index, default)
            data.setdefault(index, []).append(TypeRow(row))
        return data

    @cached_property
    def rows_controls(self) -> list[Row]:
        """

        Flat list of controls

        """
        controls = []
        for rows in self.rows_data.values():
            for row in rows:
                controls.append(row)
        return controls

    def __getitem__(self, item) -> list[Row]:
        """

        Get row by index

        """

        return self.rows_data[item]


@dataclass
class NotificationDatum:
    """

    Color and icon for notification bar

    """
    color: ColorValue
    icon: IconValue


class NotificationBar(ft.SnackBar):
    """

    Combined logging and notification bar: infers the appropriate UI representation from the log level

    """
    DATA = {
        logger.info: NotificationDatum(color=ft.Colors.BLUE, icon=ft.Icons.INFO),
        logger.warning: NotificationDatum(color=ft.Colors.AMBER, icon=ft.Icons.WARNING),
        logger.error: NotificationDatum(color=ft.Colors.RED, icon=ft.Icons.ERROR),
        logger.debug: NotificationDatum(color=ft.Colors.GREY, icon=ft.Icons.BUG_REPORT),
        logger.exception: NotificationDatum(color=ft.Colors.RED_ACCENT, icon=ft.Icons.REPORT),
    }

    def __init__(self, msg: str, method=logger.info):
        """

        Log the message immediately, otherwise configure notification bar icon/color.

        """
        self.msg = msg
        self.method = method
        self.method(msg)

        icon = ft.Icon(self.data.icon, color=self.data.color)
        text = ft.Text(self.msg)
        content = ft.Row(controls=[icon, text])
        super().__init__(content=content)

    @cached_property
    def data(self) -> NotificationDatum:
        """

        Fetching data using logging method.

        """
        return self.DATA[self.method]

    def show(self, page: Page):
        """

        Show the notification on the relevant page.

        """
        page.open(self)
