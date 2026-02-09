import importlib.util
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "run_prompt_book_loop.py"
    spec = importlib.util.spec_from_file_location("run_prompt_book_loop", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _cp(returncode: int = 0, stdout: str = "", stderr: str = ""):
    obj = MagicMock()
    obj.returncode = returncode
    obj.stdout = stdout
    obj.stderr = stderr
    return obj


class PromptBookLoopGitGuardTests(TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_guard_setup_and_cleanup_with_stash_restore(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        guard = self.mod.GitWorktreeGuard(repo_root=repo, run_id="r123")

        with patch.object(self.mod, "_stash_changes", return_value="stash@{0}") as stash_mock, patch.object(
            self.mod,
            "_run_git",
            side_effect=[
                _cp(returncode=1),  # branch check -> missing
                _cp(returncode=0),  # worktree add -b
                _cp(returncode=0),  # worktree remove
                _cp(returncode=0),  # stash pop
            ],
        ) as git_mock:
            worktree = guard.setup()
            self.assertIn("output", str(worktree))
            guard.cleanup()

        self.assertEqual(stash_mock.call_count, 1)
        self.assertGreaterEqual(git_mock.call_count, 4)
