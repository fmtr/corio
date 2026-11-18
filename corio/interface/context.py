from dataclasses import dataclass

import flet as ft


@dataclass
class Context:
    """

    Base context class

    """
    page: ft.Page
