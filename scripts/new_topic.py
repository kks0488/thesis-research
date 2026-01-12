#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Topic:
    topic_id: int
    slug: str
    title: str


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9가-힣\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "topic"


def next_topic_id(topics_dir: Path) -> int:
    if not topics_dir.exists():
        return 1
    ids: list[int] = []
    for path in topics_dir.iterdir():
        if not path.is_dir():
            continue
        match = re.match(r"^(\d{3})-", path.name)
        if match:
            ids.append(int(match.group(1)))
    return (max(ids) + 1) if ids else 1


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a new research topic folder with templates.")
    parser.add_argument("title", help="Topic title, e.g. 'Future food: precision fermentation protein'")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    topics_dir = root / "topics"
    topic_id = next_topic_id(topics_dir)
    slug = slugify(args.title)[:48]
    topic = Topic(topic_id=topic_id, slug=slug, title=args.title.strip())

    folder = topics_dir / f"{topic.topic_id:03d}-{topic.slug}"
    folder.mkdir(parents=True, exist_ok=False)

    write_file(
        folder / "README.md",
        f"""# {topic.title}

## Problem statement (1 sentence)

## Hypothesis (falsifiable)

## Success metrics

## Why now? (signals from recent theses/papers)

## Plan (next 2 weeks)
""",
    )
    write_file(folder / "claims.md", "# Claims\n\n- (주장) → (근거 링크)\n")
    write_file(folder / "experiments.md", "# Experiments\n\n(templates/experiment_log.md 참고)\n")
    write_file(folder / "decisions.md", "# Decisions\n\n- YYYY-MM-DD: ...\n")
    write_file(folder / "limitations.md", "# Limitations\n\n- ...\n")

    print(folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
