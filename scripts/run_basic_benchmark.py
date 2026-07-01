from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.env_loader import load_local_env

load_local_env()

from harness.benchmark_runner import run_benchmark


def main() -> None:
    result = run_benchmark(
        benchmark_id="coaction_venue_risk",
        baseline_id="all",
        report_dir=ROOT / "reports" / "basic_benchmark",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
