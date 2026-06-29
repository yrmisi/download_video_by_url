from dataclasses import dataclass


@dataclass
class DownloadHistoryItems:
    """
    Data structure for creating new download history records.
    """

    id: str
    url: str
    user_id: str
    profile: str
    quality: str


@dataclass
class UpdateLoadHistoryItems:
    """
    Data structure for updating existing download history records.
    """

    title: str | None = None
    thumbnail: str | None = None
    duration: int | None = None
    resolution: str | None = None
    file_path: str | None = None
    filesize: int | None = None
    status: str | None = None
