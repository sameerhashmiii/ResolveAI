"""Deterministic knowledge ingestion and retrieval primitives."""

from app.rag.embeddings import EmbeddingProvider, LocalHashEmbedding

__all__ = ["EmbeddingProvider", "LocalHashEmbedding"]
