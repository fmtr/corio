import base64
import re
from functools import cached_property
from typing import Any, Callable, Union

import pyrage
from pyrage import x25519

import corio.environment_tools as env
from corio.constants import Constants
from corio.json_tools import to_json, from_json
from corio.path_tools import Path

SerializableScalar = Union[str, int, float, bool, None]
Serializable = Union[SerializableScalar, dict, list]


class Encryptor:
    """

    Simple age-based encrypt/decrypt interface for serializable data structures.

    """

    PREFIX = ''
    PARENS = '⁂' * 2
    LEFT, RIGHT = PARENS

    def __init__(self, key: str | None = None):
        """

        Initialise with encryption key

        """

        self.key = key or self.get_key()

    def get_key(self) -> str:
        """

        Fall back to environment variable

        """
        key = env.get(Constants.FMTR_AGE_KEY_KEY, None)

        if not key:
            raise ValueError("No encryption key specified")

        return key

    @cached_property
    def identity(self) -> x25519.Identity:
        """

        Parsed x25519 identity derived from `key`.

        """
        return x25519.Identity.from_str(self.key)

    @cached_property
    def private_key(self) -> str:
        """

        Private key as a string.

        """
        return str(self.identity)

    @cached_property
    def public_key(self) -> str:
        """

        Public key as a string.

        """
        return self.identity.to_public()

    @cached_property
    def header_rx(self) -> re.Pattern:
        """

        Compile regular expression to match header using `PREFIX`

        """
        left = re.escape(self.LEFT)
        right = re.escape(self.RIGHT)
        rx = re.compile(
            fr"^{self.PREFIX}{left}(.*){right}$",
            re.DOTALL
        )
        return rx

    def enhead(self, value: str) -> str:
        """

        Add header

        """
        return f"{self.PREFIX}{self.LEFT}{value}{self.RIGHT}"

    def dehead(self, value: str) -> str:
        """

        Remove header

        """
        match = self.header_rx.match(value)
        if not match:
            return value
        return match.group(1)

    def is_encrypted(self, value: Any) -> bool:
        """

        Test if value is encrypted

        """
        if not isinstance(value, str):
            return False
        is_encrypted = bool(self.header_rx.match(value))
        return is_encrypted

    def encrypt(self, data: Serializable) -> str:
        """

        Encrypt serializable data

        """
        plain_bytes = to_json(data).encode(Constants.ENCODING)
        cipher_inner = pyrage.encrypt(plain_bytes, [self.public_key])
        cipher_b64 = base64.b64encode(cipher_inner).decode("ascii")
        cipher_text = self.enhead(cipher_b64)
        return cipher_text

    def decrypt(self, data: Any) -> Any:
        """

        Decrypt serializable data, if header is present

        """
        if not isinstance(data, str):
            return data

        inner = self.dehead(data)
        if inner == data:  # not wrapped
            return data

        cipher_text = base64.b64decode(inner)
        plain_bytes = pyrage.decrypt(cipher_text, [self.identity])
        plain = from_json(plain_bytes.decode(Constants.ENCODING))
        return plain


class EncryptorValues(Encryptor):
    """

    Encryptor that operates on leaves, leaving keys and structures intact.

    """

    def include_node(self, node: Path) -> bool:
        """

        Allow excluding paths from encryption

        """
        return True

    def _transform_tree(self, data: Serializable, transformer: Callable[[Any], Any], node: Path = None) -> Serializable:
        """

        Transform the data tree, encrypting or decrypting leaves

        """

        node = node or Path()

        if isinstance(data, list):
            return [self._transform_tree(item, transformer, node=node / f'[{i}]') for i, item in enumerate(data)]
        if isinstance(data, dict):
            return {key: self._transform_tree(value, transformer, node=node / key) for key, value in data.items()}

        if not self.include_node(node):
            return data

        return transformer(data)

    def encrypt(self, data: Serializable) -> Serializable:
        """

        User super().encrypt via _transform_tree

        """
        return self._transform_tree(data, transformer=super().encrypt)

    def decrypt(self, data: Serializable) -> Serializable:
        """

        User super().decrypt via _transform_tree

        """
        return self._transform_tree(data, transformer=super().decrypt)


class EncryptorValuesSelect(EncryptorValues):
    """

    Encrypt only the nodes specified

    """

    def __init__(self, key: str | None = None, nodes: list[str] = None):
        self.nodes = nodes
        super().__init__(key=key)

    def include_node(self, node: Path) -> bool:
        """

        Include node if it matches any of the nodes specified. If node is root (e.g. the input tree is actually just a string), then always encrypt.

        """

        if node == Path():
            return True

        include = any(node.match(field) for field in self.nodes)
        return include
