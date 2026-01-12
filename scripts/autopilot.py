#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from deepseek_client import DeepSeekError, chat_completion, load_config_from_env


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_json(url: str, *, user_agent: str, timeout_s: int = 60) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_xml(url: str, *, user_agent: str, timeout_s: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read().decode("utf-8")


def text_or_none(elem: ET.Element | None) -> str | None:
    if elem is None or elem.text is None:
        return None
    t = elem.text.strip()
    return t or None


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
    summary: str | None
    id: str | None


@dataclass(frozen=True)
class PaperHit:
    query: str
    paper: Paper


def paper_key(p: Paper) -> str:
    for k in [p.doi, p.id, p.url, p.title]:
        if k and str(k).strip():
            return f"{p.source}:{str(k).strip()}"
    return f"{p.source}:unknown:{hash((p.source, p.title, p.url))}"


def search_openalex(*, query: str, pages: int, per_page: int, email: str | None) -> list[Paper]:
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
                name = (((auth.get("author") or {}).get("display_name")) or "").strip()
                if name:
                    authors.append(name)
            abstract = inverted_index_to_text(item.get("abstract_inverted_index"))
            out.append(
                Paper(
                    source="openalex",
                    id=item.get("id"),
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


def search_arxiv(*, query: str, max_results: int) -> list[Paper]:
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
                id=text_or_none(entry.find("atom:id", ATOM_NS)),
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


def rank(p: Paper) -> tuple[int, int, int]:
    has_text = 1 if (p.abstract or p.summary) else 0
    cited = int(p.cited_by_count or 0)
    year = int(p.year or 0)
    return (has_text, cited, year)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"seen_keys": [], "last_run_at": None}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    ensure_dir(path.parent)
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n


def to_library_record(p: Paper, *, query: str, retrieved_at: str) -> dict[str, Any]:
    return {
        "source": p.source,
        "query": query,
        "retrieved_at": retrieved_at,
        "id": p.id,
        "doi": p.doi,
        "title": p.title,
        "publication_year": p.year,
        "venue": p.venue,
        "cited_by_count": p.cited_by_count,
        "authors": p.authors,
        "url": p.url,
        "abstract": p.abstract,
        "summary": p.summary,
    }


DEFAULT_QUERIES = [
    "agentic coding mergeable PR",
    "SWE-bench Verified",
    "software engineering agent verification loop",
    "CI failure triage LLM",
    "repository-level code understanding retrieval",
    "program repair large language model tests",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Autopilot: continuously collect papers and write research briefs.")
    parser.add_argument("--topic", default="topics/003-enterprise-mergeable-pr-agent", help="Topic folder path")
    parser.add_argument("--queries", default="", help="Comma-separated queries (defaults are used if empty)")
    parser.add_argument("--openalex-pages", type=int, default=1)
    parser.add_argument("--openalex-per-page", type=int, default=25)
    parser.add_argument("--arxiv-max", type=int, default=25)
    parser.add_argument("--top-n", type=int, default=16)
    parser.add_argument("--email", default="", help="Optional email for OpenAlex mailto param")
    parser.add_argument("--no-llm", action="store_true", help="Collect only (no DeepSeek call)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    topic_dir = (root / args.topic).resolve()
    if not topic_dir.exists():
        raise SystemExit(f"topic folder not found: {topic_dir}")

    queries = [q.strip() for q in (args.queries.split(",") if args.queries else DEFAULT_QUERIES) if q.strip()]
    random.Random(0).shuffle(queries)

    state_path = root / "state" / "autopilot.json"
    state = load_state(state_path)
    seen = set(state.get("seen_keys") or [])

    retrieved_at = utc_now_iso()
    all_hits: list[PaperHit] = []
    for q in queries:
        for p in search_openalex(query=q, pages=args.openalex_pages, per_page=args.openalex_per_page, email=args.email or None):
            all_hits.append(PaperHit(query=q, paper=p))
        for p in search_arxiv(query=q, max_results=args.arxiv_max):
            all_hits.append(PaperHit(query=q, paper=p))

    # Dedup + mark seen
    fresh: list[PaperHit] = []
    for hit in all_hits:
        k = paper_key(hit.paper)
        if k in seen:
            continue
        seen.add(k)
        fresh.append(hit)

    # Append to global library
    library_path = root / "literature" / "library.jsonl"
    wrote = append_jsonl(
        library_path,
        [to_library_record(hit.paper, query=hit.query, retrieved_at=retrieved_at) for hit in fresh],
    )

    selected = sorted(fresh, key=lambda h: rank(h.paper), reverse=True)[: max(1, int(args.top_n))]

    runs_dir = topic_dir / "research_runs"
    ensure_dir(runs_dir)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = runs_dir / f"{ts}-autopilot.md"

    if args.no_llm:
        lines = ["# Autopilot (no-llm)", "", f"- retrieved_at: {retrieved_at}", f"- new_records: {wrote}", "", "## Top Papers", ""]
        for i, hit in enumerate(selected, start=1):
            p = hit.paper
            lines.append(f"{i}. {p.title} ({p.source})")
            lines.append(f"   - query: {hit.query}")
            if p.url:
                lines.append(f"   - {p.url}")
            if p.doi:
                lines.append(f"   - {p.doi}")
        out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    else:
        try:
            cfg = load_config_from_env()
        except DeepSeekError as e:
            raise SystemExit(f"DeepSeek not configured: {e}") from e

        items = []
        for i, hit in enumerate(selected, start=1):
            p = hit.paper
            items.append(
                {
                    "n": i,
                    "source": p.source,
                    "query": hit.query,
                    "title": p.title,
                    "year": p.year,
                    "venue": p.venue,
                    "cited_by_count": p.cited_by_count,
                    "authors": p.authors[:10],
                    "url": p.url,
                    "doi": p.doi,
                    "abstract_or_summary": (p.abstract or p.summary or "")[:2200],
                }
            )

        topic_readme = (topic_dir / "README.md").read_text(encoding="utf-8") if (topic_dir / "README.md").exists() else ""
        prompt = f"""
You are an autonomous research team. You must be conservative and reproducible.

Topic context:
{topic_readme}

Candidate papers (JSON):
{json.dumps(items, ensure_ascii=False, indent=2)}

Tasks:
1) Pick the top 8 papers and explain why (1-2 sentences each).
2) Propose 3 pairings of papers (A+B) where combining them could improve mergeable PR rate.
3) For the best pairing, propose a concrete method (system design + algorithmic idea).
4) Propose a 3-day evaluation plan with metrics, baselines, and failure taxonomy.
5) Output a Draft Abstract (150-220 words) for a tech report.

Hard rules:
- Do NOT invent citations. Use ONLY the provided papers; cite by (title + url/doi).
- If evidence is missing, say so and propose how to collect it.

Output format: Markdown. Language: Korean (paper titles stay original).
""".strip()

        content = chat_completion(
            [
                {"role": "system", "content": "You are a rigorous research lead. Be explicit about uncertainty and do not hallucinate citations."},
                {"role": "user", "content": prompt},
            ],
            config=cfg,
            temperature=0.2,
            max_tokens=1800,
        )
        out_path.write_text(content.strip() + "\n", encoding="utf-8")

    state["seen_keys"] = sorted(seen)[-20000:]
    state["last_run_at"] = retrieved_at
    save_state(state_path, state)

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
