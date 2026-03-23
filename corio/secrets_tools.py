from dataclasses import dataclass
from functools import cached_property
from typing import Generator, Self

from corio.encryption_tools import EncryptorValuesSelect, EncryptorValues
from corio.logging_tools import logger
from corio.path_tools import Path


@dataclass
class Definition:
    """

    Pair of lists of files - and the nodes to encrypt within those files

    """
    files: list[str]
    nodes: list[str]

    @cached_property
    def encryptor(self) -> EncryptorValuesSelect:
        """

        Create encryptor with only the nodes specified

        """
        return EncryptorValuesSelect(nodes=self.nodes)

    def encrypt(self, base: Path) -> Generator[Path, None, None]:
        """

        For each file, check whether its contents have changed since it was last encrypted, and re-encrypt if so.

        """

        paths_red = []
        for path_red in self.files:
            paths_red += list(base.glob(path_red))

        for path_red in paths_red:

            red = path_red.read_data()
            black = self.encryptor.encrypt(red)
            red_robin = self.encryptor.decrypt(black)

            if red != red_robin:
                raise ValueError(f'Round-robin mismatch: {path_red=}')

            path_black = path_red.parent / Path(path_red.stem).with_suffix(f'.black.yml')

            if path_black.exists():
                black_robin = path_black.read_data()
                red_robin = self.encryptor.decrypt(black_robin)
                if red_robin == red:
                    logger.info(f'No change: {path_black=}')
                    continue

            logger.info(f'Writing new black: {path_black=}')
            path_black.write_yaml(black)
            yield path_black

    @classmethod
    def from_data(cls, data: dict) -> Self:
        """

        Initialise from dict

        """
        self = cls(**data)
        return self


@dataclass
class SecretsDefinitions:
    """

    Secrets encryptions definitions file in repo root

    """

    FILENAME = 'secrets.yml'
    definitions: list[Definition]

    def encrypt(self, base: Path) -> Generator[Path, None, None]:
        """

        Encrypt all the files specified in the definitions

        """
        for definition in self.definitions:
            yield from definition.encrypt(base)

    @classmethod
    def from_path(cls, path: Path | None = None) -> Self:
        """

        Load from file

        """
        path = path or Path.cwd() / cls.FILENAME
        data = path.read_yaml()
        definitions = [Definition.from_data(d) for d in data['definitions']]
        self = cls(definitions=definitions)
        return self

    @classmethod
    def from_cwd(cls):
        """

        Encrypt secrets from repo root

        """
        self = cls.from_path()
        paths = list(self.encrypt(Path.cwd()))
        return paths


def decrypt(base: Path | None = None):
    """

    Encrypt secrets from repo root

    """

    base = base or Path.cwd()

    encryptor = EncryptorValues()

    paths_black = []
    for path_black in base.glob('**/*.black.yml'):
        paths_black.append(path_black)

    for path_black in paths_black:

        black = path_black.read_data()
        red = encryptor.decrypt(black)

        if path_black.name == '.env.black.yml':
            path_red = path_black.parent / '.env'
        else:
            path_red = path_black.parent / Path(path_black.stem).with_suffix(f'.red.yml')

        if path_red.exists():

            is_older = path_black.modified < path_red.modified
            if is_older:
                logger.info(f'Skipping {path_black=}, as it is older than {path_red=}')
                continue

            red_old = path_red.read_data()
            if red_old == red:
                logger.info(f'No change: {path_red=}')
                continue

        logger.info(f'Writing new red: {path_red=}')
        path_red.write_data(red)
        yield path_red
