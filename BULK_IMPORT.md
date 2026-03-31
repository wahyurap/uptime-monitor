# Bulk Import Guide

Panduan untuk bulk import 50+ server sekaligus menggunakan CSV.

## Fitur

✅ **CSV Upload** — Upload file CSV dengan 50-5000 server sekaligus
✅ **Tags Support** — Assign multiple tags per server (e.g., KSO_FH, KSO_HW, KSO_ZTE)
✅ **Group Management** — Organize servers by group
✅ **Custom Ping Interval** — Set interval per server
✅ **Error Reporting** — Detailed error feedback untuk troubleshooting
✅ **Web UI** — User-friendly upload interface di `/bulk-import`
✅ **API Endpoint** — Programmatic import via POST `/api/v1/servers/bulk/import`

## Quick Start

### 1. Via Web UI (Recommended)

- Buka http://localhost:8000/bulk-import
- Klik **Download Template** untuk mendapat CSV template
- Edit file dengan data server Anda
- Upload file CSV
- Review hasil import

### 2. Via API

```bash
# Upload CSV file
curl -X POST http://localhost:8000/api/v1/servers/bulk/import \
  -F "file=@servers.csv"
```

## CSV Format

### File Format

```csv
name,ip_address,group_name,tags,ping_interval
Web Server 1,192.168.1.1,KSO_FH,web;production,60
Web Server 2,192.168.1.2,KSO_FH,web;production,60
DNS Server,8.8.8.8,KSO_HW,dns;external,120
Mail Server,mail.example.com,KSO_ZTE,mail;critical,30
```

### Column Description

| Column | Required | Format | Notes |
|--------|----------|--------|-------|
| **name** | ✓ | String (max 255) | Server name/label |
| **ip_address** | ✓ | IPv4/IPv6 | 192.168.1.1 or 2001:db8::1 |
| **group_name** | ✗ | String (max 100) | e.g., KSO_FH, KSO_HW |
| **tags** | ✗ | Semicolon-separated | e.g., web;production;critical |
| **ping_interval** | ✗ | Integer (seconds) | Default: 60 |

## Examples

### Example 1: Simple Web Servers

```csv
name,ip_address,group_name,tags,ping_interval
Web-1,192.168.1.10,KSO_FH,web,60
Web-2,192.168.1.11,KSO_FH,web,60
Web-3,192.168.1.12,KSO_FH,web,60
```

### Example 2: Mixed Infrastructure

```csv
name,ip_address,group_name,tags,ping_interval
prod-web-01,10.0.1.10,KSO_FH,web;production;critical,30
prod-web-02,10.0.1.11,KSO_FH,web;production;critical,30
prod-db-01,10.0.2.10,KSO_FH,database;production;critical,60
staging-web-01,10.0.3.10,KSO_FH,web;staging,120
external-dns,8.8.8.8,KSO_HW,dns;external;public,60
cloudflare-dns,1.1.1.1,KSO_HW,dns;external;public,60
```

### Example 3: With Custom Ping Intervals

```csv
name,ip_address,group_name,tags,ping_interval
critical-api,10.0.1.1,KSO_FH,api;critical,15
database-primary,10.0.2.1,KSO_FH,database;critical,30
backup-server,10.0.4.1,KSO_ZTE,backup,300
monitoring-host,10.0.5.1,KSO_HW,monitoring,120
```

## Tags Strategy

Recommended tag structure untuk organisasi:

### By Type
- `web` — Web servers
- `database` — Database servers
- `cache` — Cache servers (Redis, Memcached)
- `api` — API servers
- `dns` — DNS servers
- `mail` — Mail servers
- `backup` — Backup servers

### By Environment
- `production` — Production environment
- `staging` — Staging environment
- `development` — Development environment
- `testing` — Testing environment

### By Importance
- `critical` — Critical infrastructure
- `high` — High importance
- `normal` — Normal importance

### By Owner/Group (sudah ada di group_name)
- `KSO_FH` — Group/Department FH
- `KSO_HW` — Group/Department HW
- `KSO_ZTE` — Group/Department ZTE

### Example Combined Tags
```
web;production;critical,KSO_FH
database;production;critical,KSO_FH
api;staging;normal,KSO_HW
```

## API Response

### Success Response

```json
{
  "success": true,
  "created": 48,
  "skipped": 2,
  "errors": [
    "Row 15: invalid IP address: 999.999.999.999",
    "Row 42: name and ip_address required"
  ],
  "total_errors": 2
}
```

### Error Response

```json
{
  "success": false,
  "message": "CSV parsing error: File encoding error"
}
```

## Bulk Operations

### Query by Tag

