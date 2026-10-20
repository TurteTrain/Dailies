# Hourly Spotify polling deployment

These instructions deploy the Django backend to Ubuntu 24.04 at
`/opt/dailies`. The systemd timer runs `poll_spotify` once per hour and sends
its output and errors to journald.

## 1. Install system packages

```bash
sudo apt update
sudo apt install -y git python3 python3-venv postgresql postgresql-contrib
```

## 2. Clone the repository

```bash
sudo git clone <repo-url> /opt/dailies
sudo chown -R "$USER":"$USER" /opt/dailies
cd /opt/dailies
```

Check out the branch or commit that should run in production:

```bash
git checkout <branch-or-commit>
```

## 3. Create the virtual environment

```bash
cd /opt/dailies
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
deactivate
```

## 4. Create the PostgreSQL database and user

Choose a strong password and use the same values in the `.env` file below:

```bash
sudo -u postgres psql
```

```sql
CREATE USER dailies WITH PASSWORD 'replace-with-a-strong-password';
CREATE DATABASE dailies OWNER dailies;
\q
```

If the user or database already exists, use `ALTER USER` or skip the
corresponding `CREATE` statement.

## 5. Create the environment file

```bash
cp /opt/dailies/backend/.env.example /opt/dailies/backend/.env
chmod 600 /opt/dailies/backend/.env
nano /opt/dailies/backend/.env
```

Set at least these production values:

```dotenv
DJANGO_SECRET_KEY=<unique-random-secret>
DEBUG=False
ALLOWED_HOSTS=<server-hostname-or-ip>
DB_NAME=dailies
DB_USER=dailies
DB_PASSWORD=<the-postgres-password>
DB_HOST=127.0.0.1
DB_PORT=5432
SPOTIFY_CLIENT_ID=<spotify-client-id>
SPOTIFY_CLIENT_SECRET=<spotify-client-secret>
SPOTIFY_REDIRECT_URI=<the-redirect-uri-configured-in-spotify>
```

```bash
/opt/dailies/venv/bin/python -c \
  "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 6. Run migrations

```bash
cd /opt/dailies/backend
/opt/dailies/venv/bin/python manage.py migrate
```

## 7. Install and enable the hourly timer

```bash
sudo install -m 0644 /opt/dailies/deploy/poll_spotify.service \
  /etc/systemd/system/poll_spotify.service
sudo install -m 0644 /opt/dailies/deploy/poll_spotify.timer \
  /etc/systemd/system/poll_spotify.timer
sudo systemctl daemon-reload
sudo systemctl enable --now poll_spotify.timer
```

Confirm that the timer is scheduled:

```bash
systemctl status poll_spotify.timer
systemctl list-timers poll_spotify.timer
```

Run the service immediately once to verify the configuration:

```bash
sudo systemctl start poll_spotify.service
```

## 8. Check logs

Show the latest polling run:

```bash
sudo journalctl -u poll_spotify.service -n 100 --no-pager
```

Follow new output:

```bash
sudo journalctl -u poll_spotify.service -f
```

The timer does not run the service concurrently: each hourly trigger starts
the oneshot service, and systemd waits for that run to finish.
