from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

try:
    import patch_read_path_template
    import probe_read_path_block
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import patch_read_path_template
    import probe_read_path_block


DEFAULT_OUTPUT_EXE_PATH = Path(".temp/codex-patched.exe")
DEFAULT_OUTPUT_TEMPLATE_PATH = Path(".temp/read_path.patched.md")


def normalize_template_for_binary(template_text: str) -> bytes:
    return patch_read_path_template.normalize_template_for_binary(template_text)


def build_patched_template(template_text: str) -> str:
    return patch_read_path_template.build_patched_template(template_text)


def _matched_newline_bytes(match: probe_read_path_block.ReadPathBlockMatch) -> str:
    return "\r\n" if b"\r\n" in match.matched_bytes else "\n"


def _pad_linux_lf_block_if_needed(
    *, patched_block: bytes, expected_length: int, newline: str
) -> bytes:
    length_delta = expected_length - len(patched_block)
    if newline == "\n" and length_delta == 2:
        # Linux release binaries currently embed an LF-normalized template.
        # The human-readable patch text is equal-length under CRLF, but LF loses
        # two bytes because the injected scope header adds two line breaks.
        return patched_block + b"  "
    return patched_block


def patch_executable_copy(
    *,
    exe_path: Path,
    template_path: Path,
    output_path: Path,
    candidate_output_path: Path | None = None,
) -> probe_read_path_block.ReadPathBlockMatch:
    template_text = template_path.read_text(encoding="utf-8")
    patched_text = build_patched_template(template_text)
    original_match = probe_read_path_block.locate_read_path_block(exe_path, template_path)
    newline = _matched_newline_bytes(original_match)
    patched_block = probe_read_path_block.normalize_template_for_binary(
        patched_text, newline=newline
    )
    patched_block = _pad_linux_lf_block_if_needed(
        patched_block=patched_block,
        expected_length=original_match.length,
        newline=newline,
    )

    if len(patched_block) != original_match.length:
        raise ValueError(
            "Patched block length mismatch: "
            f"expected {original_match.length} bytes, got {len(patched_block)}"
        )

    if candidate_output_path is not None:
        candidate_output_path.write_text(patched_text, encoding="utf-8", newline="\n")

    shutil.copyfile(exe_path, output_path)
    with output_path.open("r+b") as handle:
        handle.seek(original_match.start_offset)
        handle.write(patched_block)

    return original_match


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Patch the embedded read_path.md block in a codex executable copy."
    )
    parser.add_argument(
        "--exe",
        default=str(probe_read_path_block.DEFAULT_EXE_PATH),
        help="Path to the input codex executable.",
    )
    parser.add_argument(
        "--template",
        default=str(probe_read_path_block.DEFAULT_TEMPLATE_PATH),
        help="Path to the upstream read_path.md template file.",
    )
    parser.add_argument(
        "--output-exe",
        default=str(DEFAULT_OUTPUT_EXE_PATH),
        help="Path for the patched executable copy.",
    )
    parser.add_argument(
        "--output-template",
        default=str(DEFAULT_OUTPUT_TEMPLATE_PATH),
        help="Path for the generated merged read_path candidate.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exe_path = Path(args.exe)
    template_path = Path(args.template)
    output_path = Path(args.output_exe)
    candidate_output_path = Path(args.output_template)

    match = patch_executable_copy(
        exe_path=exe_path,
        template_path=template_path,
        output_path=output_path,
        candidate_output_path=candidate_output_path,
    )
    payload = {
        "input_exe": str(exe_path),
        "output_exe": str(output_path),
        "template_path": str(template_path),
        "output_template": str(candidate_output_path),
        "start_offset": match.start_offset,
        "start_offset_hex": match.start_offset_hex,
        "end_offset_inclusive": match.end_offset_inclusive,
        "end_offset_inclusive_hex": match.end_offset_inclusive_hex,
        "length": match.length,
        "length_hex": match.length_hex,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    for key in (
        "input_exe",
        "output_exe",
        "template_path",
        "output_template",
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
