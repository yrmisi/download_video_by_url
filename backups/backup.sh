#!/bin/bash

# 1. Строгий режим обработки ошибок
# -e: выйти если любая команда вернет ошибку
# -u: выйти если используется неинициализированная переменная
# -o pipefail: если упадет pg_dump внутри пайпа, упадет весь скрипт
set -euo pipefail

# Настройки
PROJECT_DIR="/home/yrmisi/PythonProjects/download_video_by_url"
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
ENV_FILE="$PROJECT_DIR/app/config/envs/.env.postgres-prod"

# Пароль для шифрования бэкапов (Сгенерируй сложный ключ и сохрани его в надежном месте!)
# В продакшене лучше читать его из секретного файла, к которому есть доступ только у root
ENCRYPTION_KEY="СуперСекретныйПарольДляШифрованияБэкапов"

# Переходим в папку проекта
cd "$PROJECT_DIR" || exit 1
mkdir -p "$BACKUP_DIR"

echo "=== Starting Backup $DATE ==="

# 2. Безопасный бэкап БД без экспорта переменных в текущий Bash
# Мы передаем --env-file напрямую в docker compose. Пароли не светятся в хост-системе.
# Бэкап сразу шифруется на лету через openssl
echo "-> Dumping and encrypting PostgreSQL database..."
docker compose --env-file "$ENV_FILE" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | openssl enc -aes-256-cbc -salt -pbkdf2 -pass "pass:$ENCRYPTION_KEY" -out "$BACKUP_DIR/db_$DATE.sql.enc"

# Проверка: если файл весит 0 байт — значит pg_dump ничего не отдал
if [ ! -s "$BACKUP_DIR/db_$DATE.sql.enc" ]; then
    echo "CRITICAL ERROR: Database backup file is empty!" >&2
    exit 1
fi
echo "-> PostgreSQL backup saved and encrypted."


# 3. Безопасный бэкап файлов downloads
# Вместо того чтобы просить Nginx архивировать файлы (где могут быть проблемы с правами),
# мы архивируем локальную папку downloads прямо с хоста (ведь это bind mount или папка проекта)
# Если папка лежит в проекте, архивируем её локально. Если это docker volume, используем сервисный контейнер под root.
LOCAL_DOWNLOADS_DIR="$PROJECT_DIR/downloads" # Укажи точный путь на хосте, если он отличается

if [ -d "$LOCAL_DOWNLOADS_DIR" ]; then
    echo "-> Archiving and encrypting downloads folder..."
    tar -czf - -C "$PROJECT_DIR" downloads \
      | openssl enc -aes-256-cbc -salt -pbkdf2 -pass "pass:$ENCRYPTION_KEY" -out "$BACKUP_DIR/downloads_$DATE.tar.gz.enc"
    echo "-> Downloads folder archived and encrypted."
else
    echo "Warning: Local downloads folder not found at $LOCAL_DOWNLOADS_DIR. Skipping files backup."
fi


# 4. Безопасная очистка старых бэкапов
echo "-> Cleaning up old backups (older than 7 days)..."
find "$BACKUP_DIR" -type f \( -name "*.sql.enc" -o -name "*.tar.gz.enc" \) -mtime +7 -delete
echo "-> Old backups cleaned up."

echo "=== Backup Complete Successfully ==="
