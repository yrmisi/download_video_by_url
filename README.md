# 🎬 MediaGrab - Video & Audio Downloader

[![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Professional web application for downloading video and audio content from YouTube and other platforms with enterprise-grade security, monitoring, and reliability.

## 🚀 Features

### Core Functionality
- **Multi-format Downloads**: Support for video (MP4, MKV) and audio (MP3) extraction
- **Quality Selection**: From 144p to 4K (2160p) with device-specific presets
- **Device Profiles**: Optimized formats for PC/TV, legacy devices, mobile, and audio-only
- **Background Processing**: Async task queue with Redis status tracking
- **Download History**: User-specific history with pagination and caching

### Security & Reliability
- ✅ **SSRF Protection**: Blocks access to private IPs, localhost, and internal Docker services
- ✅ **Path Traversal Prevention**: Validates file paths against allowed directories
- ✅ **Request Timeouts**: Hard limits on yt-dlp (30min), metadata (30s), and cancellation (15s)
- ✅ **Encrypted Backups**: AES-256-CBC encryption for database and file backups
- ✅ **Rate Limiting**: Prevents API abuse (5 requests/minute per IP)
- ✅ **XSS Protection**: HTML escaping in frontend rendering
- ✅ **Memory Safety**: Proper cleanup of intervals and async tasks

### DevOps & Monitoring
- **Structured Logging**: JSON logs with correlation IDs for distributed tracing
- **Database Resilience**: Automatic retry on transient errors with exponential backoff
- **Slow Query Detection**: Alerts on queries exceeding 1 second
- **Prometheus Metrics**: Custom metrics for cleanup operations + HTTP instrumentation
- **Resource Limits**: CPU/memory constraints per container (Docker Compose)
- **Health Checks**: Automated health monitoring for all services
- **Graceful Shutdown**: Proper cleanup of background tasks and database connections

### Performance
- **Connection Pooling**: PostgreSQL pool with pre-ping and recycling
- **Redis Caching**: Metadata and history caching with TTL
- **Async I/O**: Non-blocking file operations via ThreadPoolExecutor
- **Concurrent Downloads**: Semaphore-limited parallel processing (max 3 simultaneous)

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────┐     ┌─────────────┐
│   Browser   │────▶│  Nginx   │────▶│  FastAPI    │
│  (Frontend) │     │(Reverse  │     │  (Granian)  │
└─────────────┘     │ Proxy)   │     └──────┬──────┘
                    └──────────┘            │
                                            │
                    ┌──────────┐     ┌──────▼──────┐
                    │PostgreSQL│◀───▶│ SQLAlchemy  │
                    │   (DB)   │     │  (Async)    │
                    └──────────┘     └──────┬──────┘
                                            │
                    ┌──────────┐     ┌──────▼──────┐
                    │  Redis   │◀───▶│  yt-dlp     │
                    │ (Cache/  │     │ (Executor)  │
                    │  Queue)  │     └──────┬──────┘
                    └──────────┘            │
                                            │
                                   ┌────────▼────────┐
                                   │ File System     │
                                   │ (downloads/)    │
                                   └─────────────────┘
```

### Technology Stack

**Backend:**
- **Framework**: FastAPI 0.136+ with Granian ASGI server
- **Database**: PostgreSQL 18.3 + SQLAlchemy 2.0 (async) + Alembic
- **Cache/Queue**: Redis 8.6 with hiredis
- **Media Processing**: yt-dlp + FFmpeg
- **Validation**: Pydantic 2.x with custom validators

**Frontend:**
- **UI**: Vanilla JavaScript + Tailwind CSS
- **Communication**: Fetch API with AbortController for timeouts
- **Storage**: localStorage for user ID persistence

**Infrastructure:**
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx with optimized buffering
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured JSON with correlation IDs

## 📋 Prerequisites

- Docker 24.0+ and Docker Compose 2.20+
- 4GB RAM minimum (8GB recommended for 4K downloads)
- 2 CPU cores minimum (4 cores recommended)
- Internet connection for pulling base images

## 🛠️ Installation & Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/download_video_by_url.git
cd download_video_by_url
```

### 2. Configure Environment Variables

Create environment files in `app/config/envs/`:

**`.env.postgres-prod`**:
```env
POSTGRES_USER=mediagrab_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=media_grab
POSTGRES_HOST=db
```

**`.env.redis-prod`**:
```env
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password_here
```

**`.env.app-prod`**:
```env
LOG_LEVEL=INFO
WINDOWS_HOST_IP=
ALLOWED_ORIGINS=http://localhost,http://yourdomain.com
APP_DNS_PRIMARY=1.1.1.1
APP_DNS_SECONDARY=8.8.8.8
ENCRYPTION_KEY=your_32_char_encryption_key_here
```

> ⚠️ **Security Note**: Generate a strong `ENCRYPTION_KEY` using: `openssl rand -hex 32`

### 3. Start Services

```bash
# Build and start all containers
docker compose up -d --build

# Check service health
docker compose ps

# View logs
docker compose logs -f web
```

### 4. Run Database Migrations

Migrations run automatically on startup via the `migrations` service. Verify:

```bash
docker compose logs migrations
# Should show: "INFO  [alembic.runtime.migration] Running upgrade -> <revision>"
```

### 5. Access Application

- **Web Interface**: http://localhost
- **API Docs**: http://localhost/docs (Swagger UI)
- **Metrics**: http://localhost/metrics (Prometheus format)
- **Grafana**: http://localhost:3000 (default: admin/admin)
- **PostgreSQL**: localhost:5432 (bound to 127.0.0.1 only)
- **Redis**: localhost:6379 (bound to 127.0.0.1 only)

## 🔧 Configuration

### Download Profiles

| Profile | Description | Format | Max Quality | Use Case |
|---------|-------------|--------|-------------|----------|
| `pc_tv` | Modern devices | MKV (VP9/AV1) | 4K (2160p) | New Smart TVs, PCs |
| `legacy_tv` | Older devices | MP4 (H.264) | Configurable | Old Samsung/LG TVs |
| `mobile` | Smartphones | MP4 (H.264) | 720p | Mobile data saving |
| `mp4` | Universal | MP4 | 1080p | Quick single-file download |
| `audio_only` | Audio extraction | MP3 | 192kbps | Music/podcasts |

### Resource Limits

Default container resource allocation:

```yaml
web:          1 CPU, 1GB RAM
cron_worker:  2 CPUs, 2GB RAM  # For FFmpeg processing
db:           0.5 CPU, 512MB RAM
redis:        0.5 CPU, 512MB RAM
nginx:        0.5 CPU, 512MB RAM
```

Adjust in `docker-compose.yaml` under `deploy.resources.limits`.

### Cleanup Policies

- **Expired Downloads**: Files deleted 1 hour after completion
- **Trash Cleanup**: `.part`, `.ytdl` files removed after 3 hours
- **Orphaned Files**: Any file older than 24 hours removed daily
- **Database Records**: Status updated to `deleted` after file removal

## 📊 Monitoring & Observability

### Structured Logging

All logs are JSON-formatted with correlation IDs:

```json
{
  "timestamp": "2026-07-07T18:30:45.123Z",
  "level": "INFO",
  "logger": "app.services.worker",
  "message": "Task abc-123 finished",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "module": "worker",
  "func_name": "run_download",
  "line_no": 145
}
```

View logs:
```bash
docker compose logs -f web | jq '.'  # Pretty-print JSON
```

### Prometheus Metrics

Custom metrics available at `/metrics`:

- `mediagrab_cleanup_files_removed_total{cleanup_type="expired_task"}` - Files removed by hourly cleanup
- `mediagrab_cleanup_files_removed_total{cleanup_type="daily_deep"}` - Files removed by daily trash cleanup
- `http_requests_total` - Total HTTP requests (auto-instrumented)
- `http_request_duration_seconds` - Request latency histogram

### Grafana Dashboards

Pre-configured dashboard at `monitoring/grafana/dashboards/fastapi.json`:
- Request rate and latency
- Error rates by endpoint
- Database query performance
- Redis cache hit/miss ratio

Access: http://localhost:3000 (login: admin/admin)

### Slow Query Detection

Queries exceeding 1 second are logged with full SQL:

```
WARNING  app.database.db_telemetry: Slow query detected (2.3451s)!
Statement: SELECT * FROM download_history WHERE status = %s AND created_at < %s
Parameters: ('finished', '2026-07-07 17:30:45')
```

## 🔒 Security Features

### SSRF Protection

All URLs are validated before processing:
- ❌ Blocked: `http://127.0.0.1:6379`, `http://192.168.1.1`, `http://localhost`
- ❌ Blocked: Docker internal names (`db`, `redis`, `nginx`)
- ❌ Blocked: Private IP ranges (10.x, 172.16-31.x, 192.168.x)
- ✅ Allowed: Public URLs only

Implementation: `app/schemas/load_media.py::validate_ssrf()`

### Path Traversal Prevention

File serving validates physical location:

```python
if not Path(file_path).resolve().is_relative_to(DOWNLOADS_DIR):
    raise HTTPException(403, "Access denied")
```

### Encrypted Backups

Backups use AES-256-CBC encryption:

```bash
# Manual backup
./backups/backup.sh

# Restore database
openssl enc -aes-256-cbc -d -pbkdf2 -pass "pass:$ENCRYPTION_KEY" \
  -in backups/db_20260707_183045.sql.enc | \
  docker compose exec -T db psql -U $POSTGRES_USER $POSTGRES_DB
```

### Rate Limiting

- **Download endpoint**: 5 requests/minute per IP
- **Info extraction**: No limit (cached in Redis)
- **Status polling**: No limit (lightweight Redis lookup)

Exceeding limits returns HTTP 429.

## 🧪 Testing & QA

### Edge Cases to Test

See comprehensive QA checklist in project documentation. Key scenarios:

1. **Security Tests**:
   - SSRF attempts with internal IPs
   - Path traversal via manipulated task IDs
   - XSS payloads in video titles

2. **Reliability Tests**:
   - Cancel download at 95% progress
   - Network interruption during polling
   - Disk full scenario
   - Concurrent downloads (4+ simultaneous)

3. **Performance Tests**:
   - 4K video (2GB+) download
   - 100+ item history pagination
   - Redis failure recovery
   - Database connection drops

### Load Testing

```bash
# Install k6
docker run -i loadimpact/k6 run - <<EOF
import http from 'k6/http';
import { check } from 'k6';

export default function () {
  const res = http.get('http://localhost/health');
  check(res, { 'status is 200': (r) => r.status === 200 });
}
EOF
```

## 🔄 Backup & Recovery

### Automated Backups

Configure cron job for daily backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /home/user/PythonProjects/download_video_by_url/backups/backup.sh >> /var/log/mediagrab_backup.log 2>&1
```

### Backup Contents

- **Database**: Encrypted PostgreSQL dump (`.sql.enc`)
- **Downloads**: Archived media files (`.tar.gz.enc`)
- **Retention**: 7 days (configurable in backup.sh)

### Disaster Recovery

```bash
# 1. Stop services
docker compose down

# 2. Restore database
openssl enc -aes-256-cbc -d -pbkdf2 -pass "pass:$ENCRYPTION_KEY" \
  -in backups/db_TIMESTAMP.sql.enc | \
  docker compose run --rm -T db psql -U $POSTGRES_USER $POSTGRES_DB

# 3. Restore downloads (if using bind mount)
tar -xzf <(openssl enc -aes-256-cbc -d -pbkdf2 -pass "pass:$ENCRYPTION_KEY" \
  -in backups/downloads_TIMESTAMP.tar.gz.enc) -C /path/to/downloads

# 4. Restart services
docker compose up -d
```

## 🐛 Troubleshooting

### Common Issues

**Issue**: Download stuck at "Processing video via FFmpeg..."
```bash
# Check worker logs
docker compose logs cron_worker | grep "Task <task_id>"

# Verify disk space
docker compose exec web df -h /app/downloads

# Check FFmpeg availability
docker compose exec web ffmpeg -version
```

**Issue**: "Access to private IP ranges is forbidden"
- This is expected behavior for internal URLs
- Only public URLs are allowed for security reasons

**Issue**: Database connection timeout
```bash
# Check PostgreSQL health
docker compose exec db pg_isready -U $POSTGRES_USER

# View connection pool stats
docker compose logs web | grep "pool"

# Restart database
docker compose restart db
```

**Issue**: High memory usage
```bash
# Check container resource usage
docker stats

# Restart memory-heavy containers
docker compose restart web cron_worker

# Clear Redis cache
docker compose exec redis redis-cli FLUSHDB
```

### Log Analysis

Search for errors with correlation ID:

```bash
# Find all logs for a specific request
docker compose logs web | grep "request_id\": \"abc-123\""

# Find slow queries
docker compose logs web | grep "Slow query"

# Find failed downloads
docker compose logs web | grep '"status": "error"'
```

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] Change all default passwords in `.env` files
- [ ] Generate strong `ENCRYPTION_KEY` (32+ characters)
- [ ] Set `ALLOWED_ORIGINS` to your domain(s)
- [ ] Configure SSL/TLS termination (add HTTPS proxy)
- [ ] Set up external backup storage (S3, GCS, etc.)
- [ ] Configure firewall rules (only ports 80, 443 open)
- [ ] Enable Docker log rotation (already configured)
- [ ] Set up alerting for Prometheus metrics
- [ ] Test backup restoration procedure
- [ ] Review resource limits for your hardware
- [ ] Enable fail2ban or similar for DDoS protection

## 📈 Performance Tuning

### Database Optimization

Current indexes:
- `idx_download_history_status_created` - Composite index for cleanup queries
- `user_id` - Index for history lookups
- `title` - Index for search (nullable)

Add custom indexes if needed:
```bash
docker compose exec db psql -U $POSTGRES_USER $POSTGRES_DB
CREATE INDEX idx_custom ON download_history (user_id, created_at DESC);
```

### Redis Optimization

Current settings:
- Max memory: 256MB
- Eviction policy: allkeys-lru
- Persistence: AOF enabled

Monitor usage:
```bash
docker compose exec redis redis-cli INFO memory
```

### yt-dlp Optimization

- Socket timeout: 15 seconds
- Retries: 10 (download), 10 (fragments)
- Proxy support: SOCKS5 configurable via env vars

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Development Setup

```bash
# Start dev environment (exposes ports)
docker compose -f docker-compose.dev.yaml up -d

# Run linters
docker compose exec web black app/
docker compose exec web isort app/

# Run type checking
docker compose exec web mypy app/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Powerful media extraction library
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Granian](https://github.com/emmett-framework/granian) - High-performance ASGI server
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework

---

**Built with ❤️ for the open-source community**

For questions or support, please open an issue on GitHub.
