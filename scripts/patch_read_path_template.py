from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import probe_read_path_block
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import probe_read_path_block


DEFAULT_TEMPLATE_PATH = Path(".temp/upstream-read_path-main.md")
DEFAULT_OUTPUT_PATH = Path(".temp/read_path.patched.md")

SCOPE_HEADER = (
    "This section applies only to Codex-managed global memory under {{ base_path }}."
)
SCOPED_WARNING = (
    "Never update Codex-managed memory under {{ base_path }}. You can only read it."
)
INTRO_ANCHOR = (
    "time and help you stay consistent. Use it whenever it is likely to help.\n"
)
ORIGINAL_WARNING = "Never update memories. You can only read them."
JSONL_DETAIL_ORIGINAL = (
    "  - These files are append-only `jsonl`: `session_meta.payload.id` identifies the session, "
    "`turn_context` marks turn boundaries, `event_msg` is the lightweight status stream, and "
    "`response_item` contains actual messages, tool calls, and tool outputs."
)
JSONL_DETAIL_PATCHED = (
    "  - These files are append-only `jsonl`: `session_meta.payload.id` is the session id, "
    "`turn_context` marks turns, and `response_item` contains messages, tool calls, and tool outputs."
)
QUICK_PASS_STEP4_ORIGINAL = (
    "4. If above are not clear and you need exact commands, error text, or precise evidence, "
    "search over `rollout_path` for more evidence."
)
QUICK_PASS_STEP4_PATCHED = (
    "4. If you still need exact commands, errors, or evidence, inspect `rollout_path` next."
)


def normalize_template_for_binary(template_text: str) -> bytes:
    return probe_read_path_block.normalize_template_for_binary(template_text)


def _replace_exactly_once(
    text: str, old: str, new: str, *, label: str
) -> str:
    match_count = text.count(old)
    if match_count != 1:
        raise ValueError(
            f"Expected exactly one match for {label}, found {match_count}"
        )
    return text.replace(old, new)


def build_patched_template(template_text: str) -> str:
    patched = _replace_exactly_once(
        template_text,
        INTRO_ANCHOR,
        INTRO_ANCHOR + "\n" + SCOPE_HEADER + "\n",
        label="intro anchor",
    )
    patched = _replace_exactly_once(
        patched,
        ORIGINAL_WARNING,
        SCOPED_WARNING,
        label="original warning",
    )
    patched = _replace_exactly_once(
        patched,
        JSONL_DETAIL_ORIGINAL,
        JSONL_DETAIL_PATCHED,
        label="jsonl detail",
    )
    patched = _replace_exactly_once(
        patched,
        QUICK_PASS_STEP4_ORIGINAL,
        QUICK_PASS_STEP4_PATCHED,
        label="quick-pass step 4",
    )

    original_block = normalize_template_for_binary(template_text)
    patched_block = normalize_template_for_binary(patched)
    if len(original_block) != len(patched_block):
        raise ValueError(
            "Patched template length mismatch: "
            f"expected {len(original_block)} bytes, got {len(patched_block)}"
        )

    return patched


def patch_template_file(input_path: Path, output_path: Path) -> str:
    template_text = input_path.read_text(encoding="utf-8")
    patched = build_patched_template(template_text)
    output_path.write_text(patched, encoding="utf-8", newline="\n")
    return patched


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Patch read_path.md with a scoped Codex-managed global memory warning."
    )
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE_PATH),
        help="Path to the upstream read_path.md template file.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to write the patched read_path.md template.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    template_path = Path(args.template)
    output_path = Path(args.output)
    patched = patch_template_file(template_path, output_path)
    payload = {
        "template_path": str(template_path),
        "output_path": str(output_path),
        "input_length": len(normalize_template_for_binary(template_path.read_text(encoding="utf-8"))),
        "output_length": len(normalize_template_for_binary(patched)),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    for key in ("template_path", "output_path", "input_length", "output_length"):
        print(f"{key}={payload[key]}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
