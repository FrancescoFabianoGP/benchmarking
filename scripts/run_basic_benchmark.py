from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from harness.coaction_benchmark import run_initial_benchmark


def main() -> None:
    result = run_initial_benchmark(
        baseline_id="all",
        report_dir=ROOT / "reports" / "basic_benchmark",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
