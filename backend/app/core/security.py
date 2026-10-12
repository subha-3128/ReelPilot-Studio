import ipaddress
import re
import socket
from urllib.parse import urlparse
from fastapi import HTTPException
from pathlib import Path

# Permitted video hosting domains for Kuaishou, Kwai, and Instagram
ALLOWED_DOMAINS = {
    "kuaishou.com",
    "www.kuaishou.com",
    "v.kuaishou.com",
    "kwai.com",
    "www.kwai.com",
    "kwai-video.com",
    "m.kwai.com",
    "gifshow.com",
    "v.m.chenzhongtech.com",
    "instagram.com",
    "www.instagram.com",
    "instagr.am",
    "www.instagr.am",
    "m.instagram.com",
}

def sanitize_filename(name: str) -> str:
    """Strip dangerous directory separators and non-alphanumeric characters."""
    base_name = Path(name).name
    clean = re.sub(r"[^\w\-.]", "_", base_name)
    return clean.strip(" .") or "unnamed_asset"

def validate_and_normalize_url(url: str) -> str:
    """
    Validate URL format, scheme, host allowlist, and guard against SSRF.
    Ensures URL doesn't resolve to private/loopback/link-local network addresses.
    """
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Video URL cannot be empty")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed.",
        )

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL: Missing hostname")

    # Domain allowlist check (exact match or subdomain)
    is_allowed = any(
        hostname == domain or hostname.endswith("." + domain)
        for domain in ALLOWED_DOMAINS
    )
    if not is_allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Domain '{hostname}' is not supported. "
                f"Supported services: Instagram Reels, Kuaishou, and Kwai links (e.g. instagram.com, v.kuaishou.com, kwai.com)."
            ),
        )

    # SSRF guard: resolve DNS and ensure not private/loopback
    try:
        ip_list = socket.getaddrinfo(hostname, None)
        for entry in ip_list:
            ip_str = entry[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                raise HTTPException(
                    status_code=400,
                    detail=f"Security alert: Domain resolves to private/restricted IP ({ip_str})",
                )
    except socket.gaierror:
        raise HTTPException(status_code=400, detail=f"Cannot resolve hostname '{hostname}'")

    return url

def safe_resolve_path(base_dir: Path, target_path_str: str) -> Path:
    """Ensure that target_path_str is strictly contained within base_dir or project storage to prevent path traversal."""
    target_path = Path(target_path_str).resolve()
    base_dir = base_dir.resolve()
    from app.core.config import settings
    default_dir = (settings.BASE_DIR / "storage").resolve()

    for allowed_root in [base_dir, default_dir]:
        try:
            target_path.relative_to(allowed_root)
            return target_path
        except ValueError:
            continue

    raise HTTPException(status_code=403, detail="Access denied: Path traversal detected")
