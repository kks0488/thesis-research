#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deepseek_client import chat_completion, load_config_from_env


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9가-힣\\s-]", "", text)
    text = re.sub(r"\\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "run"


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


@dataclass(frozen=True)
class Paper:
    source: str
    title: str | None
    year: int | None
    venue: str | None
    cited_by_count: int | None
    authors: list[str]
    url: str | None
    doi: str | None
    abstract: str | None
    summary: str | None  # arXiv summary


def search_openalex(query: str, per_page: int, pages: int, email: str | None) -> list[Paper]:
    base = "https://api.openalex.org/works"
    ua = "thesis-research/0.1 (mailto:unknown)" if not email else f"thesis-research/0.1 (mailto:{email})"
    per_page = max(1, min(200, int(per_page)))
    pages = max(1, int(pages))

    out: list[Paper] = []
    for page in range(1, pages + 1):
        params = {"search": query, "per-page": str(per_page), "page": str(page)}
        if email:
            params["mailto"] = email
        url = f"{base}?{urllib.parse.urlencode(params)}"
        payload = fetch_json(url, user_agent=ua)
        for item in payload.get("results", []) or []:
            authors = []
            for auth in (item.get("authorships") or []):
                name = ((auth.get("author") or {}).get("display_name") or "").strip()
                if name:
                    authors.append(name)
            abstract = inverted_index_to_text(item.get("abstract_inverted_index"))
            out.append(
                Paper(
                    source="openalex",
                    title=item.get("display_name"),
                    year=item.get("publication_year"),
                    venue=(((((item.get("primary_location") or {}).get("source") or {}).get("display_name")) or None)),
                    cited_by_count=item.get("cited_by_count"),
                    authors=authors,
                    url=item.get("id"),
                    doi=item.get("doi"),
                    abstract=abstract,
                    summary=None,
                )
            )
        time.sleep(0.2)
    return out


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def fetch_xml(url: str, user_agent: str, timeout_s: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read().decode("utf-8")


def text_or_none(elem: ET.Element | None) -> str | None:
    if elem is None or elem.text is None:
        return None
    t = elem.text.strip()
    return t or None


def search_arxiv(query: str, max_results: int) -> list[Paper]:
    base = "http://export.arxiv.org/api/query"
    search_query = f'all:"{query}"'
    params = {
        "search_query": search_query,
        "start": "0",
        "max_results": str(max(1, int(max_results))),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{base}?{urllib.parse.urlencode(params)}"
    xml_text = fetch_xml(url, user_agent="thesis-research/0.1")
    root = ET.fromstring(xml_text)

    out: list[Paper] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        authors = [text_or_none(a.find("atom:name", ATOM_NS)) for a in entry.findall("atom:author", ATOM_NS)]
        authors = [a for a in authors if a]
        links = entry.findall("atom:link", ATOM_NS)
        url_html = None
        for link in links:
            if link.attrib.get("rel") == "alternate" and link.attrib.get("type") == "text/html":
                url_html = link.attrib.get("href")
                break

        out.append(
            Paper(
                source="arxiv",
                title=text_or_none(entry.find("atom:title", ATOM_NS)),
                year=None,
                venue="arXiv",
                cited_by_count=None,
                authors=authors,
                url=url_html,
                doi=None,
                abstract=None,
                summary=text_or_none(entry.find("atom:summary", ATOM_NS)),
            )
        )
    return out


def to_library_record(p: Paper, *, query: str) -> dict[str, Any]:
    return {
        "source": p.source,
        "query": query,
        "retrieved_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "title": p.title,
        "publication_year": p.year,
        "venue": p.venue,
        "cited_by_count": p.cited_by_count,
        "doi": p.doi,
        "url": p.url,
        "authors": p.authors,
        "abstract": p.abstract,
        "summary": p.summary,
    }


def append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def rank(p: Paper) -> tuple[int, int, int]:
    year = int(p.year or 0)
    cited = int(p.cited_by_count or 0)
    has_text = 1 if (p.abstract or p.summary) else 0
    return (has_text, cited, year)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search papers and ask DeepSeek to produce a topic research brief.")
    parser.add_argument("--topic", required=True, help="Topic folder path, e.g. topics/001-...")
    parser.add_argument("--query", required=True, help="Literature search query")
    parser.add_argument("--openalex-pages", type=int, default=2)
    parser.add_argument("--openalex-per-page", type=int, default=25)
    parser.add_argument("--arxiv-max", type=int, default=30)
    parser.add_argument("--top-n", type=int, default=12, help="How many papers to pass into the LLM")
    parser.add_argument("--email", default="", help="Optional email for OpenAlex mailto param")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    topic_dir = (root / args.topic).resolve()
    if not topic_dir.exists():
        raise SystemExit(f"topic folder not found: {topic_dir}")

    cfg = load_config_from_env()

    papers: list[Paper] = []
    papers.extend(search_openalex(args.query, per_page=args.openalex_per_page, pages=args.openalex_pages, email=args.email or None))
    papers.extend(search_arxiv(args.query, max_results=args.arxiv_max))

    # Save library snapshot (append-only)
    library_path = root / "literature" / "library.jsonl"
    append_jsonl(library_path, [to_library_record(p, query=args.query) for p in papers])

    selected = sorted(papers, key=rank, reverse=True)[: max(1, int(args.top_n))]
    items = []
    for i, p in enumerate(selected, start=1):
        items.append(
            {
                "n": i,
                "source": p.source,
                "title": p.title,
                "year": p.year,
                "venue": p.venue,
                "cited_by_count": p.cited_by_count,
                "authors": p.authors[:8],
                "url": p.url,
                "doi": p.doi,
                "abstract_or_summary": (p.abstract or p.summary or "")[:2000],
            }
        )

    topic_readme = (topic_dir / "README.md").read_text(encoding="utf-8") if (topic_dir / "README.md").exists() else ""
    prompt = f"""
You are an AI research team focusing on "future food" thesis-driven innovation.

Topic context (from README):
{topic_readme}

Search query: {args.query}

Candidate papers (JSON):
{json.dumps(items, ensure_ascii=False, indent=2)}

Tasks:
1) Produce a prioritized reading list (top 8) with 1-2 sentences each: why it matters for this topic.
2) Extract 5-8 concrete claims we can reuse, each with a citation pointer (title + url/doi).
3) Propose 3 falsifiable hypotheses that would create a "new future-food opportunity".
4) Propose 3 small experiments/analyses we can do in 1-3 days without special equipment.
5) Provide a 2-week execution plan (bulleted).

Output format: Markdown with clear headings.
Language: Korean, but keep paper titles in original language.
""".strip()

    content = chat_completion(
        [
            {"role": "system", "content": "You are a rigorous research lead. Do not hallucinate citations; use only provided items."},
            {"role": "user", "content": prompt},
        ],
        config=cfg,
        temperature=0.2,
        max_tokens=1800,
    )

    runs_dir = topic_dir / "research_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = runs_dir / f"{ts}-{slugify(args.query)[:40]}.md"
    out_path.write_text(content.strip() + "\n", encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

