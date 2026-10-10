"""Build a public-only static bundle; canonical URL/sitemap only for a configured site."""
from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/producer1218-code/HealthOS-Hardware-Skill"


def build(output: Path, base_url: str | None = None):
    output = output.resolve()
    source = (ROOT / "site").resolve()
    if output == ROOT or output == source or output in source.parents or source in output.parents:
        raise ValueError("Output must be separate from repository root and site source")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose an empty output directory; the builder never removes files")
    canonical = REPO
    if base_url:
        parsed = urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Public base URL must be HTTPS without credentials, query or fragment")
        canonical = base_url.rstrip("/") + "/"
    html = (source / "index.html").read_text(encoding="utf-8")
    if base_url:
        html = html.replace(f'<link rel="canonical" href="{REPO}">', f'<link rel="canonical" href="{escape(canonical, {chr(34): "&quot;"})}">')
        html = html.replace(f'<meta property="og:url" content="{REPO}">', f'<meta property="og:url" content="{escape(canonical, {chr(34): "&quot;"})}">')
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(html, encoding="utf-8")
    for origin, target in [(source / ".nojekyll", ".nojekyll"), (ROOT / "healthos-skill.json", "healthos-skill.json"), (ROOT / "llms.txt", "llms.txt")]:
        if origin.is_symlink():
            raise ValueError("Unexpected public source symlink")
        (output / target).write_bytes(origin.read_bytes())
    if base_url:
        (output / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>' + escape(canonical) + '</loc></url></urlset>\n', encoding="utf-8")
    return canonical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "demo-output/public-site")
    parser.add_argument("--base-url", help="Verified Pages deployment base; omit for offline artifact")
    args = parser.parse_args()
    print("Built public-only bundle; canonical:", build(args.output, args.base_url))


if __name__ == "__main__":
    main()
