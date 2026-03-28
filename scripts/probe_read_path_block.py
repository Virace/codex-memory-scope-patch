from __future__ import annotations

import argparse
import json
import mmap
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_EXE_PATH = Path(".temp/codex.exe")
DEFAULT_TEMPLATE_PATH = Path(".temp/upstream-read_path-main.md")


@dataclass(frozen=True)
class ReadPathBlockMatch:
    start_offset: int
    end_offset_inclusive: int
    length: int
    matched_bytes: bytes

    @property
    def start_offset_hex(self) -> str:
        return f"0x{self.start_offset:X}"

    @property
    def end_offset_inclusive_hex(self) -> str:
        return f"0x{self.end_offset_inclusive:X}"

    @property
    def length_hex(self) -> str:
        return f"0x{self.length:X}"


def normalize_template_for_binary(template_text: str) -> bytes:
    normalized = template_text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\n", "\r\n")
    if normalized.endswith("\r\n"):
        normalized = normalized[:-2]
    return normalized.encode("utf-8")


def _find_unique_match(mm: mmap.mmap, needle: bytes) -> int:
    first = mm.find(needle)
    if first < 0:
        raise ValueError("Expected exactly one embedded block match, found 0")

    second = mm.find(needle, first + 1)
    if second >= 0:
        raise ValueError(
            f"Expected exactly one embedded block match, found multiple at 0x{first:X} and 0x{second:X}"
        )

    return first


def locate_read_path_block(exe_path: Path, template_path: Path) -> ReadPathBlockMatch:
    template_text = template_path.read_text(encoding="utf-8")
    needle = normalize_template_for_binary(template_text)
    if not needle:
        raise ValueError(f"Normalized template is empty: {template_path}")

    with exe_path.open("rb") as handle, mmap.mmap(
        handle.fileno(), 0, access=mmap.ACCESS_READ
    ) as mm:
        start_offset = _find_unique_match(mm, needle)

    return ReadPathBlockMatch(
        start_offset=start_offset,
        end_offset_inclusive=start_offset + len(needle) - 1,
        length=len(needle),
        matched_bytes=needle,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Locate the embedded read_path.md template block inside a codex executable."
    )
    parser.add_argument(
        "--exe",
        default=str(DEFAULT_EXE_PATH),
        help="Path to the target codex executable.",
    )
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE_PATH),
        help="Path to the upstream read_path.md template file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of key=value lines.",
    )
    return parser.parse_args(argv)


def _build_output_payload(
    exe_path: Path, template_path: Path, match: ReadPathBlockMatch
) -> dict[str, object]:
    payload = asdict(match)
    payload["matched_bytes"] = None
    payload["exe_path"] = str(exe_path)
    payload["template_path"] = str(template_path)
    payload["start_offset_hex"] = match.start_offset_hex
    payload["end_offset_inclusive_hex"] = match.end_offset_inclusive_hex
    payload["length_hex"] = match.length_hex
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exe_path = Path(args.exe)
    template_path = Path(args.template)
    match = locate_read_path_block(exe_path, template_path)
    payload = _build_output_payload(exe_path, template_path, match)

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    for key in (
        "exe_path",
        "template_path",
        "start_offset",
        "start_offset_hex",
        "end_offset_inclusive",
        "end_offset_inclusive_hex",
        "length",
        "length_hex",
    ):
        print(f"{key}={payload[key]}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
