# Uptime Monitor

🚀 Server uptime monitoring application via ICMP with availability calculation, REST API, dan web dashboard.

[![GitHub](https://img.shields.io/badge/GitHub-wahyurap/uptime--monitor-blue?style=flat-square)](https://github.com/wahyurap/uptime-monitor)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)]()

## Features

- ✅ **ICMP Ping Monitoring** — Ping server berkala dengan retry logic & batch processing
- 📊 **Availability Calculation** — Daily/weekly/monthly/custom timerange availability %
- 📈 **Downtime Detection** — Automatic downtime incident detection & logging
- 🌐 **REST API** — Complete API untuk CRUD server, query ping history, availability stats
- 📱 **Web Dashboard** — Real-time status, latency charts, availability trends
- 🔄 **Background Scheduler** — APScheduler untuk automated ping, aggregation, cleanup
- 🗄️ **PostgreSQL** — Time-series optimized database dengan indexing
- 🐳 **Docker Ready** — Production-ready Docker & docker-compose setup
- 🔒 **Security** — Nginx reverse proxy, SSL/TLS, environment-based config

## Tech Stack

- **Backend**: Python 3.12 + FastAPI
- **Database**: PostgreSQL 16
- **Async**: asyncio, asyncpg, SQLAlchemy 2.0
- **Scheduler**: APScheduler
- **ICMP**: aioping (fallback: subprocess ping)
- **Frontend**: Jinja2 + HTMX + Chart.js + TailwindCSS
- **Deployment**: Docker + docker-compose + Nginx

## Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/wahyurap/uptime-monitor.git
cd uptime-monitor

# Start services (Docker required)
docker-compose up --build

# Access dashboard
open http://localhost:8000
```

### Add First Server

```bash
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Google DNS",
    "ip_address": "8.8.8.8",
    "ping_interval": 60
  }'
```

## API Endpoints

### Servers
```
GET    /api/v1/servers              # List all servers
POST   /api/v1/servers              # Create server
GET    /api/v1/servers/{id}         # Get server detail
PUT    /api/v1/servers/{id}         # Update server
DELETE /api/v1/servers/{id}         # Delete server
```

### Availability
```
GET    /api/v1/servers/{id}/availability?range=daily|weekly|monthly|3months|6months|yearly|custom
GET    /api/v1/availability/summary # All servers availability summary (untuk dashboard/integration)
```

### Ping History
```
GET    /api/v1/servers/{id}/pings?page=1&page_size=50&start=2026-03-01T00:00:00Z&end=2026-03-31T23:59:59Z
```

### Health
```
GET    /api/v1/health               # App health check
```

## Configuration

Edit `.env` atau set environment variables:

```env
# Database
UPTIME_DATABASE_URL=postgresql+asyncpg://uptime:password@db:5432/uptime_monitor
UPTIME_DATABASE_URL_SYNC=postgresql://uptime:password@db:5432/uptime_monitor

# Ping defaults
UPTIME_DEFAULT_PING_INTERVAL=60          # seconds
UPTIME_PING_TIMEOUT=2.0                  # seconds
UPTIME_PING_RETRIES=3
UPTIME_PING_BATCH_SIZE=50                # concurrent pings

# Data retention
UPTIME_PING_RETENTION_DAYS=90            # cleanup old pings

# Dashboard
UPTIME_DASHBOARD_REFRESH_SECONDS=30      # auto-refresh interval
```

## Deployment

See [DEPLOY.md](DEPLOY.md) for complete production deployment guide including:
- VPS setup dengan Ubuntu/Debian
- Docker & docker-compose installation
- Nginx reverse proxy configuration
- SSL/TLS dengan Let's Encrypt
- Database backup & maintenance
- Monitoring & logging setup

**TL;DR:**
```bash
# 1. Clone & configure
git clone https://github.com/wahyurap/uptime-monitor.git
cd uptime-monitor
cp .env.example .env
# Edit .env dengan credentials

# 2. Start services
docker-compose up -d --build

# 3. Setup Nginx & SSL (see DEPLOY.md for details)

# 4. Access via https://your-domain.com
```

## Database Schema

### servers
- `id` (UUID) — Primary key
- `name` (string) — Server name/label
- `ip_address` (string) — IPv4/IPv6 address
- `group_name` (string) — Grouping (optional)
- `ping_interval` (int) — Ping interval dalam detik
- `is_active` (bool) — Enable/disable monitoring
- `created_at`, `updated_at` (timestamp)

### ping_results
- `id` (BIGINT) — Primary key
- `server_id` (UUID FK) — Reference ke servers
- `is_up` (bool) — Ping success/failure
- `latency_ms` (float) — Response time
- `timestamp` (timestamp) — Ping time

**Index**: `(server_id, timestamp)` untuk efficient time-range queries

### daily_availability (pre-computed)
- `id` (BIGINT) — Primary key
- `server_id` (UUID FK)
- `date` (date)
- `total_pings`, `success_pings` (int)
- `availability_pct` (float)
- `avg_latency` (float)

Pre-computed daily aggregates untuk fast weekly/monthly queries.

## Scheduler Jobs

- **ping_all** — Every 60s (default): Ping all active servers
- **daily_aggregation** — Every day at 00:05 UTC: Aggregate daily stats
- **cleanup_old_pings** — Every day at 01:00 UTC: Delete pings older than retention period

## API Response Examples

### Get Availability
```json
{
  "server_id": "550e8400-e29b-41d4-a716-446655440000",
  "server_name": "Web Server 1",
  "range": "monthly",
  "start": "2026-03-01T00:00:00+00:00",
  "end": "2026-03-31T23:59:59+00:00",
  "availability_pct": 99.85,
  "total_pings": 43200,
  "successful_pings": 43135,
  "avg_latency_ms": 12.5,
  "downtime_incidents": [
    {
      "start": "2026-03-15T02:10:00+00:00",
      "end": "2026-03-15T02:25:00+00:00",
      "duration_minutes": 15.0
    }
  ]
}
```

### List Servers
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Google DNS",
    "ip_address": "8.8.8.8",
    "group_name": "Public DNS",
    "ping_interval": 60,
    "is_active": true,
    "current_status": "up",
    "last_latency_ms": 8.5,
    "last_check": "2026-03-31T10:30:45+00:00"
  }
]
```

## Troubleshooting

### Containers not starting
```bash
docker-compose logs -f app
docker-compose logs -f db
```

### High memory usage
- Reduce `UPTIME_PING_RETENTION_DAYS`
- Increase `UPTIME_PING_BATCH_SIZE` untuk batch processing lebih efisien

### Permission denied for ICMP
```bash
# Ensure container has NET_RAW capability (sudah di-setup di docker-compose.yml)
# Atau run as root (less secure)
```

### Database connection error
```bash
# Verify database is running
docker-compose ps db

# Check credentials di .env
# Restart database
docker-compose restart db
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start app locally (requires PostgreSQL)
uvicorn app.main:app --reload

# Run tests
pytest tests/

# Format code
black app/
flake8 app/
```

## File Structure

```
uptime-monitor/
├── app/
│   ├── api/              # API routers
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic (pinger, scheduler, availability)
│   ├── templates/        # Jinja2 templates
│   ├── static/           # CSS, JS, images
│   ├── config.py         # Configuration
│   ├── database.py       # Database setup
│   └── main.py           # FastAPI app
├── alembic/              # Database migrations
├── tests/                # Test suite
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Container image
├── requirements.txt      # Python dependencies
├── DEPLOY.md             # Deployment guide
└── README.md             # This file
```

## Contributing

Issues dan pull requests welcome!

## License

MIT License — see LICENSE file

## Support

- 📖 [Deployment Guide](DEPLOY.md)
- 🐛 [Report Issues](https://github.com/wahyurap/uptime-monitor/issues)
- 💬 Discussions

---

Made with ❤️ using FastAPI, PostgreSQL, and Python asyncio
