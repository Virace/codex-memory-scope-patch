import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "patch-release-binary.yml"
README_PATH = ROOT / "README.md"


class PatchReleaseBinaryWorkflowTests(unittest.TestCase):
    def test_workflow_exists_and_wires_two_layer_patch_steps(self) -> None:
        self.assertTrue(WORKFLOW_PATH.exists(), f"Workflow not found: {WORKFLOW_PATH}")

        content = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", content)
        self.assertIn("release_tag:", content)
        self.assertIn("upstream_release_tag", content)
        self.assertIn("codex-x86_64-pc-windows-msvc.exe", content)
        self.assertIn(
            "raw.githubusercontent.com/openai/codex/${{ needs.prepare-release.outputs.upstream_release_tag }}/codex-rs/core/templates/memories/read_path.md",
            content,
        )
        self.assertIn("python scripts/patch_read_path_template.py", content)
        self.assertIn("python scripts/patch_read_path_block.py", content)
        self.assertIn("actions/upload-artifact", content)
        self.assertIn("codex-x86_64-unknown-linux-gnu", content)
        self.assertIn("patched_release_tag", content)
        self.assertIn("prerelease: true", content)

    def test_readme_mentions_release_binary_patch_path(self) -> None:
        content = README_PATH.read_text(encoding="utf-8")

        self.assertIn("patch-release-binary", content)
        self.assertIn("codex-x86_64-pc-windows-msvc.exe", content)
        self.assertIn("codex-x86_64-unknown-linux-gnu", content)
        self.assertIn("read_path.md", content)
        self.assertIn("patched-", content)


if __name__ == "__main__":
    unittest.main()
