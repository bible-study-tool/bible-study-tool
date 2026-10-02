"""Application Version Update Checker & GitHub Releases Client (WP-044, ADR-023).

Provides zero-telemetry, lightweight version checking against public GitHub Releases.
In accordance with ADR-023 and the project charter:
- ZERO TELEMETRY: Only queries the public GitHub release tag. Absolutely no identifiers,
  IP logging, search queries, study preferences, or personal telemetry are transmitted.
- 100% OFFLINE-SAFE: Network timeouts, DNS failures, or offline environments degrade
  silently and gracefully without user interruption or modal errors.
- IN-MEMORY THROTTLING: In-memory cache protects against GitHub API rate limits.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from search.resource import __version__

logger = logging.getLogger(__name__)

GITHUB_API_LATEST_RELEASE = "https://api.github.com/repos/bible-study-tool/bible-study-tool/releases/latest"
GITHUB_RELEASES_WEB_URL = "https://github.com/bible-study-tool/bible-study-tool/releases"

# Default cache TTL: 1 hour (3600 seconds)
DEFAULT_CACHE_TTL_SECONDS = 3600.0


def parse_semver(version_str: str) -> tuple[int, int, int]:
    """Parse a semantic version string into a comparable (major, minor, patch) integer tuple.

    Examples:
        '0.1.6'         -> (0, 1, 6)
        'v0.1.7'        -> (0, 1, 7)
        'v1.2.3-beta.1' -> (1, 2, 3)
        '2.0'           -> (2, 0, 0)
        'invalid'       -> (0, 0, 0)
    """
    clean = (version_str or "").strip().lstrip("vV").strip()
    if not clean:
        return (0, 0, 0)

    # Strip pre-release (-beta) or build (+build) metadata
    base = clean.split("-")[0].split("+")[0]
    parts: list[int] = []
    for p in base.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break

    while len(parts) < 3:
        parts.append(0)

    return (parts[0], parts[1], parts[2])


def is_newer_version(current_version: str, candidate_version: str) -> bool:
    """Return True if candidate_version is strictly greater than current_version."""
    cur = parse_semver(current_version)
    cand = parse_semver(candidate_version)
    return cand > cur


class VersionChecker:
    """Zero-telemetry GitHub Releases client with caching and offline resilience."""

    def __init__(
        self,
        api_url: str = GITHUB_API_LATEST_RELEASE,
        releases_url: str = GITHUB_RELEASES_WEB_URL,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
    ):
        self.api_url = api_url
        self.releases_url = releases_url
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cached_result: Optional[dict[str, Any]] = None
        self._cache_timestamp: float = 0.0

    def clear_cache(self) -> None:
        """Clear cached update check result."""
        self._cached_result = None
        self._cache_timestamp = 0.0

    def check_for_updates(
        self,
        current_version: str = __version__,
        force: bool = False,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        """Check for updates against the GitHub Releases API.

        Args:
            current_version: The currently installed application version.
            force: If True, bypass the in-memory cache and fetch live.
            timeout: Network socket timeout in seconds.

        Returns:
            Dictionary containing update status, latest tag, download URLs, and release notes.
        """
        now = time.time()
        if not force and self._cached_result is not None:
            if (now - self._cache_timestamp) < self.cache_ttl_seconds:
                cached = dict(self._cached_result)
                cached["cached"] = True
                return cached

        req = urllib.request.Request(
            self.api_url,
            headers={
                "User-Agent": f"BibleStudyTool/{current_version} (Zero-Telemetry; Open-Source)",
                "Accept": "application/vnd.github.v3+json",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    result = {
                        "status": "error",
                        "current_version": current_version,
                        "latest_version": None,
                        "update_available": False,
                        "release_name": None,
                        "release_notes_url": self.releases_url,
                        "download_url": self.releases_url,
                        "published_at": None,
                        "body": None,
                        "cached": False,
                        "error": f"HTTP status {response.status}",
                    }
                    return result

                raw_data = response.read()
                data = json.loads(raw_data.decode("utf-8"))

            tag_name = data.get("tag_name", "").strip()
            release_name = data.get("name") or tag_name
            html_url = data.get("html_url") or self.releases_url
            published_at = data.get("published_at")
            body = data.get("body", "")

            # Identify candidate download asset or release page
            download_url = html_url
            assets = data.get("assets", [])
            if assets and isinstance(assets, list):
                # If specific download asset exists, prefer direct link or keep html_url
                for asset in assets:
                    if isinstance(asset, dict) and asset.get("browser_download_url"):
                        download_url = str(asset["browser_download_url"])
                        break

            update_available = is_newer_version(current_version, tag_name)

            result = {
                "status": "ok",
                "current_version": current_version,
                "latest_version": tag_name,
                "update_available": update_available,
                "release_name": release_name,
                "release_notes_url": html_url,
                "download_url": download_url,
                "published_at": published_at,
                "body": (body[:1000] + "...") if len(body) > 1000 else body,
                "cached": False,
                "error": None,
            }

            self._cached_result = result
            self._cache_timestamp = now
            return result

        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as exc:
            logger.debug(f"Version update check failed gracefully (offline/unreachable): {exc}")
            # Graceful offline response
            return {
                "status": "offline",
                "current_version": current_version,
                "latest_version": None,
                "update_available": False,
                "release_name": None,
                "release_notes_url": self.releases_url,
                "download_url": self.releases_url,
                "published_at": None,
                "body": None,
                "cached": False,
                "error": str(exc),
            }
        except Exception as exc:
            logger.warning(f"Unexpected error in version check: {exc}")
            return {
                "status": "error",
                "current_version": current_version,
                "latest_version": None,
                "update_available": False,
                "release_name": None,
                "release_notes_url": self.releases_url,
                "download_url": self.releases_url,
                "published_at": None,
                "body": None,
                "cached": False,
                "error": str(exc),
            }


# Singleton instance for server runtime
default_version_checker = VersionChecker()
