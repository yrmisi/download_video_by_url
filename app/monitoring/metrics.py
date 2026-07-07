from prometheus_client import Counter

# Префикс 'mediagrab_' объединяет все кастомные метрики проекта
CLEANUP_FILES_TOTAL = Counter(
    "mediagrab_cleanup_files_removed_total",
    "Total number of physical files removed from disk by cleanup service",
    ["cleanup_type"],  # Добавляем лейбл, чтобы отличать плановую очистку от глубокой суточной
)
