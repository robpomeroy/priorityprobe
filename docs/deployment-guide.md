# PrioritySuite Deployment Guide

This guide covers deployment options for PrioritySuite, ranging from lightweight local development to production deployments using Gunicorn, Nginx/Apache, and MariaDB.

---

## 1. Local Development (SQLite)

For personal standalone use or local development:

```bash
git clone https://github.com/your-org/prioritysuite.git
cd prioritysuite

python -m venv .venv
source .venv/bin/activate  # Or on Windows: .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

By default, PrioritySuite uses SQLite (`db.sqlite3` or temporary path when on network drives), requiring zero database setup.

---

## 2. Docker Compose Deployment (Gunicorn + MariaDB + Nginx)

For hosted, multi-user deployments, the repository includes a complete `docker-compose.yml` configuration:

```text
                  +--------------------------------+
                  |         Client Browser         |
                  +--------------------------------+
                                  |
                                  | HTTPS (Port 443) / HTTP (Port 80 Redirect)
                                  v
                  +--------------------------------+
                  |       Nginx TLS Reverse Proxy  |
                  +--------------------------------+
                                  |
                 +----------------+----------------+
                 |                                 |
                 | Static Files                    | WSGI Proxy
                 v                                 v
    +-------------------------+       +-------------------------+
    |      Static Volume      |       |  PrioritySuite Gunicorn |
    |      (/app/staticfiles) |       |       (Port 8000)       |
    +-------------------------+       +-------------------------+
                                                   |
                                                   | MySQL Protocol
                                                   v
                                      +-------------------------+
                                      |     MariaDB 11.4 DB     |
                                      |       (Port 3306)       |
                                      +-------------------------+
```

### Steps to Run:

1. Copy `.env.example` to `.env` and configure your production secret key and passwords:
   ```bash
   cp .env.example .env
   # Edit .env and set DJANGO_SECRET_KEY, ALLOWED_HOSTS, DB_PASSWORD, etc.
   # Optionally set OLLAMA_ALLOWED_HOSTS (e.g. "ollama,host.docker.internal") to permit specific Ollama endpoints
   ```

2. Generate or place your TLS certificates in `./certs/`:
   ```bash
   mkdir -p certs
   # For production, place fullchain.pem and privkey.pem in certs/
   # For local testing, generate self-signed certs:
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout certs/privkey.pem -out certs/fullchain.pem -subj "/CN=localhost"
   ```

2. Build and start containers in the background:
   ```bash
   docker compose up -d --build
   ```

3. Run migrations and create initial administrator inside the container:
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```

4. Access PrioritySuite at `http://your-server-ip/` or your configured domain.

---

## 3. Automated Provisioning with Ansible (Oracle Linux / RHEL 9 + Apache)

For production deployments on RHEL-family distributions (such as **Oracle Linux 9**, **AlmaLinux 9**, or **Rocky Linux 9**), automated Ansible playbooks are located in `ansible/`:

### Prerequisites on Control Machine
```bash
pip install ansible
ansible-galaxy collection install ansible.posix community.general community.mysql
```

### Full Provisioning & Deployment
```bash
cd ansible
cp inventory.example.ini inventory.ini
cp group_vars/all.example.yml group_vars/all.yml

# Edit inventory.ini and group_vars/all.yml with your server details and passwords
ansible-playbook -i inventory.ini site.yml
```

This provisions:
- **Apache (`httpd`)** with `mod_ssl` and `mod_proxy` acting as the reverse proxy (with SELinux `httpd_can_network_connect` enabled).
- **Gunicorn** managed by `systemd`.
- **MariaDB** configured with database, user, and security hardening.
- **Firewalld** configured for HTTP (80) and HTTPS (443).
- Automatic TLS certificate handling.

### Fast Application Updates
When deploying new code or database migrations:
```bash
ansible-playbook -i inventory.ini deploy.yml
```

---

## 4. Traditional Server Deployment Reference

If deploying to a dedicated Linux server (Ubuntu 22.04/24.04 or AlmaLinux 9/RHEL 9) without Docker:

### 3.1 Install System Dependencies & MariaDB
```bash
sudo apt update && sudo apt install -y python3-venv python3-dev libmariadb-dev-compat gcc nginx
# Or on AlmaLinux/RHEL:
# sudo dnf install -y python3-devel mariadb-devel gcc nginx
```

### 3.2 Configure MariaDB Database
```sql
CREATE DATABASE prioritysuite CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'prioritysuite'@'localhost' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON prioritysuite.* TO 'prioritysuite'@'localhost';
FLUSH PRIVILEGES;
```

### 3.3 Set Up Application & Virtual Environment
```bash
sudo mkdir -p /var/www/prioritysuite
sudo chown -R $USER:$USER /var/www/prioritysuite
git clone https://github.com/your-org/prioritysuite.git /var/www/prioritysuite
cd /var/www/prioritysuite

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt mysqlclient gunicorn

# Collect static assets
python manage.py collectstatic --noinput
python manage.py migrate
```

### 3.4 Configure Gunicorn Systemd Service
Create `/etc/systemd/system/prioritysuite.service`:

```ini
[Unit]
Description=PrioritySuite Gunicorn Daemon
After=network.target mariadb.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/prioritysuite
EnvironmentFile=/var/www/prioritysuite/.env
ExecStart=/var/www/prioritysuite/.venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/prioritysuite.sock \
          config.wsgi:application

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now prioritysuite
```

### 3.5 Configure Nginx Reverse Proxy
Create `/etc/nginx/sites-available/prioritysuite`:

```nginx
server {
    listen 80;
    server_name priorities.yourdomain.com;

    client_max_body_size 20M;

    location /static/ {
        alias /var/www/prioritysuite/staticfiles/;
        expires 30d;
    }

    location / {
        proxy_pass http://unix:/run/prioritysuite.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/prioritysuite /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

*(For Apache with `mod_proxy` and `mod_wsgi`, see standard Apache reverse proxy configuration using `ProxyPass / unix:/run/priorityprobe.sock|http://localhost/`)*.
