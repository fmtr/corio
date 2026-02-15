from functools import lru_cache

from tinynetrc import Netrc

LOGIN = 'login'
PASSWORD = 'password'


class Netrc(Netrc):

    def __init__(self, file=None):
        if not file:
            from pathlib import Path

            path = Path.home() / ".netrc"
            path.touch(exist_ok=True)

        super().__init__(file=file)

@lru_cache
def get():
    return Netrc()
