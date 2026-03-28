from __future__ import annotations

import argparse
import sys
from pathlib import Path


OLD_SENTENCE = "Never update memories. You can only read them."
NEW_BLOCK = "\n".join(
    [
        "Do not directly modify Codex-managed memory artifacts under {{ base_path }} in this session.",
        "Treat only that Codex memory root as read-only.",
        "This restriction does not apply to unrelated project directories or other MCP-managed state unless separately instructed.",
    ]
)
DEFAULT_TARGET = Path("upstream/codex-rs/core/templates/memories/read_path.md")


def replace_read_path_scope(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    match_count = content.count(OLD_SENTENCE)
    if match_count != 1:
        raise ValueError(
            f"Expected exactly one match for target sentence, found {match_count} in {path}"
        )

    updated = content.replace(OLD_SENTENCE, NEW_BLOCK)
    if OLD_SENTENCE in updated:
        raise ValueError(f"Target sentence still exists after replacement in {path}")
    if updated.count(NEW_BLOCK) != 1:
        raise ValueError(f"Expected exactly one replacement block in {path}")

    path.write_text(updated, encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replace the over-broad read_path memory restriction with a scoped variant."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(DEFAULT_TARGET),
        help="Path to codex-rs/core/templates/memories/read_path.md",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = Path(args.path)
    replace_read_path_scope(target)
    print(f"Updated {target}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
