# Garage Management Backend - Deployment Guide

## Quick Start Options

### Option 1: Docker Compose (Recommended for self-hosting)

1. **Clone and setup:**
```bash
git clone <your-repo-url>
cd backend
cp .env.production .env
# Edit .env with your actual values
```

2. **Generate secret key:**
```bash
openssl rand -hex 32
# Copy this to SECRET_KEY in .env
```

3. **Start services:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

4. **Check logs:**
```bash
docker-compose -f docker-compose.prod.yml logs -f api
```

### Option 2: Railway/Render (Easiest)

1. Push code to GitHub
2. Connect Railway or Render to your repo
3. Add environment variables in dashboard
4. Deploy automatically

### Option 3: AWS/GCP/Azure

1. **Create VM instance** (Ubuntu 22.04 LTS recommended)
2. **Install Docker:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER
```

3. **Deploy:**
```bash
git clone <your-repo>
cd backend
docker-compose -f docker-compose.prod.yml up -d
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | JWT signing key (generate with `openssl rand -hex 32`) |
| `ALLOWED_ORIGINS` | Yes | Frontend domain(s), comma-separated |
| `ADMIN_PASSWORD` | Yes | Strong admin password |
| `WORKERS` | No | Number of API workers (default: 4) |

## CORS Configuration for Flutter

### For Flutter Web:
```env
ALLOWED_ORIGINS=https://your-app.web.app,https://your-app.firebaseapp.com
```

### For Flutter Mobile (iOS/Android):
Mobile apps don't use CORS, so you can use:
```env
ALLOWED_ORIGINS=*
```

Or specify your API domain for security:
```env
ALLOWED_ORIGINS=https://your-api.com
```

### For Local Development:
```env
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,http://10.0.2.2:8000
```

**Note:** `10.0.2.2` is for Android emulator to reach localhost

## Database Setup

### Using Docker (included):
PostgreSQL runs automatically in docker-compose.prod.yml

### Using Managed Database:
1. Create PostgreSQL database (AWS RDS, Supabase, etc.)
2. Update `DATABASE_URL`:
```env
DATABASE_URL=postgresql://user:pass@your-db-host.com:5432/dbname
```
3. Remove `db` service from docker-compose.prod.yml

## SSL/HTTPS Setup

### Option 1: Let's Encrypt (Free)
```bash
# Install certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/
```

### Option 2: Cloudflare (Easiest)
1. Use Cloudflare as DNS proxy
2. Enable "Full (Strict)" SSL mode
3. No certificate management needed

## Testing Your Deployment

1. **Health check:**
```bash
curl https://your-domain.com/
```

2. **API docs:**
Open `https://your-domain.com/docs` in browser

3. **Test login:**
```bash
curl -X POST https://your-domain.com/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_admin_password"
```

## Updating Deployment

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# View logs
docker-compose -f docker-compose.prod.yml logs -f api
```

## Troubleshooting

### Database connection errors:
```bash
# Check database is running
docker-compose -f docker-compose.prod.yml ps

# View database logs
docker-compose -f docker-compose.prod.yml logs db
```

### CORS errors:
- Check `ALLOWED_ORIGINS` includes your frontend domain
- For mobile, use `*` or specific domain

### Port already in use:
```bash
# Change port in docker-compose.prod.yml
ports:
  - "8080:8000"  # Use 8080 instead of 8000
```

## Free Hosting Options

| Platform | Pros | Cons |
|----------|------|------|
| **Railway** | Easy deploy, free tier | Limited free hours |
| **Render** | Free tier, auto-deploy | Sleep after inactivity |
| **Fly.io** | Generous free tier | Requires CLI |
| **Oracle Cloud** | Always free tier | Complex setup |

## Recommended for Production

1. **Database:** Supabase (free tier) or AWS RDS
2. **API Hosting:** Railway or Render
3. **File Storage:** AWS S3 or Cloudflare R2
4. **Domain:** Cloudflare (free DNS + SSL)

## Security Checklist

- [ ] Changed default admin password
- [ ] Generated strong SECRET_KEY
- [ ] Set specific ALLOWED_ORIGINS (not `*`)
- [ ] Using HTTPS
- [ ] Database password is strong
- [ ] Removed `--reload` from production
- [ ] Set up firewall (only 80/443 open)

## Support

For issues, check:
1. Docker logs: `docker-compose logs`
2. API docs: `/docs` endpoint
3. Tests: `docker-compose exec api pytest`
