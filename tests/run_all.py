"""运行所有测试."""
import sys
from pathlib import Path

# 确保项目根在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import subprocess
import os


def run_all():
    tests_dir = Path(__file__).parent
    test_files = sorted(tests_dir.glob("test_*.py"))

    passed = 0
    failed = 0

    for test_file in test_files:
        print(f"\n{'='*60}")
        print(f"  Running: {test_file.name}")
        print(f"{'='*60}")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
            cwd=str(tests_dir.parent),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        if result.returncode == 0:
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
