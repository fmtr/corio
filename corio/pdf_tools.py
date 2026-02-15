import pymupdf as pm
import pymupdf4llm
from typing import List, Tuple, Dict, Any, Self

from corio import data_modelling_tools


class BoundingBox(data_modelling_tools.Base):
    left: float
    top: float
    right: float
    bottom: float

    @property
    def order(self):
        """

        Approximate natural reading order

        """
        return (self.top, self.left), (self.bottom, self.right)

    @property
    def rect(self) -> pm.Rect:
        """

        Position as a PyMuPDF Rect

        """
        return pm.Rect(self.left, self.top, self.right, self.bottom)

    @classmethod
    def from_dict(cls, data: Tuple[float]) -> Self:
        """

        Instantiate from PyMuPDF dictionary data

        """
        data = {key: value for key, value in zip(cls.model_fields.keys(), data)}
        return cls(**data)


class Span(data_modelling_tools.Base):
    size: float
    flags: int
    font: str
    color: int
    ascender: float
    descender: float
    text: str
    origin: Tuple[float, float]
    bbox: BoundingBox

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        data['bbox'] = BoundingBox.from_dict(data['bbox'])
        return cls(**data)


class Line(data_modelling_tools.Base):
    spans: List[Span]
    wmode: int
    dir: Tuple[float, float]
    bbox: BoundingBox

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Line':
        """

        Instantiate from PyMuPDF dictionary data

        """
        data['spans'] = [Span.from_dict(span) for span in data['spans']]
        data['bbox'] = BoundingBox.from_dict(data['bbox'])
        return cls(**data)

    @property
    def text(self) -> str:
        """

        Simple text representation

        """
        return ' '.join([span.text for span in self.spans])


class Block(data_modelling_tools.Base):
    number: int
    type: int
    bbox: BoundingBox
    lines: List[Line]

    @property
    def text(self) -> str:
        """

        Simple text representation

        """
        return ' '.join([line.text for line in self.lines])

    @classmethod
    def from_dict(cls, data: Dict) -> Self:
        """

        Instantiate from PyMuPDF dictionary data

        """
        data['lines'] = [Line.from_dict(line) for line in data['lines']]
        data['bbox'] = BoundingBox.from_dict(data['bbox'])
        return cls(**data)

    @property
    def rect(self) -> pm.Rect:
        """

        Position as a PyMuPDF Rect

        """
        return self.bbox.rect


class Page(data_modelling_tools.Base):
    number: int
    width: float
    height: float
    blocks: List[Block]

    @property
    def text(self) -> str:
        """

        Simple text representation

        """
        return ' '.join([block.text for block in self.blocks])

    @classmethod
    def from_dict(cls, data: Dict) -> Self:
        """

        Instantiate from PyMuPDF dictionary data

        """

        data['blocks'] = [Block.from_dict(block) for block in data['blocks']]
        return cls(**data)

class Document(pm.Document):
    """

    Subclassed Document object with data-modelled elements property and markdown conversion.

    """

    @property
    def data(self) -> List[Page]:
        """

        Get representation of Document elements as Python objects.

        """

        pages = []

        for page_pm in self:
            data = page_pm.get_text("dict", flags=pm.TEXTFLAGS_TEXT | pm.TEXT_ACCURATE_BBOXES)
            data['number'] = page_pm.number
            page = Page.from_dict(data)
            pages.append(page)

        return pages

    def to_markdown(self, **kwargs) -> str:
        """

        Markdown output via `pymupdf4llm`

        """
        return pymupdf4llm.to_markdown(self, **kwargs)

    def to_text_pages(self) -> List[str]:
        """

        Simple text output per-page.

        """
        lines = []
        for page in self:
            text = page.get_text()
            lines.append(text)

        return lines

    def to_text(self) -> str:
        """

        Simple text output.

        """

        text = '\n'.join(self.to_text_pages())
        return text

    def split(self) -> List[Self]:
        """

        Split pages into individual documents.

        """

        documents = []
        for i, page in enumerate(self, start=1):
            document = self.__class__()
            document.insert_pdf(self, from_page=i, to_page=i)
            documents.append(document)

        return documents

if __name__ == '__main__':
    from corio.path_tools import Path

    PATH_DATA = Path.data()
    # PATH_PDF=PATH_DATA/'chib.pdf'
    PATH_PDF = PATH_DATA / 'kvm.pdf'
    assert PATH_PDF.exists()

    doc = Document(PATH_PDF)
    data = doc.data
    md = doc.to_markdown()
    md
