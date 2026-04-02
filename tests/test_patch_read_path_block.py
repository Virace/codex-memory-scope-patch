import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPTS_DIR / "patch_read_path_block.py"
TEMPLATE_PATCH_SCRIPT_PATH = SCRIPTS_DIR / "patch_read_path_template.py"

TEMPLATE_TEXT = """## Memory

You have access to a memory folder with guidance from prior runs. It can save
time and help you stay consistent. Use it whenever it is likely to help.

Never update memories. You can only read them.

Quick memory pass (when applicable):

  - These files are append-only `jsonl`: `session_meta.payload.id` identifies the session, `turn_context` marks turn boundaries, `event_msg` is the lightweight status stream, and `response_item` contains actual messages, tool calls, and tool outputs.
  - For efficient lookup, prefer matching the filename suffix or `session_meta.payload.id`; avoid broad full-content scans unless needed.
4. If above are not clear and you need exact commands, error text, or precise evidence, search over `rollout_path` for more evidence.
"""


def load_module():
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Script not found: {SCRIPT_PATH}")
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("patch_read_path_block", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_template_patch_module():
    if not TEMPLATE_PATCH_SCRIPT_PATH.exists():
        raise FileNotFoundError(
            f"Template patch script not found: {TEMPLATE_PATCH_SCRIPT_PATH}"
        )
    spec = importlib.util.spec_from_file_location(
        "patch_read_path_template", TEMPLATE_PATCH_SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PatchReadPathBlockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def write_text(self, name: str, content: str) -> Path:
        path = self.root / name
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    def test_build_patched_template_rewrites_scope_and_preserves_binary_length(self) -> None:
        module = load_module()
        template_patch_module = load_template_patch_module()
        template_path = self.write_text("read_path.md", TEMPLATE_TEXT)

        patched_text = module.build_patched_template(
            template_path.read_text(encoding="utf-8")
        )

        self.assertIn(
            "This section applies only to Codex-managed global memory under {{ base_path }}.",
            patched_text,
        )
        self.assertIn(
            "Never update Codex-managed memory under {{ base_path }}. You can only read it.",
            patched_text,
        )
        self.assertIn(
            "  - These files are append-only `jsonl`: `session_meta.payload.id` is the session id, `turn_context` marks turns, and `response_item` contains messages, tool calls, and tool outputs.",
            patched_text,
        )
        self.assertIn(
            "4. If you still need exact commands, errors, or evidence, inspect `rollout_path` next.",
            patched_text,
        )

        original_block = module.normalize_template_for_binary(TEMPLATE_TEXT)
        patched_block = module.normalize_template_for_binary(patched_text)
        self.assertEqual(len(original_block), len(patched_block))
        self.assertEqual(
            patched_text,
            template_patch_module.build_patched_template(TEMPLATE_TEXT),
        )

    def test_patch_executable_copy_replaces_embedded_block_without_resizing_file(self) -> None:
        module = load_module()
        template_patch_module = load_template_patch_module()
        template_path = self.write_text("read_path.md", TEMPLATE_TEXT)
        original_block = module.normalize_template_for_binary(TEMPLATE_TEXT)
        prefix = b"prefix-bytes:"
        suffix = b":suffix-bytes"
        exe_path = self.root / "codex.exe"
        exe_path.write_bytes(prefix + original_block + suffix)
        output_path = self.root / "codex-patched.exe"
        candidate_path = self.root / "read_path.patched.md"

        result = module.patch_executable_copy(
            exe_path=exe_path,
            template_path=template_path,
            output_path=output_path,
            candidate_output_path=candidate_path,
        )

        self.assertEqual(exe_path.stat().st_size, output_path.stat().st_size)
        patched_bytes = output_path.read_bytes()
        self.assertEqual(result.start_offset, len(prefix))
        self.assertIn(
            module.normalize_template_for_binary(candidate_path.read_text(encoding="utf-8")),
            patched_bytes,
        )
        self.assertNotIn(original_block, patched_bytes)
        self.assertEqual(
            candidate_path.read_text(encoding="utf-8"),
            template_patch_module.build_patched_template(TEMPLATE_TEXT),
        )

    def test_patch_executable_copy_supports_linux_lf_embedded_block(self) -> None:
        module = load_module()
        template_patch_module = load_template_patch_module()
        template_path = self.write_text("read_path.md", TEMPLATE_TEXT)
        original_block = TEMPLATE_TEXT.replace("\r\n", "\n").replace("\r", "\n").encode(
            "utf-8"
        )
        prefix = b"prefix-bytes:"
        suffix = b":suffix-bytes"
        exe_path = self.root / "codex-linux"
        exe_path.write_bytes(prefix + original_block + suffix)
        output_path = self.root / "codex-linux-patched"
        candidate_path = self.root / "read_path.linux.patched.md"

        result = module.patch_executable_copy(
            exe_path=exe_path,
            template_path=template_path,
            output_path=output_path,
            candidate_output_path=candidate_path,
        )

        patched_text = template_patch_module.build_patched_template(TEMPLATE_TEXT)
        patched_block = patched_text.replace("\r\n", "\n").replace("\r", "\n").encode(
            "utf-8"
        )
        padded_block = patched_block.rstrip(b"\n") + b"  \n"
        output_bytes = output_path.read_bytes()

        self.assertEqual(exe_path.stat().st_size, output_path.stat().st_size)
        self.assertEqual(result.start_offset, len(prefix))
        self.assertIn(padded_block, output_bytes)
        self.assertNotIn(original_block, output_bytes)
        self.assertEqual(candidate_path.read_text(encoding="utf-8"), patched_text)

    def test_patch_executable_copy_fails_when_template_patch_loses_equal_length(self) -> None:
        module = load_module()
        template_path = self.write_text(
            "read_path.md",
            TEMPLATE_TEXT.replace(
                "4. If above are not clear and you need exact commands, error text, or precise evidence, search over `rollout_path` for more evidence.\n",
                "",
            ),
        )
        exe_path = self.root / "codex.exe"
        exe_path.write_bytes(b"placeholder")
        output_path = self.root / "codex-patched.exe"

        with self.assertRaisesRegex(ValueError, "Expected exactly one match"):
            module.patch_executable_copy(
                exe_path=exe_path,
                template_path=template_path,
                output_path=output_path,
            )


if __name__ == "__main__":
    unittest.main()
