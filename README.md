# FastAPI Blog

A self-hosted personal blog built with FastAPI, Vue 3, and SQLite. Write, publish, and manage your content from a browser, then deploy the entire application as a single Docker service.

Originally built for **无情老小儿** · [Live site](https://xionzhi.com/)

## Features

- Markdown and HTML editor with previews, drafts, posts, and standalone pages.
- Tags, content search, archives, RSS, and a sitemap.
- Image uploads, code highlighting, and an image lightbox.
- Image library with search, reusable editor selections, safe path changes, and usage-aware deletion.
- Customizable site information, navigation, and cover images.
- Anonymous traffic analytics and optional SMTP password recovery.
- Native JSON import and export with conflict checks and image integrity verification.

The interface is in English. Article content can use any language. A fresh installation starts with an empty database and no default administrator account.

## Quick start

Requires **Python 3.12** and **Node.js 22** with npm.

```bash
git clone https://github.com/xionzhi/fastapi_blog.git
cd fastapi_blog
```

### 1. Set up the backend

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.lock.txt
cp .env.example .env
export PYTHONPATH=backend

python -m app.cli create-admin --username admin
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

<details>
<summary>Windows PowerShell</summary>

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
Copy-Item .env.example .env
$env:PYTHONPATH = 'backend'

.\.venv\Scripts\python.exe -m app.cli create-admin --username admin
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

</details>

The administrator command prompts for a password of at least 12 characters. The database is initialized automatically, and Alembic migrations run at startup.

### 2. Start the frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

| Page              | URL                                   |
| ----------------- | ------------------------------------- |
| Blog              | http://127.0.0.1:5173/                |
| Admin workspace   | http://127.0.0.1:5173/workspace/login |
| API documentation | http://127.0.0.1:8000/docs            |

Vite proxies API and image requests to the backend. Development does not require a production build. Local data lives in `data/dev/` and is excluded from Git.

## Docker deployment

Production targets a **single Linux host** with Docker Compose and an HTTPS reverse proxy. The container serves the frontend, API, and uploaded images; Python and Node.js are only needed inside the build.

### 1. Configure the application

From the repository root on your server:

```bash
cp .env.production.example .env
chmod 0600 .env
mkdir -p data/production/images
sudo chown -R 10001:10001 data/production
sudo chmod 0700 data/production
```

Edit `.env` with your domain:

```dotenv
BLOG_URL=https://blog.example.com
BLOG_ALLOWED_ORIGINS=https://blog.example.com
BLOG_SECURE_COOKIES=true
```

Set `BLOG_TRUSTED_PROXY_NETWORKS` to the verified source address of your reverse proxy. For host Nginx forwarding into Docker, this is typically the Docker bridge gateway with a `/32` prefix. Forwarded headers are ignored when this setting is empty, causing visitors behind the proxy to share one rate limit. Do not trust all addresses with `0.0.0.0/0` or `::/0`.

### 2. Build and start

```bash
docker compose config --quiet
docker compose build --pull
docker compose run --rm --no-deps blog python -m app.cli create-admin --username admin
docker compose up -d --wait
curl --fail http://127.0.0.1:8000/api/health
```

The container runs as UID/GID `10001` and persists data in `data/production/`. Port `8000` is bound to localhost only.

### 3. Enable HTTPS

Use [deploy/nginx.conf.example](deploy/nginx.conf.example) as a starting point. Replace `xxx.com`, configure your certificate paths, and proxy requests to `127.0.0.1:8000`. The example belongs in Nginx's `http` context; its `http2 on` directive requires Nginx 1.25.1 or newer.

```bash
sudo nginx -t
sudo systemctl reload nginx
curl --fail https://blog.example.com/api/health
```

Production requires HTTPS and secure session cookies. Interactive API documentation is disabled in production. A log rotation example is available in [deploy/logrotate.conf](deploy/logrotate.conf).

## Configuration

Use [.env.example](.env.example) for development and [.env.production.example](.env.production.example) for deployment. Keep `.env` outside version control.

- **Email:** SMTP delivery is disabled by default. Configure `BLOG_SMTP_*` and `BLOG_MAIL_FROM`, then bind a recovery address in **Settings → Administrator email**. Only encrypted SMTP (`starttls` or `ssl`) is supported.
- **Analytics:** Built-in anonymous analytics are enabled by default, with 90-day retention. Set `BLOG_ANALYTICS_ENABLED=false` to disable them.
- **Changes:** After editing production environment variables, run `docker compose up -d --wait` to recreate the container with the new configuration.

## Content and backups

Use **Images** in the workspace to browse existing files, upload images, copy URLs or Markdown, and rename or move files within the image directory. Path changes update saved article and site references; affected articles receive a new version so stale editor tabs cannot overwrite the update. External links and unsaved edits are not rewritten. Deletion is blocked while saved content uses an image. Images remain regular files in the existing data directory; no separate asset database is required.

The editor's **Image library** inserts a selected image at the cursor in Markdown or HTML. The same picker is available for article covers, the home cover, logo, and author image.

Use **Settings → Export and import data** to transfer content in the project's native JSON format. Exports include drafts and site settings; administrator accounts, sessions, analytics, SMTP credentials, and deployment configuration are excluded. JSON files are limited to 16 MB. Copy image files separately and review the import preview before applying changes.

To back up a running production database:

```bash
docker compose exec blog python -m app.cli backup /app/data/backup-001.sqlite3
```

Use a new backup filename each time, and back up `data/production/images/` separately. The backup command creates a consistent SQLite snapshot; copying only the live database file can miss pending WAL data. Full database backups include administrator credentials, so store them securely.

Avatars use automatically generated WebP thumbnails. Cover images and logos are served from their original files without resizing or re-encoding. The disposable `data/production/image-cache/` directory is regenerated on demand and does not need to be backed up or transferred.

Ordinary image URLs are cached for seven days. UUID uploads and versioned thumbnails use a one-year immutable cache. Use a new filename when replacing an image so visitors receive the update immediately.

To reset an administrator password from the server console:

```bash
docker compose exec blog python -m app.cli create-admin --username admin --reset-password
```

## Development

With the Python virtual environment active, install development dependencies and run checks from the repository root:

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest -q
ruff check backend
ruff format --check backend
```

On Windows, use `.\.venv\Scripts\python.exe` and `.\.venv\Scripts\ruff.exe` if the environment is not activated.

```bash
cd frontend
npm run format:check
```

For a manual production frontend build, run `npm run build` from `frontend/`. Docker performs this step during image creation. See [AGENTS.md](AGENTS.md) for project conventions.

## Acknowledgments

The public theme builds on Casper. Bundled theme and font license notices are included in [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES/).
