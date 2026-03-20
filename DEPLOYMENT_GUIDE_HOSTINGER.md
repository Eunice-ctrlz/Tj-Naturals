# TJNaturals Deployment Guide (Hostinger VPS)

This guide walks you through deploying your Django app on an Ubuntu VPS.

## 1. Local Preparation
(You have already run these)
- Dump database to JSON: `python manage.py dumpdata --exclude auth.permission --exclude contenttypes > datadump.json`
- Update requirements: `pip freeze > requirements.txt`
- Push your project to GitHub (or copy files to VPS).

## 2. Server Setup (SSH into VPS)
Update packages:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-dev libpq-dev postgresql postgresql-contrib nginx curl git -y
```

## 3. Database Setup (PostgreSQL)
Log into Postgres:
```bash
sudo -u postgres psql
```
Create Database & User:
```sql
CREATE DATABASE tjnaturals_db;
CREATE USER tjnaturals_user WITH PASSWORD 'strong_password_here';
ALTER ROLE tjnaturals_user SET client_encoding TO 'utf8';
ALTER ROLE tjnaturals_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE tjnaturals_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE tjnaturals_db TO tjnaturals_user;
\q
```

## 4. Project Setup
Clone repository or copy files to `/home/tjnaturals`:
```bash
mkdir -p /home/tjnaturals
cd /home/tjnaturals
# git clone ... or copy files here
```

Create Virtual Environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

Configure `.env` file (`nano .env`):
```ini
DEBUG=False
SECRET_KEY=your_production_secret_key
ALLOWED_HOSTS=your_domain.com,www.your_domain.com,server_ip_address

DB_NAME=tjnaturals_db
DB_USER=tjnaturals_user
DB_PASSWORD=strong_password_here
DB_HOST=localhost
DB_PORT=5432

EMAIL_HOST_USER=... (and other email settings)
```

Run Migrations & Static Files:
```bash
python manage.py collectstatic
python manage.py migrate
python manage.py loaddata datadump.json
python manage.py csu  # Create superuser custom command if needed, or create manually
```

## 5. Gunicorn Setup
Test Gunicorn:
```bash
gunicorn --bind 0.0.0.0:8000 TJNaturals.wsgi
```
(If it runs, Ctrl+C to stop)

Create Systemd Service (`sudo nano /etc/systemd/system/gunicorn.service`):
```ini
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/home/tjnaturals
ExecStart=/home/tjnaturals/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/home/tjnaturals/tjnaturals.sock TJNaturals.wsgi:application

[Install]
WantedBy=multi-user.target
```

Start & Enable Gunicorn:
```bash
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl status gunicorn
```

## 6. Nginx Setup
Create Config (`sudo nano /etc/nginx/sites-available/tjnaturals`):
```nginx
server {
    listen 80;
    server_name your_domain.com www.your_domain.com server_ip_address;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/tjnaturals;
    }

    location /media/ {
        root /home/tjnaturals;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/tjnaturals/tjnaturals.sock;
    }
}
```

Enable Site:
```bash
sudo ln -s /etc/nginx/sites-available/tjnaturals /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## 7. SSL with Certbot
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com -d www.your_domain.com
```
