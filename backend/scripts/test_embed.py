"""Index a repo end to end, then search it with raw SQL:
python -m scripts.test_embed [github_url] ["question"]

Clone -> parse -> chunk -> embed (Voyage) -> store (pgvector) -> similarity search.
Needs `python -m db.setup` to have been run once.
"""
import logging
import sys
import time

from db.setup import get_connection
from indexer.chunker import chunk_files
from indexer.cloner import clone_github_repo
from indexer.embedder import embed_chunks, embed_query, store_chunks
from indexer.parser import parse_github_repo

# Show the embedder's progress and rate-limit waits
logging.basicConfig(level=logging.INFO, format="  %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/manassingh9220/pgq"
question = sys.argv[2] if len(sys.argv) > 2 else "How does a worker claim the next job?"

repo_path = clone_github_repo(url)
chunks = chunk_files(parse_github_repo(repo_path))
print(f"Chunked ✅ {len(chunks)} chunks")

started = time.time()
embeddings = embed_chunks(chunks)
print(f"Embedded ✅ {len(embeddings)} vectors of {len(embeddings[0])} dims in {time.time() - started:.1f}s")

repo_id = store_chunks(url, repo_path.name, chunks, embeddings)
print("Stored ✅ repo_id", repo_id)

conn = get_connection()
cur = conn.cursor()

cur.execute("SELECT status, chunks_count FROM repositories WHERE id = %s", (repo_id,))
status, chunks_count = cur.fetchone()
cur.execute("SELECT count(*) FROM code_chunks WHERE repo_id = %s", (repo_id,))
rows = cur.fetchone()[0]
assert status == "ready" and chunks_count == rows == len(chunks), (status, chunks_count, rows)
print(f"DB ✅ status={status}, {rows} rows")

# Raw SQL similarity search: <=> is cosine distance, so similarity = 1 - distance
query_vector = embed_query(question)
cur.execute(
    """SELECT file_path, start_line, end_line, 1 - (embedding <=> %s) AS similarity, content
       FROM code_chunks
       WHERE repo_id = %s
       ORDER BY embedding <=> %s
       LIMIT 5""",
    (query_vector, repo_id, query_vector),
)

print(f'\nQ: "{question}"')
for file_path, start_line, end_line, similarity, content in cur.fetchall():
    first_line = content.strip().splitlines()[0][:70]
    print(f"  {similarity:.3f}  {file_path}:{start_line}-{end_line}  {first_line}")

conn.close()
