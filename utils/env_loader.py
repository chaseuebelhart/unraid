from pathlib import Path
from dotenv import load_dotenv

def find_repo_root(start_file: str) -> Path:
    """
    Walk upward from the file's directory until finding the repo root,
    identified by the presence of a `.git` directory.
    """
    current = Path(start_file).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Could not locate repo root containing a .git directory.")

def load_project_env(start_file: str = __file__, filename: str = ".env") -> None:
    """
    Loads the .env file from the repository root.

    Simply call:
        from utils.env_loader import load_project_env
        load_project_env()

    And your environment variables will be loaded no matter where your script is located.
    """
    root = find_repo_root(start_file)
    env_path = root / filename

    if not env_path.exists():
        raise FileNotFoundError(f"Cannot find .env at: {env_path}")

    load_dotenv(env_path)

def get_repo_root(start_file: str = __file__) -> Path:
    """
    Returns the repository root Path object.
    """
    return find_repo_root(start_file)
