#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from deepseek_client import DeepSeekError, chat_completion, load_config_from_env


def ensure_workshop(workshop_file: Path) -> None:
    if not workshop_file.exists():
        raise SystemExit(f"Workshop file not found: {workshop_file}")
    if workshop_file.suffix.lower() != ".md":
        raise SystemExit("Workshop file must be a .md file")


def extract_json(text: str) -> dict | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def generate_ideas_compat(workshop_text: str, *, max_ideas: int, num_reflections: int) -> list[dict]:
    try:
        cfg = load_config_from_env()
    except DeepSeekError as e:
        raise SystemExit(f"DeepSeek not configured: {e}") from e

    ideas: list[dict] = []
    for i in range(max_ideas):
        prev = json.dumps(ideas, ensure_ascii=False, indent=2)
        prompt = f"""
You are an AI research ideation system. Produce one proposal at a time.

Workshop description:
{workshop_text}

Previous proposals (JSON list):
{prev}

Output ONLY JSON with this schema:
{{
  "Name": "...",
  "Title": "...",
  "Short Hypothesis": "...",
  "Related Work": "...",
  "Abstract": "...",
  "Experiments": ["..."],
  "Risk Factors and Limitations": ["..."]
}}
""".strip()
        content = chat_completion(
            [{"role": "user", "content": prompt}],
            config=cfg,
            temperature=0.4,
            max_tokens=1600,
        )
        idea = extract_json(content) or {"raw": content}

        for _ in range(max(0, num_reflections - 1)):
            refine_prompt = f"""
Refine the following proposal to improve novelty and feasibility. Output ONLY JSON with the same schema.

Proposal JSON:
{json.dumps(idea, ensure_ascii=False, indent=2)}
""".strip()
            refined = chat_completion(
                [{"role": "user", "content": refine_prompt}],
                config=cfg,
                temperature=0.3,
                max_tokens=1400,
            )
            idea = extract_json(refined) or idea

        ideas.append(idea)
    return ideas


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge into AI-Scientist-v2 ideation.")
    parser.add_argument("--workshop-file", required=True, help="Workshop description markdown file")
    parser.add_argument("--max-ideas", type=int, default=3)
    parser.add_argument("--num-reflections", type=int, default=2)
    parser.add_argument("--out", default="", help="Optional output JSON path for ideas")
    args = parser.parse_args()

    workshop_file = Path(args.workshop_file).resolve()
    ensure_workshop(workshop_file)

    model = (os.getenv("AI_SCIENTIST_MODEL") or "deepseek-reasoner").strip()
    native_ok = model == "deepseek-coder-v2-0724" and (os.getenv("AI_SCIENTIST_NATIVE") or "").strip() == "1"
    if not native_ok:
        try:
            load_config_from_env()
        except DeepSeekError as e:
            raise SystemExit(f"DeepSeek not configured: {e}") from e
    if native_ok:
        ai_home = Path(os.getenv("AI_SCIENTIST_HOME") or "").expanduser()
        if not ai_home.exists():
            raise SystemExit("AI_SCIENTIST_HOME not set or path not found. Clone https://github.com/SakanaAI/AI-Scientist-v2 first.")
        ideation_script = ai_home / "ai_scientist" / "perform_ideation_temp_free.py"
        if not ideation_script.exists():
            raise SystemExit(f"AI-Scientist-v2 script not found: {ideation_script}")

        python_bin = os.getenv("AI_SCIENTIST_PYTHON") or sys.executable
        cmd = [
            python_bin,
            str(ideation_script),
            "--workshop-file",
            str(workshop_file),
            "--model",
            model,
            "--max-num-generations",
            str(int(args.max_ideas)),
            "--num-reflections",
            str(int(args.num_reflections)),
        ]
        subprocess.run(cmd, check=True)
        idea_path = Path(str(workshop_file)).with_suffix(".json")
        if not idea_path.exists():
            raise SystemExit(f"AI-Scientist-v2 output not found: {idea_path}")
        ideas = json.loads(idea_path.read_text(encoding="utf-8"))
    else:
        workshop_text = workshop_file.read_text(encoding="utf-8")
        ideas = generate_ideas_compat(
            workshop_text,
            max_ideas=int(args.max_ideas),
            num_reflections=int(args.num_reflections),
        )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(ideas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(out_path)
    else:
        print(json.dumps(ideas, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
