import psycopg2
from pgvector.psycopg2 import register_vector
from config import settings

SCHEMA = f"""
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS repositories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    indexed_at TIMESTAMP DEFAULT now(),
    chunks_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'indexing' -- indexing,ready,failed
);

CREATE TABLE IF NOT EXISTS code_chunks(
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id uuid REFERENCES repositories(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    language TEXT,
    content TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    chunk_type TEXT, -- function, class, method, block
    chunk_name TEXT, -- function name, class name, method name if applicable
    embedding vector({settings.embedding_dim}),
    indexed_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS code_chunks_repo_id_idx ON code_chunks(repo_id);

CREATE INDEX IF NOT EXISTS code_chunks_embedding_hnsw_idx ON code_chunks
USING hnsw (embedding vector_cosine_ops)
WITH ( m=16, ef_construction=64);
"""

def get_connection():
    """connction that converts numpy arrays to/from vector type."""
    conn = psycopg2.connect(settings.codebase_db_url)
    register_vector(conn)
    return conn

def __init_db():
    # Plain connection here: register_vector needs the extension to already exist.
    # The `with conn` block commits on success and rolls back on error.
    conn = psycopg2.connect(settings.codebase_db_url)
    with conn, conn.cursor() as cur:
        cur.execute(SCHEMA)
    conn.close()

if __name__ == "__main__":
    __init_db()
    print("Database initialized successfully.")
