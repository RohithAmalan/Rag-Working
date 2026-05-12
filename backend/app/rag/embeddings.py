import re
from typing import Sequence

import numpy as np


class LocalHashEmbeddings:
    def __init__(self, dim: int = 384):
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vector = np.zeros(self.dim, dtype="float32")
        for token in re.findall(r"\w+", text.lower()):
            vector[hash(token) % self.dim] += 1.0

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector.tolist()

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def get_embeddings(openai_api_key: str):
    return LocalHashEmbeddings()
