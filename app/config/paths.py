"""
Path configuration for the application.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATES_DIR = BASE_DIR / "templates"

DOWNLOADS_DIR = BASE_DIR.parent / "downloads"

ENVS_DIR = BASE_DIR / "config"

STATIC_DIR = BASE_DIR.parent / "frontend" / "static"
