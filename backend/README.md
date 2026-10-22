# Dailies

A website that collects users' Spotify listening history and turns it into a daily rewind.

- **Backend:** Django + PostgreSQL (`backend/`)
- **Frontend:** React (`frontend/`)
- **Data source:** Spotify Web API (Authorization Code flow, `user-read-recently-played` scope)

Spotify's "recently played" endpoint only returns the last 50 tracks, so the backend runs a polling command that saves new listens into the database. Run it regularly to build up history.

## Repository layout

```
Dailies/
├── .gitignore
├── README.md
├── frontend/                  # React app
└── backend/
    ├── manage.py
    ├── requirements.txt
    ├── .env.example           # copy to .env and fill in
    ├── config/                # Django settings and root URLs
    └── dailies/               # main Django app
        ├── models.py          # SpotifyUser, Track, Listen
        ├── views.py           # /login and /callback (Spotify OAuth)
        ├── spotify.py         # Spotify API helper functions
        ├── admin.py
        └── management/commands/poll_spotify.py
```

## Backend setup

### Prerequisites

- Git
- Python 3.10+ and the venv module (Ubuntu: `sudo apt install python3-venv`)
- PostgreSQL
- A Spotify account

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd Dailies
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
cd backend
pip install -r requirements.txt
```

The virtual environment is required. Running `pip` outside it fails on newer Ubuntu/Debian with an "externally managed environment" error. Activate it in every new terminal with `source venv/bin/activate` from the repo root.

### 2. Create your own Spotify app

Each person registers their own Spotify app so no one has to share secrets.

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and click **Create app**.
2. Set the redirect URI to exactly `http://127.0.0.1:8000/callback`.
   - It must be `http` and `127.0.0.1`. Not `localhost`, not `https`, no trailing slash.
   - Click **Add**, then scroll down and click **Save**.
3. Copy the **Client ID** and **Client Secret** from the app's Settings.
4. Under **User Management**, add the email of your own Spotify account. Apps in development mode only allow listed users to log in.

### 3. Create a local PostgreSQL database

```bash
sudo -u postgres psql
```

```sql
CREATE USER rewind_user WITH PASSWORD 'pick-a-password';
CREATE DATABASE rewind OWNER rewind_user;
```

The user and database names must match the `DATABASES` block in `backend/config/settings.py`. Every developer uses a local database, so nobody sees anyone else's data. On macOS/Windows, install Postgres first or run it in Docker.

### 4. Create your `.env`

From `backend/`:

```bash
cp .env.example .env
```

Fill in the values:

```
DJANGO_SECRET_KEY=<generate one, see below>
DB_PASSWORD=<password from step 3>
SPOTIFY_CLIENT_ID=<from your Spotify app>
SPOTIFY_CLIENT_SECRET=<from your Spotify app>
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/callback
```

Generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Never commit `.env`.** It is gitignored. Check that `git status` does not list it.

### 5. Migrate and run the server

From `backend/` with the venv active:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 6. Collect and view your listening history

1. Open `http://127.0.0.1:8000/login` (use `127.0.0.1`, not `localhost`) and approve access. You should see "Connected!".
2. In a second terminal (venv active, inside `backend/`), run:
   ```bash
   python manage.py poll_spotify
   ```
3. Open `http://127.0.0.1:8000/admin`, log in with your superuser account, and browse **Listens** and **Tracks**.

Re-running `poll_spotify` is safe. A unique constraint skips duplicates, so each run only adds new plays.

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `externally-managed-environment` when running pip | The venv is not active. Run `source venv/bin/activate` first. |
| `KeyError: 'SPOTIFY_...'` or `'DJANGO_SECRET_KEY'` | `.env` is missing, misspelled, or not in `backend/`. Run all commands from `backend/`. |
| `.env` changes have no effect | Restart `runserver`. It does not watch `.env`. |
| "redirect_uri: Not matching configuration" on Spotify | The dashboard URI must be exactly `http://127.0.0.1:8000/callback`, and you must click **Save**. |
| 403 / "user not registered" when logging in | Your email is not under **User Management** in your Spotify app. |
| "State mismatch" after approving | You started login from `localhost`. Use `127.0.0.1`. |
| Database connection error | Postgres is not running, or the DB name, user, or password differs from `.env` / `settings.py`. |
| `ModuleNotFoundError` for an app module | Check that imports use `dailies` and that `"dailies"` is in `INSTALLED_APPS`. |

## Git workflow

- **Never commit directly to `main`.** Create a branch per task and open a pull request.
- Before starting work:
  ```bash
  git checkout main
  git pull origin main
  git checkout -b feature/short-description
  ```
- After pulling, run `python manage.py migrate` in case someone added migrations.
- Commit small and often, then push and open a PR:
  ```bash
  git add <files>
  git commit -m "Describe what the change does"
  git push -u origin feature/short-description
  ```
- Check `git status` before `git add .` to make sure `.env` and `venv/` are not included.
- Never force-push (`git push --force`) to shared branches.

### Django-specific rules

- If you change `models.py`, run `python manage.py makemigrations` and commit the migration file in the **same PR**.
- If two people create migrations at the same time, the second to merge runs `python manage.py makemigrations --merge` and commits the result.
- If you install a new package, run `pip freeze > requirements.txt` from `backend/` and commit it. Teammates then run `pip install -r requirements.txt` after pulling.

## Security notes

- Do not share secrets in the repo, chat, or screenshots. If a secret leaks, regenerate it in the Spotify dashboard (client secret) or generate a new `DJANGO_SECRET_KEY`.
- Spotify refresh tokens are stored in the database. Treat database dumps as sensitive.
- Before any public deployment, set `DEBUG=False` and configure `ALLOWED_HOSTS`.
