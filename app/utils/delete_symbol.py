import re


def slugify_filename(name: str) -> str:
    """
    Removes characters prohibited from file names.
    """
    return re.sub(r'[\\/*?:"<>|]', "_", name)
