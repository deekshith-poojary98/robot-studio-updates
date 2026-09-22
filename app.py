"""Robot Studio update feed — thin proxy over GitHub Releases.

Deploy separately from the desktop app. Intended to move to its own repo later.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "deekshith-poojary98")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "robot-studio")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "300"))
CHANNEL_DEFAULT = os.environ.get("CHANNEL_DEFAULT", "stable")

app = FastAPI(
    title="Robot Studio Updates",
    version="0.1.0",
    description="GET /v1/latest — latest Robot Studio release metadata.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache: dict[str, Any] = {"fetched_at": 0.0, "releases": []}


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "robot-studio-updates",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _parse_semver(tag: str) -> tuple[int, int, int, int] | None:
    """Parse v1.1.0 or 1.1.0(+build) → (major, minor, patch, build)."""
    raw = tag.strip()
    if raw.startswith("v") or raw.startswith("V"):
        raw = raw[1:]
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:\+(\d+))?", raw)
    if not match:
        return None
    major, minor, patch, build = match.groups()
    return int(major), int(minor), int(patch), int(build or 0)


def _is_prerelease_channel(channel: str) -> bool:
    return channel.lower() in {"beta", "pre", "prerelease", "all"}


async def _load_releases(*, force: bool = False) -> list[dict[str, Any]]:
    now = time.monotonic()
    if (
        not force
        and _cache["releases"]
        and (now - float(_cache["fetched_at"])) < CACHE_TTL_SECONDS
    ):
        return list(_cache["releases"])

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, headers=_github_headers(), params={"per_page": 20})
    if response.status_code == 404:
        raise HTTPException(status_code=502, detail="GitHub repository not found")
    if response.status_code == 403:
        raise HTTPException(
            status_code=502,
            detail="GitHub rate-limited or forbidden (set GITHUB_TOKEN)",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub releases failed: HTTP {response.status_code}",
        )

    releases = response.json()
    if not isinstance(releases, list):
        raise HTTPException(status_code=502, detail="Unexpected GitHub response")

    _cache["releases"] = releases
    _cache["fetched_at"] = now
    return releases


def _pick_asset(
    assets: list[dict[str, Any]],
    *,
    os_name: str | None,
    arch: str | None,
) -> dict[str, Any] | None:
    if not assets:
        return None
    if not os_name:
        return assets[0]

    os_key = os_name.lower()
    arch_key = (arch or "").lower()
    names = [(a, (a.get("name") or "").lower()) for a in assets]

    def score(name: str) -> int:
        points = 0
        if os_key in name:
            points += 10
        if arch_key and arch_key in name:
            points += 5
        # Prefer zip packages from package-desktop.yml naming.
        if name.endswith(".zip"):
            points += 2
        return points

    ranked = sorted(names, key=lambda item: score(item[1]), reverse=True)
    best, best_name = ranked[0]
    if score(best_name) < 10:
        return None
    return best


def _release_to_payload(
    release: dict[str, Any],
    *,
    os_name: str | None,
    arch: str | None,
    channel: str,
) -> dict[str, Any]:
    tag = str(release.get("tag_name") or "")
    parsed = _parse_semver(tag)
    version = tag.lstrip("vV") if tag else ""
    build = parsed[3] if parsed else 0
    if "+" in version:
        version = version.split("+", 1)[0]

    asset = _pick_asset(list(release.get("assets") or []), os_name=os_name, arch=arch)
    download_url = None
    asset_name = None
    if asset:
        download_url = asset.get("browser_download_url")
        asset_name = asset.get("name")

    return {
        "version": version,
        "build": build,
        "tag": tag,
        "channel": channel,
        "released_at": release.get("published_at") or release.get("created_at"),
        "notes_url": release.get("html_url"),
        "download_url": download_url,
        "asset_name": asset_name,
        "mandatory": False,
        "source": f"github:{GITHUB_OWNER}/{GITHUB_REPO}",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/latest")
async def latest(
    os: str | None = Query(
        default=None,
        description="Client OS: macos | windows | linux",
        pattern="^(macos|windows|linux)$",
    ),
    arch: str | None = Query(
        default=None,
        description="Optional CPU arch hint: x64 | arm64",
        pattern="^(x64|arm64|amd64|aarch64)$",
    ),
    channel: str = Query(
        default=CHANNEL_DEFAULT,
        description="stable (non-prerelease) or beta (include prereleases)",
    ),
) -> dict[str, Any]:
    """Return the newest matching Robot Studio release."""
    arch_norm = arch
    if arch_norm == "amd64":
        arch_norm = "x64"
    if arch_norm == "aarch64":
        arch_norm = "arm64"

    releases = await _load_releases()
    allow_pre = _is_prerelease_channel(channel)

    candidates: list[dict[str, Any]] = []
    for release in releases:
        if release.get("draft"):
            continue
        if release.get("prerelease") and not allow_pre:
            continue
        tag = str(release.get("tag_name") or "")
        if _parse_semver(tag) is None:
            continue
        candidates.append(release)

    if not candidates:
        raise HTTPException(status_code=404, detail="No matching releases found")

    candidates.sort(
        key=lambda item: _parse_semver(str(item.get("tag_name") or "")) or (0, 0, 0, 0),
        reverse=True,
    )
    newest = candidates[0]
    return _release_to_payload(
        newest,
        os_name=os,
        arch=arch_norm,
        channel="beta" if allow_pre else "stable",
    )
