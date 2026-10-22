import logging
import time
from typing import Iterator, Optional

import numpy as np
import voyageai
from psycopg2.extras import execute_values

from config import settings
from db.setup import get_connection
from indexer.chunker import Chunk

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "voyage-code-3"

# Voyage's per-request limits are 1,000 texts and 120K tokens (kept under, for safety).
# A batch also has to fit the per-minute token limit, or it can never succeed.
MAX_BATCH_TEXTS = 1_000
MAX_BATCH_TOKENS = min(100_000, int(settings.voyage_tokens_per_minute * 0.9))
# input_type adds a short retrieval prompt to every text, which Voyage counts
# but the local tokenizer doesn't
PROMPT_TOKENS_PER_TEXT = 16

_client: Optional[voyageai.Client] = None


def get_client() -> voyageai.Client:
    # Created on first use so importing this module doesn't need the API key.
    # max_retries backs off and retries on rate limits and temporary errors.
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=settings.voyage_api_key, max_retries=5)
    return _client


def embedding_text(chunk: Chunk) -> str:
    """
    The text that gets embedded. The file path is added because names like
    worker.py or reaper.py say a lot about the code; the stored content stays raw.
    """
    return f"File: {chunk.file_path} ({chunk.language})\n\n{chunk.content}"


def _make_batches(texts: list[str]) -> Iterator[tuple[list[str], int]]:
    """Groups texts, in order, into batches under the per-request limits."""
    batch, batch_tokens = [], 0
    for text in texts:
        # Counted locally with Voyage's tokenizer, no API call
        tokens = get_client().count_tokens([text], model=EMBEDDING_MODEL) + PROMPT_TOKENS_PER_TEXT
        if batch and (batch_tokens + tokens > MAX_BATCH_TOKENS or len(batch) == MAX_BATCH_TEXTS):
            yield batch, batch_tokens
            batch, batch_tokens = [], 0
        batch.append(text)
        batch_tokens += tokens
    if batch:
        yield batch, batch_tokens


def embed_chunks(chunks: list[Chunk]) -> list[np.ndarray]:
    """
    Embeds chunks in batches, pacing requests to stay under the tokens-per-minute limit.

    Args:
        chunks (list[Chunk]): Chunks from chunk_files.

    Returns:
        list[np.ndarray]: One float32 vector per chunk, in the same order.
    """
    embeddings = []
    window_start, window_tokens = time.monotonic(), 0

    for batch, batch_tokens in _make_batches([embedding_text(c) for c in chunks]):
        # Sending this batch would go over this minute's budget: wait for the next minute
        if window_tokens + batch_tokens > settings.voyage_tokens_per_minute:
            wait = 61 - (time.monotonic() - window_start)
            if wait > 0:
                logger.info("Waiting %.0fs for Voyage's per-minute token limit", wait)
                time.sleep(wait)
            window_start, window_tokens = time.monotonic(), 0

        result = get_client().embed(
            batch,
            model=EMBEDDING_MODEL,
            input_type="document",
            output_dimension=settings.embedding_dim,
        )
        window_tokens += batch_tokens
        embeddings.extend(np.array(e, dtype=np.float32) for e in result.embeddings)
        logger.info("Embedded %d/%d chunks", len(embeddings), len(chunks))

    return embeddings


def embed_query(question: str) -> np.ndarray:
    """Embeds a search question. input_type="query" pairs with "document" above."""
    result = get_client().embed(
        [question],
        model=EMBEDDING_MODEL,
        input_type="query",
        output_dimension=settings.embedding_dim,
    )
    return np.array(result.embeddings[0], dtype=np.float32)


def store_chunks(
    repo_url: str, repo_name: str, chunks: list[Chunk], embeddings: list[np.ndarray]
) -> str:
    """
    Saves a repository's chunks and embeddings, replacing any earlier index of it.
    Runs in one transaction: if anything fails, the previous index stays as it was.

    Returns:
        str: The repository's id.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(f"{len(chunks)} chunks but {len(embeddings)} embeddings")

    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO repositories (url, name, status) VALUES (%s, %s, 'indexing')
                   ON CONFLICT (url) DO UPDATE SET name = EXCLUDED.name, status = 'indexing'
                   RETURNING id""",
                (repo_url, repo_name),
            )
            repo_id = cur.fetchone()[0]

            # Re-indexing replaces the old chunks instead of adding duplicates
            cur.execute("DELETE FROM code_chunks WHERE repo_id = %s", (repo_id,))

            # execute_values sends all rows in a few statements instead of one per chunk
            execute_values(
                cur,
                """INSERT INTO code_chunks (repo_id, file_path, language, content, start_line,
                                            end_line, chunk_type, chunk_name, embedding)
                   VALUES %s""",
                [
                    (repo_id, c.file_path, c.language, c.content, c.start_line,
                     c.end_line, c.chunk_type, c.chunk_name, embedding)
                    for c, embedding in zip(chunks, embeddings)
                ],
            )

            cur.execute(
                """UPDATE repositories SET chunks_count = %s, status = 'ready', indexed_at = now()
                   WHERE id = %s""",
                (len(chunks), repo_id),
            )
    finally:
        conn.close()

    return repo_id
