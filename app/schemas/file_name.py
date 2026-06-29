from dataclasses import dataclass


@dataclass
class FileData:
    """
    Container for file path and sanitized filename.
    """

    file_disk_path: str
    friendly_name: str
