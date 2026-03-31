# Tutorial Deploy Uptime Monitor di VPS

## Prasyarat

- VPS dengan Ubuntu 20.04+ atau Debian 11+
- Domain (opsional, tapi recommended)
- SSH access ke VPS
- Minimal 2GB RAM, 10GB storage

## Step 1: Setup Server & Install Dependencies

```bash
# SSH ke VPS
ssh root@your_vps_ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker root

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

## Step 2: Clone Repository

```bash
# Pilih direktori deployment (misal /opt)
cd /opt

# Clone repo
git clone https://github.com/wahyurap/uptime-monitor.git
cd uptime-monitor
```

## Step 3: Configure Environment

```bash
# Copy .env template
cp .env.example .env  # atau buat baru

# Edit .env
nano .env
```

**Isi .env:**
```env
# Database
UPTIME_DATABASE_URL=postgresql+asyncpg://uptime:uptime_secure_password@db:5432/uptime_monitor
UPTIME_DATABASE_URL_SYNC=postgresql://uptime:uptime_secure_password@db:5432/uptime_monitor

# Application
UPTIME_DEFAULT_PING_INTERVAL=60
UPTIME_PING_TIMEOUT=2.0
UPTIME_PING_RETRIES=3
UPTIME_PING_BATCH_SIZE=50
UPTIME_PING_RETENTION_DAYS=90
```

**Ubah password default!** Gunakan password yang kuat:
```bash
# Generate password aman
openssl rand -base64 24
```

## Step 4: Update docker-compose.yml

Ubah file `docker-compose.yml` untuk production:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: uptime
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-uptime_secure_password}
      POSTGRES_DB: uptime_monitor
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U uptime -d uptime_monitor"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      UPTIME_DATABASE_URL: postgresql+asyncpg://uptime:${POSTGRES_PASSWORD:-uptime_secure_password}@db:5432/uptime_monitor
      UPTIME_DATABASE_URL_SYNC: postgresql://uptime:${POSTGRES_PASSWORD:-uptime_secure_password}@db:5432/uptime_monitor
    depends_on:
      db:
        condition: service_healthy
    cap_add:
      - NET_RAW
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs

volumes:
  pgdata:
    driver: local
```

## Step 5: Setup Reverse Proxy (Nginx)

Gunakan Nginx untuk production (HTTPS, load balancing, security headers):

```bash
# Install Nginx
apt install -y nginx certbot python3-certbot-nginx

# Buat config Nginx
nano /etc/nginx/sites-available/uptime-monitor
```

**Config Nginx** (`/etc/nginx/sites-available/uptime-monitor`):
```nginx
upstream uptime_app {
    server localhost:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP ke HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificate (akan di-generate oleh Certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    location / {
        proxy_pass http://uptime_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # WebSocket support (jika diperlukan)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /static/ {
        proxy_pass http://uptime_app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

**Enable site:**
```bash
ln -s /etc/nginx/sites-available/uptime-monitor /etc/nginx/sites-enabled/
nginx -t  # Test config
systemctl restart nginx
```

## Step 6: Setup SSL Certificate

```bash
# Ganti your-domain.com dengan domain Anda
certbot certonly --nginx -d your-domain.com

# Auto-renewal
systemctl enable certbot.timer
systemctl start certbot.timer
```

## Step 7: Start Application

```bash
# Buat .env file dengan password dari Step 3
export POSTGRES_PASSWORD="your_secure_password_here"

# Build dan start services
docker-compose up -d --build

# Check logs
docker-compose logs -f app

# Verify database
docker-compose exec db psql -U uptime -d uptime_monitor -c "\dt"
```

## Step 8: Verify Deployment

```bash
# Check containers running
docker-compose ps

# Test API
curl http://localhost:8000/api/v1/health

# Check Nginx
curl https://your-domain.com/api/v1/health
```

## Step 9: Add Servers untuk Monitoring

Setelah aplikasi running, tambahkan server via API:

```bash
# Tambah server
curl -X POST https://your-domain.com/api/v1/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Google DNS",
    "ip_address": "8.8.8.8",
    "group_name": "Public DNS",
    "ping_interval": 60,
    "is_active": true
  }'

# Lihat semua server
curl https://your-domain.com/api/v1/servers

# Cek availability
curl "https://your-domain.com/api/v1/servers/{server_id}/availability?range=daily"
```

## Step 10: Backup & Maintenance

### Regular Backup

```bash
# Backup database
docker-compose exec db pg_dump -U uptime uptime_monitor > uptime_backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker-compose exec -T db psql -U uptime uptime_monitor < uptime_backup_20240315_120000.sql
```

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild dan restart
docker-compose up -d --build

# Check logs
docker-compose logs -f app
```

### Monitor Disk Usage

```bash
# Check Docker storage
docker system df

# Cleanup old images/containers
docker system prune -a

# Auto-cleanup old ping results
# (Already handled by scheduler di app)
```

## Step 11: Monitoring & Logging

### View Logs

```bash
# Real-time logs
docker-compose logs -f app

# Database logs
docker-compose logs -f db

# Last N lines
docker-compose logs --tail=100 app
```

### Monitor System Resources

```bash
# Install monitoring tools
apt install -y htop iotop nethogs

# Monitor containers
docker stats

# Monitor disk
df -h
du -sh /var/lib/docker/volumes/uptime-monitor_pgdata/_data
```

## Troubleshooting

### PostgreSQL Connection Error

```bash
# Check database status
docker-compose ps db

# View database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### High Memory Usage

```bash
# Check container memory
docker stats

# Reduce retention days di .env
UPTIME_PING_RETENTION_DAYS=30  # Dari 90 ke 30
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Atau ubah port di docker-compose.yml
ports:
  - "8001:8000"  # Map ke port berbeda
```

### SSL Certificate Error

```bash
# Renew certificate
certbot renew --force-renewal

# Check certificate
certbot certificates
```

## Production Checklist

- [ ] Database password di-change dari default
- [ ] SSL certificate di-setup
- [ ] Nginx reverse proxy di-configure
- [ ] Backup strategy di-setup
- [ ] Monitoring & alerting di-configure (opsional)
- [ ] Firewall rules di-setup (hanya port 80, 443, SSH)
- [ ] Auto-restart di-enable (restart: unless-stopped)
- [ ] Log rotation di-configure
- [ ] DNS pointing ke domain

## Firewall Setup (UFW)

```bash
# Enable UFW
ufw enable

# Allow SSH (penting! jangan lock out)
ufw allow 22/tcp

# Allow HTTP & HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Check rules
ufw status
```

## Perintah Useful

```bash
# Restart semua services
docker-compose restart

# Stop semua services
docker-compose down

# Remove all data (WARNING!)
docker-compose down -v

# Scale aplikasi (jika perlu)
docker-compose up -d --scale app=2  # Perlu load balancer

# Exec command di container
docker-compose exec app python -c "print('Hello')"

# View specific service logs
docker-compose logs app -f --tail=50
```

## Support & Issues

- **GitHub Issues**: https://github.com/wahyurap/uptime-monitor/issues
- **Docker Logs**: `docker-compose logs -f`
- **Database**: Akses via psql atau admin tools

---

Selamat! Aplikasi Uptime Monitor sudah di-deploy. Monitor dashboard di `https://your-domain.com`
