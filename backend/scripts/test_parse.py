"""Clone a repo and parse it end to end: python -m scripts.test_parse [github_url]"""
import sys
from collections import Counter

from indexer.cloner import clone_github_repo
from indexer.parser import parse_github_repo

url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/manassingh9220/pgq"

repo_path = clone_github_repo(url)
print("Cloned ✅", repo_path)

# Cloning again must replace the old copy, not fail
clone_github_repo(url)
print("Re-clone ✅")

files = parse_github_repo(repo_path)
print(f"Parsed ✅ {len(files)} files, {sum(f.line_count for f in files)} lines")
print("By language:", dict(Counter(f.language for f in files)))

for f in files[:10]:
    print(f"  {f.file_path:40} {f.language:11} {f.line_count} lines")

skipped_dirs = (".git/", "node_modules/", "venv/", "__pycache__/")
assert not any(d in f.file_path for f in files for d in skipped_dirs), "skipped dir leaked"
assert not any(f.file_path.startswith("/") for f in files), "absolute path found"
print("Paths ✅ all relative, no skipped folders")
