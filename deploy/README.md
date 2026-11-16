# Hourly Spotify polling deployment

These instructions deploy the Django backend to Ubuntu 24.04 at
`/home/ubuntu/Dailies`. The systemd timer runs `poll_spotify` once per hour and sends
its output and errors to journald.

## 1. Install system packages

```bash
sudo apt update
sudo apt install -y git python3 python3-venv postgresql postgresql-contrib
```

## 2. Clone the repository

```bash
git clone <repo-url> /home/ubuntu/Dailies
cd /home/ubuntu/Dailies
```

Check out the branch or commit that should run in production:

```bash
git checkout <branch-or-commit>
```

## 3. Create the virtual environment

```bash
cd /home/ubuntu/Dailies
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r backend/requirements-ml.txt
deactivate
```

`requirements-ml.txt` is for the AI mood model (`backend/dailies/mood.py`). It
installs only `onnxruntime`, `tokenizers` and `numpy` (no torch). The model
files are already in the repo at `backend/dailies/mood_model/`. Without these
packages the poller still runs. It just prints
`mood: model not installed, skipping` and leaves moods empty.

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
cp /home/ubuntu/Dailies/backend/.env.example /home/ubuntu/Dailies/backend/.env
chmod 600 /home/ubuntu/Dailies/backend/.env
nano /home/ubuntu/Dailies/backend/.env
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
LASTFM_API_KEY=<lastfm-api-key>
```

Django reads this file itself (python-dotenv). Don't `source` it in bash: the
secret key can contain characters like `&`, `$` and `(` that break the shell.

```bash
/home/ubuntu/Dailies/venv/bin/python -c \
  "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 6. Run migrations

```bash
cd /home/ubuntu/Dailies/backend
/home/ubuntu/Dailies/venv/bin/python manage.py migrate
```

## 7. Install and enable the hourly timer

```bash
sudo install -m 0644 /home/ubuntu/Dailies/deploy/poll_spotify.service \
  /etc/systemd/system/poll_spotify.service
sudo install -m 0644 /home/ubuntu/Dailies/deploy/poll_spotify.timer \
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

## 9. Update the server after a merge

```bash
cd /home/ubuntu/Dailies
git pull --ff-only origin master
venv/bin/pip install -r backend/requirements.txt -r backend/requirements-ml.txt
cd backend && ../venv/bin/python manage.py migrate
sudo systemctl start poll_spotify.service   # optional: run once now instead of waiting for the hour
```

Each run tags the mood of up to 100 new tracks and uses about 115 MB of RAM.
If many tracks are waiting (for example right after the model is first
installed), run the service a few times to catch up. The log line
`mood: tagged N tracks` shows the progress.
