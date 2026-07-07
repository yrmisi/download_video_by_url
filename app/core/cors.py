import os


def get_allowed_origins() -> list[str]:
    """
    Returns a list of allowed URLs (origins) for CORS,
    loading them from an environment variable or using default values for dev.
    """

    # На dev можно использовать "http://localhost:8000,http://localhost:5173", порт 5173 - дефолт для Vite на фронтенде
    # На prod — конкретный домен фронтенда
    raw_origins = os.getenv("ALLOWED_ORIGINS", "")
    if raw_origins:
        return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    return [
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
