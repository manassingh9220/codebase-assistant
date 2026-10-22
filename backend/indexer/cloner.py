import shutil
from pathlib import Path
from typing import Optional

from git import GitCommandError, Repo

# Clones go in <repo root>/github_repos, no matter which directory you run from
repo_folder = Path(__file__).resolve().parent.parent.parent / "github_repos"

GITHUB_PREFIX = "https://github.com/"


def clone_github_repo(repo_url: str, token: Optional[str] = None) -> Path:
    """
    Clones a GitHub repository (latest commit only) into github_repos/<owner>__<repo>.
    An existing clone of the same repository is replaced.

    Args:
        repo_url (str): The https://github.com/<owner>/<repo> URL of the repository.
        token (Optional[str]): An optional GitHub token for private repositories.

    Returns:
        Path: The local folder the repository was cloned into.
    """
    clean_url = repo_url.strip().rstrip("/").removesuffix(".git")
    if not clean_url.startswith(GITHUB_PREFIX):
        raise ValueError(f"Expected a {GITHUB_PREFIX}<owner>/<repo> URL, got: {repo_url}")

    parts = clean_url.removeprefix(GITHUB_PREFIX).split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Expected a {GITHUB_PREFIX}<owner>/<repo> URL, got: {repo_url}")
    owner, repo_name = parts

    # Owner in the folder name so a/utils and b/utils don't overwrite each other
    dest = repo_folder / f"{owner}__{repo_name}"
    if dest.exists():
        shutil.rmtree(dest)

    auth_url = clean_url.replace("https://", f"https://{token}@") if token else clean_url

    try:
        # GitPython blocks URLs that are really git options (e.g. --upload-pack).
        # GIT_TERMINAL_PROMPT=0 makes a missing/private repo fail instead of
        # waiting for someone to type a username and password.
        repo = Repo.clone_from(
            auth_url, dest, depth=1, env={"GIT_TERMINAL_PROMPT": "0"}
        )
    except GitCommandError as e:
        # Mask the token in git's own output and don't chain the original error
        stderr = e.stderr.replace(token, "***") if token else e.stderr
        # GitPython wraps git's output as "stderr: '...'"; keep git's actual reason
        reason = " ".join(
            line.strip() for line in stderr.splitlines()
            if line.startswith(("remote:", "fatal:"))
        ) or stderr.strip()
        raise RuntimeError(f"Failed to clone {clean_url}: {reason}") from None

    if token:
        # git saves the clone URL in .git/config; replace it with the token-free one
        repo.remote("origin").set_url(clean_url)

    return dest
