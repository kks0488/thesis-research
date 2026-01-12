#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class OpenAlexWork:
    source: str
    query: str
    retrieved_at: str
    id: str | None
    doi: str | None
    title: str | None
    publication_year: int | None
    venue: str | None
    cited_by_count: int | None
    authors: list[str]
    url: str | None
    open_access: str | None
    abstract: str | None


def _get(obj: dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = obj
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def fetch_json(url: str, user_agent: str, timeout_s: int = 30) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def inverted_index_to_text(inv: dict[str, list[int]] | None) -> str | None:
    if not inv:
        return None
    positions: dict[int, str] = {}
    for token, idxs in inv.items():
        for i in idxs:
            positions[int(i)] = token
    if not positions:
        return None
    return " ".join(positions[i] for i in sorted(positions.keys())).strip() or None


def parse_works(payload: dict[str, Any], *, query: str, retrieved_at: str) -> Iterable[OpenAlexWork]:
    for item in payload.get("results", []) or []:
        authors: list[str] = []
        for auth in (item.get("authorships") or []):
            name = _get(auth, "author.display_name")
            if name:
                authors.append(str(name))
        abstract = inverted_index_to_text(item.get("abstract_inverted_index"))
        yield OpenAlexWork(
            source="openalex",
            query=query,
            retrieved_at=retrieved_at,
            id=item.get("id"),
            doi=item.get("doi"),
            title=item.get("display_name"),
            publication_year=item.get("publication_year"),
            venue=_get(item, "primary_location.source.display_name"),
            cited_by_count=item.get("cited_by_count"),
            authors=authors,
            url=item.get("id"),
            open_access=str(_get(item, "open_access.oa_status") or "") or None,
            abstract=abstract,
        )


def to_jsonl_record(work: OpenAlexWork) -> dict[str, Any]:
    return {
        "source": work.source,
        "query": work.query,
        "retrieved_at": work.retrieved_at,
        "id": work.id,
        "doi": work.doi,
        "title": work.title,
        "publication_year": work.publication_year,
        "venue": work.venue,
        "cited_by_count": work.cited_by_count,
        "authors": work.authors,
        "url": work.url,
        "open_access": work.open_access,
        "abstract": work.abstract,
    }


def append_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source",
        "query",
        "retrieved_at",
        "title",
        "publication_year",
        "venue",
        "cited_by_count",
        "doi",
        "url",
        "authors",
        "open_access",
        "abstract",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for rec in records:
            row = dict(rec)
            row["authors"] = "; ".join(rec.get("authors") or [])
            w.writerow({k: row.get(k) for k in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description="Search OpenAlex works and append results to literature/library.jsonl.")
    parser.add_argument("--query", required=True, help="Search query, e.g. 'precision fermentation protein'")
    parser.add_argument("--per-page", type=int, default=25, help="Results per page (max 200)")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to fetch")
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between requests")
    parser.add_argument("--out", default="literature/library.jsonl", help="Output JSONL path (relative to repo root)")
    parser.add_argument("--csv", default="", help="Optional CSV output path (relative to repo root)")
    parser.add_argument(
        "--email",
        default="",
        help="Optional contact email for polite API usage (sent as mailto param).",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_path = (root / args.out).resolve()
    csv_path = (root / args.csv).resolve() if args.csv else None

    per_page = max(1, min(200, int(args.per_page)))
    pages = max(1, int(args.pages))

    base = "https://api.openalex.org/works"
    user_agent = "thesis-research/0.1 (mailto:unknown)" if not args.email else f"thesis-research/0.1 (mailto:{args.email})"
    retrieved_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    all_records: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        params = {
            "search": args.query,
            "per-page": str(per_page),
            "page": str(page),
        }
        if args.email:
            params["mailto"] = args.email
        url = f"{base}?{urllib.parse.urlencode(params)}"
        payload = fetch_json(url, user_agent=user_agent)
        works = [to_jsonl_record(w) for w in parse_works(payload, query=args.query, retrieved_at=retrieved_at)]
        all_records.extend(works)
        time.sleep(max(0.0, float(args.sleep)))

    count = append_jsonl(out_path, all_records)
    if csv_path:
        write_csv(csv_path, all_records)

    print(f"wrote {count} records -> {out_path}")
    if csv_path:
        print(f"wrote csv -> {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
