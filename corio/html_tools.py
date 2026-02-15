import html2text
from functools import lru_cache


@lru_cache
def get_parser():
    """
    
    Get an HTML2TEXT parser
     
    """
    parser = html2text.HTML2Text()
    parser.ignore_links = True
    return parser


def to_text(html):
    """

    Simple convertion a HTML document to a plain text.

    """
    parser = get_parser()
    text = parser.handle(html).strip()
    return text
