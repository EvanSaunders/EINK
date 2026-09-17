#!/usr/bin/env python3
"""
Planet Zoo 2 Zoopedia scraper -- messages.json edition.

Frontier's Zoopedia page loads its text from a static i18n bundle:
    https://www.planetzoogame.com/_i18n/<BUILD_HASH>/en-US/messages.json

That file contains every animal's name, scientific name, description,
conservation info, social/reproduction text, wild population and fun facts,
keyed like "Animal_Lion_African" / "Zoopedia_Description_Lion_African" / etc.
The BUILD_HASH changes whenever Frontier redeploys, so this script re-discovers
it each run by scraping the current hash out of the live Zoopedia page.

Two-tier fetch strategy:
  1. Try plain `requests` first (fast, no browser). Static JSON assets are
     often served without the bot-detection the HTML pages have.
  2. If that's blocked, fall back to Playwright (real browser) for both the
     hash discovery and the JSON fetch.

Diffing:
  Every run compares the full en-US "Animal_*" key set (names) plus every
  "Zoopedia_*_<slug>" field against the previous saved copy. New animals and
  changed fields are logged. The full messages.json is archived each run
  (dated) plus kept as "latest_messages.json" for reference.

This script does NOT download images -- messages.json has no image URLs.
The animal-name slugs here (e.g. "Lion_African") match the CDN filename
convention (Lion_African_illustration.jpg) but the CDN folder hash per
animal still needs to be resolved separately (e.g. via a browser visiting
that animal's own Zoopedia page) -- a good next step once this text-diffing
loop is confirmed working.

Usage:
    pip install requests playwright   # playwright only needed as fallback
    playwright install chromium
    python zoopedia_scrape.py --out ./zoopedia
    python zoopedia_scrape.py --out ./zoopedia --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://www.planetzoogame.com"
ZOOPEDIA_URL = f"{BASE}/en-US/2/zoopedia"
HASH_RE = re.compile(r"_i18n/([a-f0-9]{6,10})/en-US/messages\.json")
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Accept": "*/*"}


# --------------------------------------------------------------------------
# Fetching: plain requests first, Playwright fallback
# --------------------------------------------------------------------------

def discover_hash_requests(session: requests.Session, log) -> str | None:
    try:
        resp = session.get(ZOOPEDIA_URL, headers=HEADERS, timeout=20)
        log(f"  GET {ZOOPEDIA_URL} -> {resp.status_code}")
        if resp.status_code != 200:
            return None
        m = HASH_RE.search(resp.text)
        return m.group(1) if m else None
    except Exception as exc:
        log(f"  requests hash discovery failed: {exc}")
        return None


def fetch_messages_requests(session: requests.Session, build_hash: str, log) -> dict | None:
    url = f"{BASE}/_i18n/{build_hash}/en-US/messages.json"
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        log(f"  GET {url} -> {resp.status_code}")
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        log(f"  requests messages.json fetch failed: {exc}")
    return None


def fetch_via_playwright(cached_hash: str | None, log):
    """Returns (messages_dict, build_hash) using a real browser."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, locale="en-US")
        page = ctx.new_page()

        found = {}

        def on_response(resp):
            if "_i18n/" in resp.url and resp.url.endswith("messages.json"):
                found["url"] = resp.url

        page.on("response", on_response)
        log(f"  [playwright] -> {ZOOPEDIA_URL}")
        page.goto(ZOOPEDIA_URL, wait_until="networkidle", timeout=60000)
        time.sleep(1)

        messages_url = found.get("url")
        if not messages_url:
            html = page.content()
            m = HASH_RE.search(html)
            if m:
                messages_url = f"{BASE}/_i18n/{m.group(1)}/en-US/messages.json"

        if not messages_url and cached_hash:
            messages_url = f"{BASE}/_i18n/{cached_hash}/en-US/messages.json"

        data = None
        build_hash = None
        if messages_url:
            m = HASH_RE.search(messages_url)
            build_hash = m.group(1) if m else None
            log(f"  [playwright] messages.json = {messages_url}")
            resp = ctx.request.get(messages_url, timeout=20000)
            if resp.ok:
                data = resp.json()

        browser.close()
        return data, build_hash


