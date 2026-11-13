# PrioritySuite Ansible Provisioning & Deployment

This directory contains automated, idempotent Ansible playbooks and roles for provisioning and deploying PrioritySuite on **RHEL-based distributions (Oracle Linux 9, AlmaLinux 9, Rocky Linux 9, RHEL 9)** with **Apache (`httpd` + `mod_ssl` + `mod_proxy`)**, **Gunicorn**, and **MariaDB**.

---

## 1. Quick Start

### Prerequisites
On your control machine (the machine running Ansible):
```bash
pip install ansible
ansible-galaxy collection install ansible.posix community.general community.mysql
```

### Configuration
1. Copy the example inventory and configuration files:
   ```bash
   cp inventory.example.ini inventory.ini
   cp group_vars/all.example.yml group_vars/all.yml
   ```
2. Edit `inventory.ini` to set your target server's IP address and SSH credentials.
3. Edit `group_vars/all.yml` to set your domain name, database passwords, and `django_secret_key`.

---

## 2. Playbooks

### Initial Server Provisioning & Full Deployment (`site.yml`)
Provisions the entire stack from scratch:
- Installs EPEL, system dependencies, Python 3, `firewalld`, SELinux tools
- Configures `firewalld` (ports 80 & 443)
- Installs and configures MariaDB database and user
- Clones PrioritySuite, sets up virtualenv, applies migrations, runs `collectstatic`
- Configures and starts Gunicorn as a `systemd` service
- Installs Apache (`httpd`), enables SELinux `httpd_can_network_connect`, configures reverse proxy VirtualHost, and enables TLS/HTTPS

Run the full playbook:
```bash
ansible-playbook -i inventory.ini site.yml
```

### Application Code Updates (`deploy.yml`)
For subsequent updates, deploy the latest code without reprovisioning OS packages or database services:
- Pulls latest git commits
- Updates virtualenv dependencies (`pip install -r requirements.txt`)
- Runs database migrations (`python manage.py migrate`)
- Collects static assets (`python manage.py collectstatic`)
- Restarts Gunicorn daemon cleanly

Run the fast deploy playbook:
```bash
ansible-playbook -i inventory.ini deploy.yml
```

---

## 3. Architecture on Target Host

```text
               +--------------------------------------+
               |             Client Browser           |
               +--------------------------------------+
                                   |
                                   | HTTPS (Port 443) / HTTP (Port 80 Redirect)
                                   v
               +--------------------------------------+
               |     Apache (httpd + mod_proxy)       |
               +--------------------------------------+
                                   |
                  +----------------+----------------+
                  |                                 |
                  | Static Files                    | ProxyPass (127.0.0.1:8000)
                  | (/var/www/.../staticfiles)      | X-Forwarded-Proto: https
                  v                                 v
     +-------------------------+       +-------------------------+
     |   httpd_sys_content_t   |       |  PrioritySuite Gunicorn |
     |      Static Files       |       |  (systemd daemon)       |
     +-------------------------+       +-------------------------+
                                                    |
                                                    | MySQL Protocol (127.0.0.1:3306)
                                                    v
                                       +-------------------------+
                                       |     MariaDB 10.5+       |
                                       +-------------------------+
```

### Key Security & SELinux Features:
- **Dedicated System User:** PrioritySuite runs under an unprivileged `prioritysuite` system user.
- **SELinux Enforcing:** Apache is permitted to proxy upstream traffic via the persistent `httpd_can_network_connect` boolean, and static files are labeled with `httpd_sys_content_t`.
- **Firewalld:** Only HTTP (80), HTTPS (443), and SSH (22) ports are exposed. MariaDB and Gunicorn listen exclusively on loopback interfaces.
- **TLS Key Protection & Certificates:** Private keys are locked to `0600` root-only access. Production deployments require valid operator certificates (e.g. via Certbot / Let's Encrypt or corporate CA); `generate_self_signed_cert: true` is strictly intended for initial offline staging.
- **Credential Protection:** Sensitive database user creation tasks use `no_log: true` to prevent secrets exposure in Ansible output. Production passwords should be encrypted with `ansible-vault`.
- **Host Key Verification:** SSH host-key verification is enabled by default (`host_key_checking = True`) in `ansible.cfg` to prevent MITM attacks.
- **Secure Reverse Proxy Headers:** Apache injects `X-Forwarded-Proto: https`, which matches Django's `SECURE_PROXY_SSL_HEADER` so session and CSRF cookies are strictly marked `Secure`. Plaintext port 80 redirects securely to the configured domain.
