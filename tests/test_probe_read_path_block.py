import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "probe_read_path_block.py"
)


def load_module():
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Script not found: {SCRIPT_PATH}")
    spec = importlib.util.spec_from_file_location("probe_read_path_block", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ProbeReadPathBlockTests(unittest.TestCase):
    def write_temp_file(self, name: str, content: bytes) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / name
        path.write_bytes(content)
        return path

    def write_temp_text_file(self, name: str, content: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / name
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    def test_locates_unique_normalized_template_block(self) -> None:
        module = load_module()
        template_text = (
            "## Memory\n\n"
            "Never update memories. You can only read them.\n\n"
            "- {{ base_path }}/MEMORY.md\n"
            "deep repo exploration.\n"
        )
        template_path = self.write_temp_text_file("read_path.md", template_text)
        normalized = module.normalize_template_for_binary(template_text)
        prefix = b"prefix-bytes:"
        suffix = b":suffix-bytes"
        exe_path = self.write_temp_file("codex.exe", prefix + normalized + suffix)

        block = module.locate_read_path_block(exe_path, template_path)

        self.assertEqual(block.start_offset, len(prefix))
        self.assertEqual(block.end_offset_inclusive, len(prefix) + len(normalized) - 1)
        self.assertEqual(block.length, len(normalized))
        self.assertEqual(block.matched_bytes, normalized)

    def test_raises_when_normalized_template_is_missing(self) -> None:
        module = load_module()
        template_path = self.write_temp_text_file(
            "read_path.md", "## Memory\nNever update memories. You can only read them.\n"
        )
        exe_path = self.write_temp_file("codex.exe", b"not present here")

        with self.assertRaisesRegex(ValueError, "Expected exactly one embedded block match"):
            module.locate_read_path_block(exe_path, template_path)

    def test_raises_when_normalized_template_appears_multiple_times(self) -> None:
        module = load_module()
        template_text = "## Memory\nNever update memories. You can only read them.\n"
        template_path = self.write_temp_text_file("read_path.md", template_text)
        normalized = module.normalize_template_for_binary(template_text)
        exe_path = self.write_temp_file(
            "codex.exe", b"AA" + normalized + b"BB" + normalized + b"CC"
        )

        with self.assertRaisesRegex(ValueError, "Expected exactly one embedded block match"):
            module.locate_read_path_block(exe_path, template_path)


if __name__ == "__main__":
    unittest.main()
