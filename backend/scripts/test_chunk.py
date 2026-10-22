"""Chunk an already-cloned repo and check every chunk's line numbers:
python -m scripts.test_chunk [owner__repo]

Run scripts.test_parse first if the repo isn't in github_repos/ yet.
"""
import sys
from collections import Counter

from indexer.chunker import CHUNK_SIZE, chunk_data
from indexer.cloner import repo_folder
from indexer.parser import parse_github_repo

folder = sys.argv[1] if len(sys.argv) > 1 else "manassingh9220__pgq"
files = parse_github_repo(repo_folder / folder)

all_chunks = []
for f in files:
    chunks = chunk_data(f)
    lines = f.content.splitlines()

    for c in chunks:
        assert 1 <= c.start_line <= c.end_line <= f.line_count, (f.file_path, c.start_line, c.end_line)
        assert len(c.content) <= CHUNK_SIZE, (f.file_path, len(c.content))
        # The chunk must sit inside the lines it claims (it can start or end mid-line)
        assert c.content in "\n".join(lines[c.start_line - 1 : c.end_line]), (f.file_path, c.start_line)

    # No text is lost between consecutive chunks. The splitter strips whitespace,
    # so blank lines between two chunks are the only allowed gap.
    for prev, nxt in zip(chunks, chunks[1:]):
        gap = lines[prev.end_line : nxt.start_line - 1]
        assert all(not line.strip() for line in gap), (f.file_path, prev.end_line, nxt.start_line)

    all_chunks.extend(chunks)

print(f"Chunked ✅ {len(files)} files -> {len(all_chunks)} chunks")
print("By language:", dict(Counter(c.language for c in all_chunks)))
sizes = sorted(len(c.content) for c in all_chunks)
print(f"Chunk size (chars): min {sizes[0]}, median {sizes[len(sizes) // 2]}, max {sizes[-1]}")
print("Line numbers ✅ all chunks match their lines, no gaps between chunks")

sample = next((f for f in files if f.file_path.endswith("worker.py")), files[0])
print(f"\n{sample.file_path} ({sample.line_count} lines):")
for c in chunk_data(sample):
    first_line = c.content.splitlines()[0][:60]
    print(f"  lines {c.start_line:>3}-{c.end_line:<3} {first_line}")
