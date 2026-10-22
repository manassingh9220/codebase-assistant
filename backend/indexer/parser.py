import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# File extension -> language name stored in code_chunks.language
LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".sql": "sql",
    ".md": "markdown",
}

# Folders never worth indexing: VCS data, dependencies, build output, caches
SKIP_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "vendor",
}

# Anything bigger is almost always generated code or data, not something to read
MAX_FILE_BYTES = 1_000_000


@dataclass
class ParsedFile:
    file_path: str  # relative to the repo root, e.g. "src/pgq/worker.py"
    language: str
    content: str
    line_count: int


def parse_github_repo(repo_path: Path) -> list[ParsedFile]:
    """
    Walks a cloned repository and reads every supported source file.

    Args:
        repo_path (Path): The local folder returned by clone_github_repo.

    Returns:
        list[ParsedFile]: One entry per readable file, sorted by path.
    """
    files = []

    for dirpath, dirnames, filenames in os.walk(repo_path):
        # Editing dirnames in place stops os.walk from going into these folders
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)

        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            language = LANGUAGES.get(path.suffix.lower())

            if language is None or filename.endswith(".min.js"):
                continue
            # A symlink can point outside the repo
            if path.is_symlink():
                continue

            size = path.stat().st_size
            if size == 0 or size > MAX_FILE_BYTES:
                continue

            relative_path = path.relative_to(repo_path).as_posix()
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError) as e:
                # One bad file shouldn't stop the whole repo
                logger.warning("Skipping %s: %s", relative_path, e)
                continue

            files.append(
                ParsedFile(
                    file_path=relative_path,
                    language=language,
                    content=content,
                    line_count=len(content.splitlines()),
                )
            )

    return files
