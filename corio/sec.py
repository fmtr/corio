from __future__ import annotations

from functools import cached_property
from typing import ClassVar
from typing import Generator
from typing import TYPE_CHECKING

from pydantic import Field
from pydantic_settings import CLI_SUPPRESS
from pydantic_settings import CliSubCommand

from corio import dm as dm
from corio import sets as sets
from corio.iterator import flatten_tree
from corio.logs import logger
from corio.path import Path

if TYPE_CHECKING:
    from corio.encrypt import EncryptorValues, EncryptorValuesSelect

token_hex=None # FastAPI tries to import this?

class Definition(dm.Base):
    """

    Pair of lists of files - and the nodes to encrypt within those files

    """
    config: Cli | None = Field(default=None, exclude=True, repr=False, description=CLI_SUPPRESS)
    files: list[str]
    nodes: list[str] = Field(default_factory=list)

    @cached_property
    def encryptor(self) -> EncryptorValuesSelect:
        """

        Create encryptor with only the nodes specified

        """
        from corio.encrypt import EncryptorValuesSelect

        return EncryptorValuesSelect(nodes=self.nodes)

    def is_keys_values_aligned(self, black_robin: dict) -> bool:
        """

        Check if the keys that should be encrypted are encrypted, and vice versa, in the existing black on disk. If they aren't, we need to re-encrypt the file.

        """
        black_flat = flatten_tree(black_robin)

        for path, value in black_flat.items():
            is_key_encrypted = self.encryptor.include_node(path)
            is_value_encrypted = self.encryptor.is_encrypted(value)
            if is_key_encrypted != is_value_encrypted:
                return False

        return True

    def encrypt(self, base: Path) -> Generator[Path, None, None]:
        """

        Iterate over the files specified in the definition, and encrypt them.

        """

        paths_red = []
        for path_red in self.files:
            paths_red += list(base.glob(path_red))

        paths_red = [path for path in paths_red if path.is_file() and not path.name.endswith('.black.yml')]

        for path_red in paths_red:
            path = self.encrypt_file(path_red)
            if path:
                yield path

    def encrypt_file(self, path_red: Path) -> Path | None:
        """

        For each file, check whether its contents, or the encrypted nodes lists, have changed since it was last encrypted - and re-encrypt if so.

        """

        red = path_red.read_data()
        black = self.encryptor.encrypt(red)
        red_robin = self.encryptor.decrypt(black)

        if red != red_robin:
            raise ValueError(f'Round-robin mismatch: {path_red}')

        path_black = path_red.parent / f'{path_red.name}.black.yml'

        if path_black.exists():
            black_robin = path_black.read_data()
            red_robin = self.encryptor.decrypt(black_robin)
            is_aligned = self.is_keys_values_aligned(black_robin)
            if red_robin == red and is_aligned:
                logger.info(f'No change: {path_black}')
                return None

        logger.info(f'Writing new black: {path_black}')
        path_black.write_yaml(black)
        return path_black


class Command(dm.Base):
    """

    CLI subcommand base

    """
    config: Cli | None = Field(default=None, exclude=True, repr=False, description=CLI_SUPPRESS)
    def is_black(self, path: Path) -> bool:
        """

        Is the current file a black file?

        """
        return path.name.endswith('.black.yml')

class Encrypt(Command):
    """

    Encrypt subcommand

    """

    def run(self):
        """

        Encrypt all the files specified in the definitions

        """
        super().run()

        with logger.span(f'Encrypting secrets in repo "{self.config.path_repo}"...'):
            for definition in self.config.definitions:
                for path in self.process_definition(definition):
                    path  # todo add to repo.

    def get_paths(self, definition: Definition) -> list[Path]:
        """

        Get initial set of paths matched by all definitions.

        """
        paths = []
        for pattern in definition.files:
            paths += list(self.config.path_repo.glob(pattern))

        return paths

    def process_definition(self, definition: Definition) -> Generator[Path, None, None]:
        """

        Iterate over the files specified in the definition, and encrypt them.

        """

        paths_red = self.get_paths(definition)
        paths_red = [path for path in paths_red if path.is_file() and not self.is_black(path)]

        for path_red in paths_red:
            path = self.process_file(path_red, definition)
            if path:
                yield path

    def process_file(self, path_red: Path, definition: Definition) -> Path | None:
        """

        For each file, check whether its contents, or the encrypted nodes lists, have changed since it was last encrypted - and re-encrypt if so.

        """

        red = path_red.read_data()
        black = definition.encryptor.encrypt(red)
        red_robin = definition.encryptor.decrypt(black)

        if red != red_robin:
            raise ValueError(f'Round-robin mismatch: {path_red}')

        path_black = path_red.parent / f'{path_red.name}.black.yml'

        if path_black.exists():
            black_robin = path_black.read_data()
            red_robin = definition.encryptor.decrypt(black_robin)
            is_aligned = definition.is_keys_values_aligned(black_robin)
            if red_robin == red and is_aligned:
                logger.info(f'No change: {path_black}')
                return None

        logger.info(f'Writing new black: {path_black}')
        path_black.write_yaml(black)
        return path_black


class Decrypt(Command):
    """

    Decrypt subcommand

    """
    source: Path = Field(default_factory=Path.cwd)
    target: Path = Field(default_factory=Path.cwd)

    def run(self):
        """

        Decrypt every black file under source into the mirrored target tree.

        """
        super().run()

        with logger.span(f'Decrypting secrets from "{self.source}" to "{self.target}"...'):
            for path in self.get_paths():
                self.process_file(path)

    @cached_property
    def encryptor(self) -> EncryptorValues:
        """

        Decryption doesn't need definitions, so can use a generic values encryptor

        """
        from corio.encrypt import EncryptorValues

        return EncryptorValues()

    def get_paths(self):
        return [path for path in self.source.glob('**/*.black.yml') if path.is_file()]

    def process_file(self, path_black: Path) -> Path | None:
        black = path_black.read_data()
        red = self.encryptor.decrypt(black)

        relative_black = path_black.relative_to(self.source)
        relative_red = relative_black.parent / Path(relative_black.stem).stem
        path_red = self.target / relative_red
        path_red.parent.mkdirf()

        if path_red.exists():

            is_older = path_black.modified < path_red.modified
            if is_older:
                logger.info(f'Skipping {path_black}, as it is older than {path_red}')
                return

            red_robin = path_red.read_data()
            if red == red_robin:
                logger.info(f'No change: {path_red}')
                return

        logger.info(f'Writing new red: {path_red}')
        path_red.write_data(red)
        return path_red





class Cli(sets.Base):
    """

    Secrets encryptions definitions file in repo root

    """

    FILENAME: ClassVar[str] = '.secrets.yml'
    definitions: list[Definition] = Field(default_factory=list)
    encrypt: CliSubCommand[Encrypt]
    decrypt: CliSubCommand[Decrypt]

    def __init__(self, **kwargs):
        """

        Add self to all definitions and subcommands

        """
        super().__init__(**kwargs)

        for definition in self.definitions:
            definition.config = self

        for sub in self.encrypt, self.decrypt:
            if not sub:
                continue
            sub.config = self


    @classmethod
    def find_yaml_file(cls) -> Path | None:
        """
    
        Walk up the directory tree looking for cls.FILENAME
    
        """
        try:
            path = Path.cwd().find_up(cls.FILENAME)
        except FileNotFoundError:
            path = None
        return path

    @cached_property
    def path_repo(self) -> Path:
        """

        Path to repo root, where YAML file was found

        """
        return self.find_yaml_file().parent
