from dataclasses import dataclass

from flet.core.page import Page


@dataclass
class Context:
    """

    Base context class

    """
    page: Page
