import hashlib
import math
import re
import unicodedata
from typing import Protocol

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[._/-][a-z0-9]+)*")


def technical_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return TOKEN_PATTERN.findall(normalized)


class EmbeddingProvider(Protocol):
    """Replaceable boundary for local, learned, or hosted embedding implementations."""

    @property
    def name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed(self, text: str) -> list[float]: ...


class LocalHashEmbedding:
    """Stateless signed feature hashing over technical unigrams and adjacent bigrams."""

    name = "local-hash-v1"
    dimension = 384

    def embed(self, text: str) -> list[float]:
        tokens = technical_tokens(text)
        features = tokens + [
            f"{left}\x1f{right}" for left, right in zip(tokens, tokens[1:], strict=False)
        ]
        vector = [0.0] * self.dimension
        for feature in features:
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimension
            vector[index] += 1.0 if digest[8] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector
