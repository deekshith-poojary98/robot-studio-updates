# Robot Studio Updates

Tiny FastAPI middleman that exposes the latest Robot Studio release to the desktop app.

All configuration comes from environment variables — nothing is hardcoded.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness |
| `GET` | `/v1/latest` | Latest release metadata |

### `GET /v1/latest`

Query params (all optional):

| Param | Values | Notes |
|-------|--------|--------|
| `os` | `macos` \| `windows` \| `linux` | Picks a matching release asset |
| `arch` | `x64` \| `arm64` | Helps disambiguate Linux zips |
| `channel` | e.g. `stable` \| `beta` | Defaults to `CHANNEL_DEFAULT` |

Example:

```bash
curl 'https://robot-studio-updates.onrender.com/v1/latest?os=macos'
```

## Environment (required)

| Variable | Required | Purpose |
|----------|----------|---------|
| `GITHUB_OWNER` | yes | Release repo owner |
| `GITHUB_REPO` | yes | Release repo name |
| `CACHE_TTL_SECONDS` | yes | In-memory cache for GitHub Releases (e.g. `300`) |
| `CHANNEL_DEFAULT` | yes | Default channel when query omits it (e.g. `stable`) |
| `GITHUB_TOKEN` | no | Raises GitHub API rate limits / needed for private repos |

## Run locally

```bash
cd robot-studio-updates
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export GITHUB_OWNER=deekshith-poojary98
export GITHUB_REPO=robot-studio
export CACHE_TTL_SECONDS=300
export CHANNEL_DEFAULT=stable
# export GITHUB_TOKEN=ghp_...   # optional

uvicorn app:app --host 127.0.0.1 --port 8090 --reload
```

## Deploy (Render)

**Start Command:**

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

Set the same env vars in the Render dashboard. Point Robot Studio at the public URL with:

```bash
--dart-define=ROBOT_STUDIO_UPDATE_URL=https://robot-studio-updates.onrender.com
```

## Out of scope (on purpose)

- Auto-download / installer patching
- Auth for clients
- Multi-product feeds
- Persistent DB
