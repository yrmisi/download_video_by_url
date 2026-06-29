from dataclasses import dataclass


@dataclass
class MediaInfo:
    """
    Metadata extracted from media source.
    """

    title: str
    thumbnail: str
    max_quality: int
