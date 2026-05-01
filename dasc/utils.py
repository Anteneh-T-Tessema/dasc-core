import hashlib
from typing import Optional

def calculate_file_hash(filepath: str) -> Optional[str]:
    """
    Calculates the SHA-256 hash of a local file.
    Returns None if the file does not exist.
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except FileNotFoundError:
        return None
    except Exception:
        return None

def calculate_string_hash(content: str) -> str:
    """Calculates SHA-256 hash of a string."""
    return hashlib.sha256(content.encode()).hexdigest()
