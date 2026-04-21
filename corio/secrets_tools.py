from __future__ import annotations

from functools import cached_property
from typing import ClassVar
from typing import Generator

from pydantic import Field
from pydantic_settings import CliSubCommand

from corio import data_modelling_tools as dm
from corio import settings_tools as sets
from corio.encryption_tools import EncryptorValuesSelect, EncryptorValues
from corio.iterator_tools import flatten_tree, strip_none, IndexList
from corio.logging_tools import logger
from corio.path_tools import Path


class Definition(dm.Base):
    """

    Pair of lists of files - and the nodes to encrypt within those files

    """
    config: Config | None = Field(default=None, exclude=True, repr=False)
    files: list[str]
    nodes: list[str] = Field(default_factory=list)

    @cached_property
    def encryptor(self) -> EncryptorValuesSelect:
        """

        Create encryptor with only the nodes specified

        """
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

    def filter(self, path: Path) -> Path | None:
        """

        Filter out directories and files not covered by any specified contexts

        """

        if path.is_dir():
            return

        if path.name.endswith('.black.yml'):
            return

        for context in self.config.encrypt.context:
            for pattern in self.config.contexts.name[context].files:
                pattern = f'{self.config.path_repo}/{pattern}'
                if path.full_match(pattern):
                    return path

        return


    def encrypt(self, base: Path) -> Generator[Path, None, None]:
        """

        Iterate over the files specified in the definition, and encrypt them.

        """

        paths_red = []
        for path_red in self.files:
            paths_red += list(base.glob(path_red))

        paths_red = strip_none(*[self.filter(path) for path in paths_red])

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


class Context(dm.Base):
    """

    Context definition

    """
    name: str
    files: list[str]


class Command(dm.Base):
    """

    CLI subcommand base

    """
    config: Config | None = Field(default=None, exclude=True, repr=False)
    context: list[str]

    def is_black(self, path: Path) -> bool:
        """

        Is the current file a black file?

        """
        return path.name.endswith('.black.yml')

    def filter(self, path: Path) -> Path | None:
        """

        Filter based on directories, black files and files covered by any specified contexts

        """

        if path.is_dir():
            return

        if not self.is_included_self_suffix(path):
            return

        for context in self.context:
            for pattern in self.config.contexts.name[context].files:
                pattern = f'{self.config.path_repo}/{pattern}'
                if path.full_match(pattern):
                    return path

        return


class Encrypt(Command):
    """

    Encrypt subcommand

    """

    def run(self):
        """

        Encrypt all the files specified in the definitions

        """
        super().run()

        for definition in self.config.definitions:
            for path in self.process_definition(definition):
                path  # todo add to repo.

    def is_included_self_suffix(self, path: Path) -> bool:
        """

        Exclude any black files, so we don't double-encrypt them.

        """
        return not self.is_black(path)

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
        paths_red = strip_none(*[self.filter(path) for path in paths_red])

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

    def run(self):
        """

        Decrypt all the files in the specified contexts

        """
        super().run()

        paths = self.get_paths()
        paths = strip_none(*[self.filter(path) for path in paths])

        for path in paths:
            path = self.process_file(path)
            if path:
                path

    @cached_property
    def encryptor(self) -> EncryptorValues:
        """

        Decryption doesn't need definitions, so can use a generic values encryptor

        """
        return EncryptorValues()

    def is_included_self_suffix(self, path: Path) -> bool:
        """

        Include only files that _are_ black

        """
        return self.is_black(path)

    def get_paths(self):

        paths_black = []
        for path_black in self.config.path_repo.glob('**/*.black.yml'):
            paths_black.append(path_black)

        return paths_black

    def process_file(self, path_black: Path) -> Path | None:
        black = path_black.read_data()
        red = self.encryptor.decrypt(black)

        path_red = path_black.parent / Path(path_black.stem).stem

        if path_red.exists():

            is_older = path_black.modified < path_red.modified
            if is_older:
                logger.info(f'Skipping {path_black=}, as it is older than {path_red}')
                return

            red_robin = path_red.read_data()
            if red == red_robin:
                logger.info(f'No change: {path_red}')
                return

        logger.info(f'Writing new red: {path_red}')
        path_red.write_data(red)
        return path_red


class Config(sets.Base):
    """

    Secrets encryptions definitions file in repo root

    """

    FILENAME: ClassVar[str] = '.secrets.yml'
    definitions: list[Definition] = Field(default_factory=list)
    contexts: list[Context] = Field(default_factory=list)

    encrypt: CliSubCommand[Encrypt]
    decrypt: CliSubCommand[Decrypt]

    def __init__(self, **kwargs):
        """

        Add self to all definitions and subcommands

        """
        super().__init__(**kwargs)

        self.contexts = IndexList(self.contexts)

        for definition in self.definitions:
            definition.config = self

        for sub in self.encrypt, self.decrypt:
            if not sub:
                continue
            sub.config = self


    @classmethod
    def find_yaml_file(cls) -> Path:
        """
    
        Walk up the directory tree looking for cls.FILENAME
    
        """

        path = Path.cwd().find_up(cls.FILENAME)
        return path

    @cached_property
    def path_repo(self) -> Path:
        """

        Path to repo root, where YAML file was found

        """
        return self.find_yaml_file().parent


if __name__ == '__main__':
    ...
