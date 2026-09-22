# Robot Studio Updates

Tiny FastAPI middleman that exposes the latest Robot Studio release to the desktop app.

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
| `channel` | `stable` (default) \| `beta` | `stable` skips GitHub prereleases |

Example:

```bash
curl 'http://127.0.0.1:8090/v1/latest?os=macos&arch=arm64'
```

```json
{
  "version": "1.1.0",
  "build": 0,
  "tag": "v1.1.0",
  "channel": "stable",
  "released_at": "2026-09-17T12:00:00Z",
  "notes_url": "https://github.com/deekshith-poojary98/robot-studio/releases/tag/v1.1.0",
  "download_url": "https://github.com/.../Robot-Studio-1.1.0-macos.zip",
  "asset_name": "Robot-Studio-1.1.0-macos.zip",
  "mandatory": false,
  "source": "github:deekshith-poojary98/robot-studio"
}
```

Desktop clients compare `version` / `build` to the running app and open `download_url` / `notes_url` when newer.

Point Robot Studio at the public host with:

```bash
--dart-define=ROBOT_STUDIO_UPDATE_URL=https://updates.example.com
```

## Run locally

```bash
cd robot-studio-updates
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8090 --reload
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `GITHUB_OWNER` | `deekshith-poojary98` | Release repo owner |
| `GITHUB_REPO` | `robot-studio` | Release repo name |
| `GITHUB_TOKEN` | _(empty)_ | Optional; raises GitHub API rate limits / needed for private repos |
| `CACHE_TTL_SECONDS` | `300` | In-memory cache for GitHub Releases |
| `CHANNEL_DEFAULT` | `stable` | Default when `channel` query is omitted |

## Deploy (sketch)

On any small VPS:

```bash
uvicorn app:app --host 0.0.0.0 --port 8090
```

Put HTTPS in front (Caddy / nginx / Cloudflare). Point Robot Studio at that public base URL.

## Out of scope (on purpose)

- Auto-download / installer patching
- Auth for clients
- Multi-product feeds
- Persistent DB
