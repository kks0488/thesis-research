#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def ensure_workshop(workshop_file: Path) -> None:
    if not workshop_file.exists():
        raise SystemExit(f"Workshop file not found: {workshop_file}")
    if workshop_file.suffix.lower() != ".md":
        raise SystemExit("Workshop file must be a .md file")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge into AI-Scientist-v2 ideation.")
    parser.add_argument("--workshop-file", required=True, help="Workshop description markdown file")
    parser.add_argument("--max-ideas", type=int, default=3)
    parser.add_argument("--num-reflections", type=int, default=2)
    parser.add_argument("--out", default="", help="Optional output JSON path for ideas")
    args = parser.parse_args()

    ai_home = Path(os.getenv("AI_SCIENTIST_HOME") or "").expanduser()
    if not ai_home.exists():
        raise SystemExit("AI_SCIENTIST_HOME not set or path not found. Clone https://github.com/SakanaAI/AI-Scientist-v2 first.")

    if not os.getenv("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY must be set for AI-Scientist-v2 DeepSeek usage.")

    workshop_file = Path(args.workshop_file).resolve()
    ensure_workshop(workshop_file)

    ideation_script = ai_home / "ai_scientist" / "perform_ideation_temp_free.py"
    if not ideation_script.exists():
        raise SystemExit(f"AI-Scientist-v2 script not found: {ideation_script}")

    model = (os.getenv("AI_SCIENTIST_MODEL") or "deepseek-coder-v2-0724").strip()
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
