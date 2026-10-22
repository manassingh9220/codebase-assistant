"""Check the DB schema and run a vector search end to end: python -m scripts.test_db

Everything written here is rolled back, so it leaves no data behind.
"""
import numpy as np

from config import settings
from db.setup import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
print("pgvector ✅ version", cur.fetchone()[0])

cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name IN ('repositories', 'code_chunks')
""")
print("Tables ✅", sorted(r[0] for r in cur.fetchall()))

cur.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'code_chunks'")
print("Indexes ✅", sorted(r[0] for r in cur.fetchall()))

# Insert a repo and three chunks with random embeddings
cur.execute(
    "INSERT INTO repositories (url, name) VALUES (%s, %s) RETURNING id",
    ("https://github.com/example/test-repo", "test-repo"),
)
repo_id = cur.fetchone()[0]

vectors = np.random.rand(3, settings.embedding_dim).astype(np.float32)
for i, vec in enumerate(vectors):
    cur.execute(
        """INSERT INTO code_chunks (repo_id, file_path, content, embedding)
           VALUES (%s, %s, %s, %s)""",
        (repo_id, f"file_{i}.py", f"def func_{i}(): pass", vec),
    )

# Search with chunk 1's own vector: it must come back as the nearest match
cur.execute(
    """SELECT file_path, 1 - (embedding <=> %s) AS similarity
       FROM code_chunks WHERE repo_id = %s
       ORDER BY embedding <=> %s LIMIT 1""",
    (vectors[1], repo_id, vectors[1]),
)
file_path, similarity = cur.fetchone()
assert file_path == "file_1.py", f"expected file_1.py, got {file_path}"
print(f"Vector search ✅ nearest = {file_path} (similarity {similarity:.3f})")

conn.rollback()
conn.close()
