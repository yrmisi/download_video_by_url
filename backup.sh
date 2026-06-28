#!/bin/bash

# Настройки
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/home/yrmisi/PythonProjects/download_video_by_url"
# Переходим в папку проекта
cd "$PROJECT_DIR" || exit 1

# Создаем папку для бэкапов, если её нет
mkdir -p "$BACKUP_DIR"

# Загружаем переменные окружения из файла проекта, чтобы Bash о них узнал
if [ -f "app/config/envs/.env.postgres-prod" ]; then
    export $(grep -v '^#' app/config/envs/.env.postgres-prod | xargs)
fi

echo "=== Starting Backup $DATE ==="

# 2. Делаем бэкап
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_DIR/db_$DATE.sql"
echo "-> PostgreSQL backup saved."

# 2. Бэкап файлов (архивируем локальную папку с волюмами, если они примонтированы как bind mount,
# либо делаем архив папки downloads из контейнера nginx/web)
docker compose exec -T nginx tar -czf - /usr/share/nginx/html/downloads > "$BACKUP_DIR/downloads_$DATE.tar.gz"
echo "-> Downloads folder archived."

# 3. Удаление старых бэкапов (оставляем только за последние 7 дней, чтобы диск не переполнился)
find "$BACKUP_DIR" -type f -mtime +7 -delete
echo "-> Old backups cleaned up."

echo "=== Backup Complete ==="