```bash
# Get all servers dengan tag 'production'
curl http://localhost:8000/api/v1/servers?tag=production

# Get all servers dengan tag 'KSO_FH' dari group_name
curl http://localhost:8000/api/v1/servers?group=KSO_FH
```

### Query by Group

```bash
# Get semua servers di grup KSO_FH
curl http://localhost:8000/api/v1/servers?group=KSO_FH
```

### Combined Filter

```bash
# Get production web servers di KSO_FH
curl http://localhost:8000/api/v1/servers?group=KSO_FH&tag=production
```

## Preparation Checklist

Sebelum bulk import, siapkan:

- [ ] Export/list semua IP address yang ingin dimonitor
- [ ] Organize by group (KSO_FH, KSO_HW, KSO_ZTE, dst)
- [ ] Assign tags untuk setiap server (tipe, environment, importance)
- [ ] Decide ping interval (default 60s, critical bisa 30s)
- [ ] Create CSV file dengan format yang benar
- [ ] Validate IP addresses (test connectivity jika perlu)
- [ ] Check for duplicates dalam list
- [ ] Review CSV file sebelum upload
- [ ] Import ke staging terlebih dahulu (jika ada)

## Troubleshooting

### "Row X: invalid IP address"
```
Pastikan format IP valid:
✓ 192.168.1.1 (IPv4)
✓ 8.8.8.8 (IPv4)
✓ 2001:db8::1 (IPv6)
✗ 256.256.256.256 (invalid)
✗ not-an-ip (invalid)
```

### "Row X: name and ip_address required"
```
Pastikan setiap row punya:
- Column 'name' tidak kosong
- Column 'ip_address' tidak kosong
```

### File upload tidak menerima
```
Pastikan:
- File extension: .csv
- File encoding: UTF-8
- File size: < 10MB
```

### CSV parse error: Line XX
```
Cek:
- Format CSV valid (comma-separated)
- Tidak ada line breaks dalam field
- Text enclosed in quotes jika ada comma: "Server, Description"
```

### Ping interval error
```
ping_interval harus integer:
✓ 30, 60, 120, 300
✗ "60s", "1m", "1 minute"
```

## Best Practices

1. **Test dengan sample kecil dulu** — Import 5-10 server untuk test sebelum bulk
2. **Validate data** — Check duplicate IPs, invalid addresses sebelum import
3. **Use meaningful names** — Hindari generic names, gunakan naming convention
4. **Organize dengan tags** — Jangan rely hanya pada group_name
5. **Document your schema** — Simpan template CSV untuk referensi
6. **Batch imports** — Jika 5000+ server, split ke beberapa batch
7. **Monitor imports** — Check logs setelah import besar
8. **Verify connectivity** — Pastikan network dapat reach servers sebelum monitoring

## Limits

- **Max servers per import**: 5000 (split jika lebih besar)
- **CSV file size**: < 10MB
- **Max tags per server**: 50
- **Max group servers**: 10,000
- **Batch processing**: 50 servers concurrent ping

## Advanced: Programmatic Import

### Python Example

```python
import csv
import requests

API_URL = "http://localhost:8000/api/v1"

# Read CSV dan create servers
with open('servers.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        server = {
            'name': row['name'],
            'ip_address': row['ip_address'],
            'group_name': row.get('group_name'),
            'tags': row.get('tags', '').split(';'),
            'ping_interval': int(row.get('ping_interval', 60))
        }
        response = requests.post(f"{API_URL}/servers", json=server)
        print(f"Created: {server['name']} - {response.status_code}")
```

### Bash Example

```bash
#!/bin/bash
API_URL="http://localhost:8000/api/v1"

while IFS=',' read -r name ip group tags interval; do
    [ "$name" == "name" ] && continue  # Skip header

    curl -X POST "$API_URL/servers" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"$name\",
        \"ip_address\": \"$ip\",
        \"group_name\": \"$group\",
        \"tags\": [\"${tags//;/\",\"}\"],
        \"ping_interval\": $interval
      }"
done < servers.csv
```

## Monitoring Bulk Operations

Setelah import besar:

```bash
# Check berapa servers aktif
curl http://localhost:8000/api/v1/servers | jq length

# Check servers per group
curl "http://localhost:8000/api/v1/servers?group=KSO_FH" | jq length

# Check servers per tag
curl "http://localhost:8000/api/v1/servers?tag=production" | jq length

# Check availability summary
curl http://localhost:8000/api/v1/availability/summary | jq '.[] | {name: .server_name, status: .current_status}'
```

## Support

- 📖 [README.md](README.md)
- 🐛 [Report Issues](https://github.com/wahyurap/uptime-monitor/issues)
- 📊 Bulk import page: http://localhost:8000/bulk-import
