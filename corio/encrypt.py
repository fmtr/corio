import base64
import pyrage
import re
from dataclasses import dataclass
from functools import cached_property
from pyrage import x25519
from typing import Callable, Union

import corio.env as env
from corio import strings
from corio.constants import Constants
from corio.jsn import from_json, to_json
from corio.path import Path

SerializableScalar = Union[str, int, float, bool, None]
Serializable = Union[SerializableScalar, dict, list]


@dataclass
class Node:
    """Select a path and, optionally, parts of its string value."""

    glob: str
    pattern: str | None = None

    @cached_property
    def rx(self) -> re.Pattern:
        """

        Compile the optional partial-match pattern.

        """
        pattern = self.pattern or "(.*)"
        rx = re.compile(f"^{pattern}$")
        return rx


class MatchTransformer:
    """

    Transform captured portions of a regular-expression match.

    """

    def __init__(
            self,
            transformer: Callable[[Serializable], Serializable],
            preserve_unmatched: bool = True,
    ):
        """

        Initialise with a value transformer.

        """
        self.transformer = transformer
        self.preserve_unmatched = preserve_unmatched

    def __call__(self, match: re.Match[str]) -> str:
        """Transform every capture group while preserving the rest of the match."""
        parts = []
        for portion in strings.get_portions(match):
            if not portion.captured:
                if self.preserve_unmatched:
                    parts.append(portion.value)
                continue
            parts.append(str(self.transformer(portion.value)))
        transformed = "".join(parts)
        return transformed


class Encryptor:
    """

    Simple age-based encrypt/decrypt interface for serializable data structures.

    """

    PREFIX = ""
    PARENS = "⁂" * 2
    LEFT, RIGHT = PARENS

    def __init__(self, key: str | None = None):
        """

        Initialise with an encryption key.

        """
        self.key = key or self.get_key()

    def get_key(self) -> str:
        """

        Fall back to the environment variable.

        """
        key = env.get(Constants.FMTR_AGE_KEY_KEY, None)
        if not key:
            raise ValueError("No encryption key specified")
        return key

    @cached_property
    def identity(self) -> x25519.Identity:
        """

        Parsed x25519 identity derived from ``key``.

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

        Compile an unanchored expression that finds encrypted fragments.

        """
        left = re.escape(self.LEFT)
        right = re.escape(self.RIGHT)
        rx = re.compile(fr"{self.PREFIX}{left}(.*?){right}", re.DOTALL)
        return rx

    def enhead(self, value: str) -> str:
        """

        Add a header.

        """
        header = f"{self.PREFIX}{self.LEFT}{value}{self.RIGHT}"
        return header

    def dehead(self, value: str) -> str:
        """

        Remove a header.

        """
        match = self.header_rx.fullmatch(value)
        if not match:
            return value
        inner = match.group(1)
        return inner

    def is_encrypted(self, value: Serializable) -> bool:
        """

        Test if a value contains an encrypted fragment.

        """
        if not isinstance(value, str):
            return False
        is_encrypted = bool(self.header_rx.search(value))
        return is_encrypted

    def encrypt(self, data: Serializable) -> str:
        """

        Encrypt serializable data.

        """
        plain_bytes = to_json(data).encode(Constants.ENCODING)
        cipher_inner = pyrage.encrypt(plain_bytes, [self.public_key])
        cipher_b64 = base64.b64encode(cipher_inner).decode("ascii")
        cipher_text = self.enhead(cipher_b64)
        return cipher_text

    def decrypt(self, data: Serializable) -> Serializable:
        """

        Decrypt serializable data, if a header is present.

        """
        if not isinstance(data, str):
            return data

        def decrypt_inner(inner: str) -> Serializable:
            cipher_text = base64.b64decode(inner)
            plain_bytes = pyrage.decrypt(cipher_text, [self.identity])
            plain = from_json(plain_bytes.decode(Constants.ENCODING))
            return plain

        if self.header_rx.fullmatch(data):
            inner = self.dehead(data)
            plain = decrypt_inner(inner)
            return plain

        decrypt_fragment = MatchTransformer(decrypt_inner, preserve_unmatched=False)
        plain = self.header_rx.sub(decrypt_fragment, data)
        return plain


class EncryptorValues(Encryptor):
    """

    Encryptor that operates on leaves, leaving keys and structures intact.

    """

    @cached_property
    def default(self) -> Node:
        node = Node(glob="*", pattern=None)
        return node

    def include(self, path: Path) -> Node | None:
        """

        Allow excluding paths from encryption.

        """
        node = self.default
        return node

    def _transform_tree(
            self,
            data: Serializable,
            transformer: Callable[[Path, Serializable], Serializable],
            path: Path | None = None,
    ) -> Serializable:
        """

        Transform the data tree, encrypting or decrypting leaves.

        """
        path = path or Path()
        if isinstance(data, list):
            transformed = [
                self._transform_tree(item, transformer, path / f"[{i}]")
                for i, item in enumerate(data)
            ]
            return transformed
        if isinstance(data, dict):
            transformed = {
                key: self._transform_tree(value, transformer, path / key)
                for key, value in data.items()
            }
            return transformed
        return transformer(path, data)

    def encrypt(self, data: Serializable) -> Serializable:
        """

        Encrypt leaves through the data tree.

        """
        encrypted = self._transform_tree(data, transformer=self._encrypt_value)
        return encrypted

    def _encrypt_value(self, path: Path, data: Serializable) -> Serializable:
        node = self.include(path)
        if node is None:
            return data
        if not isinstance(data, str) or not node.pattern:
            return super().encrypt(data)
        return node.rx.sub(MatchTransformer(super().encrypt), data)

    def decrypt(self, data: Serializable) -> Serializable:
        """

        Decrypt leaves through the data tree.

        """
        plain = self._transform_tree(data, transformer=self._decrypt_value)
        return plain

    def _decrypt_value(self, path: Path, data: Serializable) -> Serializable:
        plain = super().decrypt(data)
        return plain


class EncryptorValuesSelect(EncryptorValues):
    """

    Encrypt only the nodes specified.

    """

    def __init__(self, key: str | None = None, nodes: list[Node] | None = None):
        """

        Initialise with the nodes to encrypt.

        """
        self.nodes = nodes
        super().__init__(key=key)

    def include(self, path: Path) -> Node | None:
        """

        Include a path if it matches any configured node.

        For a root scalar, use the first configured node so its partial
        pattern can be applied.

        """
        if path != Path():
            for node in self.nodes or []:
                if path.match(node.glob):
                    return node
            return None

        if self.nodes is None:
            return None
        if not self.nodes:
            node = self.default
            return node
        node = self.nodes[0]
        return node
