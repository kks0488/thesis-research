#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def fetch_xml(url: str, user_agent: str, timeout_s: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read().decode("utf-8")


def text_or_none(elem: ET.Element | None) -> str | None:
    if elem is None or elem.text is None:
        return None
    t = elem.text.strip()
    return t or None


def parse_feed(xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    entries = []
    for entry in root.findall("atom:entry", ATOM_NS):
        authors = [text_or_none(a.find("atom:name", ATOM_NS)) for a in entry.findall("atom:author", ATOM_NS)]
        authors = [a for a in authors if a]
        links = entry.findall("atom:link", ATOM_NS)
        url = None
        for link in links:
            if link.attrib.get("rel") == "alternate" and link.attrib.get("type") == "text/html":
                url = link.attrib.get("href")
                break

        entries.append(
            {
                "source": "arxiv",
                "query": None,
                "retrieved_at": None,
                "id": text_or_none(entry.find("atom:id", ATOM_NS)),
                "title": text_or_none(entry.find("atom:title", ATOM_NS)),
                "published": text_or_none(entry.find("atom:published", ATOM_NS)),
                "updated": text_or_none(entry.find("atom:updated", ATOM_NS)),
                "summary": text_or_none(entry.find("atom:summary", ATOM_NS)),
                "authors": authors,
                "primary_category": entry.find("arxiv:primary_category", ATOM_NS).attrib.get("term")
                if entry.find("arxiv:primary_category", ATOM_NS) is not None
                else None,
                "url": url,
            }
        )
    return entries


def append_jsonl(path: Path, records: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search arXiv and append results to literature/library.jsonl.")
    parser.add_argument("--query", required=True, help='Search query, e.g. "cellular agriculture"')
    parser.add_argument("--max-results", type=int, default=50, help="Max results (<= 2000 recommended)")
    parser.add_argument("--start", type=int, default=0, help="Start offset")
    parser.add_argument("--sleep", type=float, default=0.5, help="Sleep seconds between requests")
    parser.add_argument("--out", default="literature/library.jsonl", help="Output JSONL path (relative to repo root)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_path = (root / args.out).resolve()

    max_results = max(1, int(args.max_results))
    start = max(0, int(args.start))

    base = "http://export.arxiv.org/api/query"
    search_query = f'all:"{args.query}"'
    retrieved_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    params = {
        "search_query": search_query,
        "start": str(start),
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{base}?{urllib.parse.urlencode(params)}"
    xml_text = fetch_xml(url, user_agent="thesis-research/0.1")
    records = parse_feed(xml_text)
    for rec in records:
        rec["query"] = args.query
        rec["retrieved_at"] = retrieved_at
    count = append_jsonl(out_path, records)
    time.sleep(max(0.0, float(args.sleep)))

    print(f"wrote {count} records -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