def fetch_messages_json(state: dict, log) -> tuple[dict | None, str | None]:
    """Full strategy: cached hash -> requests; else discover hash -> requests;
    else Playwright end to end."""
    session = requests.Session()
    cached_hash = state.get("build_hash")

    if cached_hash:
        log(f"trying cached build hash {cached_hash} via plain HTTP")
        data = fetch_messages_requests(session, cached_hash, log)
        if data:
            return data, cached_hash

    log("discovering current build hash via plain HTTP")
    fresh_hash = discover_hash_requests(session, log)
    if fresh_hash:
        data = fetch_messages_requests(session, fresh_hash, log)
        if data:
            return data, fresh_hash

    log("plain HTTP path failed or blocked -- falling back to Playwright")
    try:
        data, build_hash = fetch_via_playwright(cached_hash, log)
        return data, build_hash
    except ImportError:
        print(
            "Playwright not installed and plain HTTP fetch failed. "
            "Run: pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
        return None, None
    except Exception as exc:
        print(f"Playwright fallback failed: {exc}", file=sys.stderr)
        return None, None


# --------------------------------------------------------------------------
# Parsing / diffing
# --------------------------------------------------------------------------

def extract_animal_slugs(en_us: dict) -> dict[str, str]:
    """{slug: display_name} from 'Animal_<slug>' keys (skip _Plural)."""
    out = {}
    for key, val in en_us.items():
        if key.startswith("Animal_") and not key.endswith("_Plural"):
            out[key[len("Animal_"):]] = val
    return out


def fields_for_slug(en_us: dict, slug: str) -> dict:
    """Every Zoopedia_<Category>_<slug> field for this animal, plus fun facts."""
    suffix = f"_{slug}"
    out = {}
    for key, val in en_us.items():
        if key.startswith("Zoopedia_") and key.endswith(suffix) and "FunFacts" not in key:
            category = key[len("Zoopedia_"):-len(suffix)]
            out[category] = val
    facts = []
    i = 1
    while True:
        k = f"Zoopedia_FunFacts_{slug}_{i}"
        if k in en_us:
            facts.append(en_us[k])
            i += 1
        else:
            break
    if facts:
        out["FunFacts"] = facts
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape Planet Zoo 2's Zoopedia via messages.json.")
    ap.add_argument("--out", default="./zoopedia", help="output folder (default ./zoopedia)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    archive_dir = out / "messages_archive"
    archive_dir.mkdir(exist_ok=True)

    state_path = out / "state.json"
    manifest_path = out / "animals.json"
    log_path = out / "changes.log"

    def log(msg: str) -> None:
        if args.verbose:
            print(msg)

    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    data, build_hash = fetch_messages_json(state, log)
    if not data or "en-US" not in data:
        print("Failed to fetch messages.json via any method.", file=sys.stderr)
        return 1

    en_us = data["en-US"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    (archive_dir / f"{now.replace(':', '-')}.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    (out / "latest_messages.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    slugs = extract_animal_slugs(en_us)
    log(f"found {len(slugs)} animals in messages.json")

    new_slugs, changed = [], []

    for slug, name in sorted(slugs.items()):
        fields = fields_for_slug(en_us, slug)
        prev = manifest.get(slug)
        if prev is None:
            new_slugs.append(slug)
            print(f"NEW  {name}  ({slug})")
        else:
            for k, v in fields.items():
                if prev.get("fields", {}).get(k) != v:
                    changed.append(f"{slug}.{k}")
        manifest[slug] = {
            "name": name,
            "fields": fields,
            "last_seen": now,
            "first_seen": prev["first_seen"] if prev else now,
        }

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    state["build_hash"] = build_hash
    state["last_run"] = now
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{now}] hash={build_hash} {len(slugs)} animals, "
                 f"{len(new_slugs)} new, {len(changed)} fields changed\n")
        for s in new_slugs:
            fh.write(f"  + {manifest[s]['name']} ({s})\n")
        for c in changed:
            fh.write(f"  ~ {c}\n")

    print(f"{len(slugs)} animals total, {len(new_slugs)} new, "
          f"{len(changed)} field changes. Manifest: {manifest_path}")
    if not build_hash:
        print("Warning: could not confirm build hash this run; will re-discover next time.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

