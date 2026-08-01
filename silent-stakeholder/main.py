"""
Silent Stakeholder — CLI entrypoint.

  python main.py --sample 3000     # analyze (free LLM or heuristics)
  python main.py --chat            # launch chatbot UI
  python app.py                    # same as --chat
"""

from __future__ import annotations

import argparse

from config import TOP_N_GAPS
import llm


def main():
    parser = argparse.ArgumentParser(description="Silent Stakeholder")
    parser.add_argument("--sample", type=int, default=None, help="Sample N reviews")
    parser.add_argument("--top", type=int, default=TOP_N_GAPS, help="Top N gaps (3-20)")
    parser.add_argument("--chat", action="store_true", help="Launch chatbot UI")
    args = parser.parse_args()

    if args.chat:
        from app import main as chat_main

        chat_main()
        return

    print(f"LLM backend: {llm.active_provider()}")
    from pipeline import run_analysis

    gaps = run_analysis(sample_n=args.sample, top_n=args.top)
    for i, g in enumerate(gaps, 1):
        print(f"#{i} [{g.verdict}] {g.confidence}% — {g.need}")


if __name__ == "__main__":
    main()
