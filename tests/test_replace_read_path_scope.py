import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "replace_read_path_scope.py"
)


def load_module():
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Script not found: {SCRIPT_PATH}")
    spec = importlib.util.spec_from_file_location("replace_read_path_scope", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReplaceReadPathScopeTests(unittest.TestCase):
    def write_temp_file(self, content: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "read_path.md"
        path.write_text(content, encoding="utf-8")
        return path

    def test_resolves_current_split_memory_path_before_legacy_path(self) -> None:
        module = load_module()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        current_path = (
            root / "codex-rs" / "memories" / "read" / "templates" / "memories" / "read_path.md"
        )
        legacy_path = root / "codex-rs" / "core" / "templates" / "memories" / "read_path.md"
        current_path.parent.mkdir(parents=True)
        legacy_path.parent.mkdir(parents=True)
        current_path.write_text("current\n", encoding="utf-8")
        legacy_path.write_text("legacy\n", encoding="utf-8")

        self.assertEqual(current_path, module.resolve_default_target(root))

    def test_resolves_legacy_path_when_current_split_memory_path_is_missing(self) -> None:
        module = load_module()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        legacy_path = root / "codex-rs" / "core" / "templates" / "memories" / "read_path.md"
        legacy_path.parent.mkdir(parents=True)
        legacy_path.write_text("legacy\n", encoding="utf-8")

        self.assertEqual(legacy_path, module.resolve_default_target(root))

    def test_replaces_exact_sentence_once(self) -> None:
        module = load_module()
        path = self.write_temp_file(
            "Header\n\nNever update memories. You can only read them.\n\nFooter\n"
        )

        module.replace_read_path_scope(path)

        actual = path.read_text(encoding="utf-8")
        self.assertIn(
            "Do not directly modify Codex-managed memory artifacts under {{ base_path }} in this session.",
            actual,
        )
        self.assertIn("Treat only that Codex memory root as read-only.", actual)
        self.assertIn(
            "This restriction does not apply to unrelated project directories or other MCP-managed state unless separately instructed.",
            actual,
        )
        self.assertNotIn("Never update memories. You can only read them.", actual)

    def test_fails_when_sentence_is_missing(self) -> None:
        module = load_module()
        path = self.write_temp_file("Header only\n")

        with self.assertRaisesRegex(ValueError, "Expected exactly one match"):
            module.replace_read_path_scope(path)

    def test_fails_when_sentence_appears_multiple_times(self) -> None:
        module = load_module()
        path = self.write_temp_file(
            "\n".join(
                [
                    "Never update memories. You can only read them.",
                    "Middle",
                    "Never update memories. You can only read them.",
                ]
            )
        )

        with self.assertRaisesRegex(ValueError, "Expected exactly one match"):
            module.replace_read_path_scope(path)


if __name__ == "__main__":
    unittest.main()
