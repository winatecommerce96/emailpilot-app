import json
import os
from pathlib import Path
from typing import Dict, List

_manifest_cache: Dict[str, dict] = {}
_manifest_mtime: float = 0.0
_BASE_DIR = Path(__file__).resolve().parents[2] if len(Path(__file__).resolve().parents) >= 2 else Path.cwd()


def _load_manifest() -> dict:
    global _manifest_cache, _manifest_mtime
    manifest_path = (_BASE_DIR / "frontend" / "dist" / ".vite" / "manifest.json").resolve()
    if not manifest_path.exists():
        return {}
    mtime = manifest_path.stat().st_mtime
    if mtime != _manifest_mtime:
        try:
            _manifest_cache = json.loads(manifest_path.read_text())
            _manifest_mtime = mtime
        except Exception:
            _manifest_cache = {}
    return _manifest_cache


def vite_assets(entry_name: str) -> str:
    """Return HTML tags for the given entry from Vite manifest.

    Emits <link rel="stylesheet"> for CSS and <script type="module"> for the JS entry.
    If manifest is missing, returns an empty string (progressive enhancement).
    """
    manifest = _load_manifest()
    if not manifest:
        return ""

    # Support either bare entry name or with extension
    candidates: List[str] = [entry_name, f"{entry_name}.js", f"{entry_name}.ts"]
    key = next((k for k in candidates if k in manifest), None)
    if key is None:
        # Also try src/entries/<name>.ts
        alt = f"src/entries/{entry_name}.ts"
        if alt in manifest:
            key = alt
        else:
            return ""

    item = manifest[key]
    tags: List[str] = []

    # CSS files
    for css in item.get("css", []):
        href = f"/static/dist/{css}"
        tags.append(f'<link rel="stylesheet" href="{href}" />')

    # The JS entry
    file_path = item.get("file")
    if file_path:
        src = f"/static/dist/{file_path}"
        tags.append(f'<script type="module" src="{src}"></script>')

    # Imported CSS from dynamic imports
    for imp in item.get("imports", []):
        imp_item = manifest.get(imp)
        if not imp_item:
            continue
        for css in imp_item.get("css", []):
            href = f"/static/dist/{css}"
            link_tag = f'<link rel="stylesheet" href="{href}" />'
            if link_tag not in tags:
                tags.append(link_tag)

    return "\n".join(tags)
