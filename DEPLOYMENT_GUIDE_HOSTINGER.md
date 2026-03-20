# Comprehensive Django Deployment Guide for Hostinger VPS (Ubuntu 22.04/24.04)

This guide provides a step-by-step walkthrough to deploy the **TJ Naturals** Django project on a Hostinger VPS using Nginx, Gunicorn, and PostgreSQL.

---

## 🏗️ Phase 1: Local Preparation (Do this on your PC)

### 1. Prepare `requirements.txt`
Ensure all production packages are listed.
```powershell
pip install gunicorn psycopg2-binary
pip freeze > requirements.txt
```

### 2. Export Local Data (Optional but Recommended)
If you want to keep your current users and products:
```powershell
python manage.py dumpdata --exclude auth.permission --exclude contenttypes --indent 2 > datadump.json
```

### 3. Push Code to GitHub
The easiest way to move code to the VPS is via GitHub.
1. Create a repository on GitHub (e.g., `tj-naturals`).
2. Run these commands in your project folder:
   ```bash
   git init
   git add .
   git commit -m "Prepare for deployment"
   git branch -M main
   # Replace YOUR_USERNAME with your actual GitHub username
   git remote add origin https://github.com/YOUR_USERNAME/tj-naturals.git
   git push -u origin main
   ```
   *(Note: Ensure `.env` and `db.sqlite3` are in your `.gitignore` file so they aren't uploaded).*

---

## 🚀 Phase 2: Server Setup (Connect to VPS)

### 1. Connect via SSH
Use PowerShell (Windows) or Terminal (Mac/Linux). Hostinger provides your IP and root password in the dashboard.
```bash
ssh root@YOUR_VPS_IP
```
*Type `yes` if asked about fingerprints, then enter your password.*

### 2. Update System Packages
Once logged in, run:
```bash
sudo apt update
sudo apt upgrade -y
```

### 3. Install Required Software
Install Python, PostgreSQL, Nginx, and Git.
```bash
sudo apt install python3-pip python3-dev libpq-dev postgresql postgresql-contrib nginx curl git build-essential -y
```

---

## 🗄️ Phase 3: Database Setup (PostgreSQL)

### 1. Access PostgreSQL Console
```bash
sudo -u postgres psql
```

### 2. Create Database and User
Replace `'strong_password'` with a real secure password.
```sql
CREATE DATABASE tjnaturals_db;
CREATE USER tjnaturals_user WITH PASSWORD 'strong_password';
ALTER ROLE tjnaturals_user SET client_encoding TO 'utf8';
ALTER ROLE tjnaturals_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE tjnaturals_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE tjnaturals_db TO tjnaturals_user;
\q
```

---

## 📂 Phase 4: Project Setup

### 1. Clone the Repository
Go to the `www` directory (standard for web apps).
```bash
cd /var/www
# Replace with your actual repo URL
sudo git clone https://github.com/YOUR_USERNAME/tj-naturals.git tjnaturals
cd tjnaturals
```

### 2. Create Virtual Environment
```bash
sudo apt install python3-venv -y
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create the `.env` file on the server.
```bash
nano .env
```
Paste this content (Right-click to paste in PuTTY/Terminal):
```ini
DEBUG=False
SECRET_KEY=generate_a_new_random_secret_here
ALLOWED_HOSTS=YOUR_DOMAIN.COM,WWW.YOUR_DOMAIN.COM,YOUR_VPS_IP

# Database Config - Update if needed
DB_NAME=tjnaturals_db
DB_USER=tjnaturals_user
DB_PASSWORD=strong_password
DB_HOST=localhost
DB_PORT=5432

# Email Config (Use the same as local)
EMAIL_HOST_USER=your_real_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
EMAIL_USE_TLS=True
EMAIL_PORT=587
EMAIL_HOST=smtp.gmail.com
```
*Press `Ctrl+X`, then `Y`, then `Enter` to save.*

### 5. Run Migrations & Collect Static
```bash
python manage.py collectstatic --noinput
python manage.py migrate
```

### 6. Import Data (Optional)
If you exported `datadump.json`:
1. Upload it to the server (you can use `scp` or `FileZilla`).
2. Run: `python manage.py loaddata datadump.json`

---

## ⚡ Phase 5: Gunicorn Setup (The Application Server)

### 1. Test Gunicorn Manually
```bash
gunicorn --bind 0.0.0.0:8000 TJNaturals.wsgi
```
*Visit `http://YOUR_VPS_IP:8000` in your browser. If the site loads (without styles), it works exactly as expected. Press `Ctrl+C` to stop.*

### 2. Create Systemd Socket
This creates a communication pipe for Nginx.
```bash
sudo nano /etc/systemd/system/gunicorn.socket
```
Paste:
```ini
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```

### 3. Create Systemd Service
This keeps your site running in the background.
```bash
sudo nano /etc/systemd/system/gunicorn.service
```
Paste (Update paths if different):
```ini
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/tjnaturals
ExecStart=/var/www/tjnaturals/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          TJNaturals.wsgi:application

[Install]
WantedBy=multi-user.target
```

### 4. Start Gunicorn
```bash
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
```

---

## 🌐 Phase 6: Nginx Setup (The Web Server)

### 1. Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/tjnaturals
```
Paste (Replace `your_domain.com` with your actual domain):
```nginx
server {
    listen 80;
    server_name your_domain.com www.your_domain.com YOUR_VPS_IP;

    location = /favicon.ico { access_log off; log_not_found off; }

    # Static Files
    location /static/ {
        alias /var/www/tjnaturals/static/;
    }

    # Media Files (Images)
    location /media/ {
        alias /var/www/tjnaturals/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```

### 2. Enable Site & Restart Nginx
```bash
sudo ln -s /etc/nginx/sites-available/tjnaturals /etc/nginx/sites-enabled
sudo nginx -t  # Should say "syntax is ok"
sudo systemctl restart nginx
```

### 3. Allow Traffic through Firewall
```bash
sudo ufw allow 'Nginx Full'
```

---

## 🔒 Phase 7: SSL Certificate (HTTPS)

Secure your site with a free Let's Encrypt certificate.

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your_domain.com -d www.your_domain.com
```
*Follow the prompts (enter email, agree to terms). Select "2" to redirect HTTP to HTTPS.*

---

## ✅ Post-Deployment Checks

1. Visit `https://your_domain.com`.
2. Test **Login**, **Cart**, and **Checkout**.
3. Test **Password Reset** (to ensure Email settings are correct).
4. If images are missing, ensure `media/` folder permissions:
   ```bash
   sudo chown -R www-data:www-data /var/www/tjnaturals/media
   sudo chmod -R 775 /var/www/tjnaturals/media
   ```
