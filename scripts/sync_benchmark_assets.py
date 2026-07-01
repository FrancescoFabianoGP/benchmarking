from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COACTION_SOURCE_ROOT = (
    ROOT / "GP_components" / "zeus-service" / "app" / "workflow" / "local_db" / "coaction"
)
COACTION_TARGET_ROOT = ROOT / "cases" / "coaction_venue_risk" / "data"


def _copy_tree(source: Path, target: Path) -> list[str]:
    copied: list[str] = []
    if not source.exists():
        raise FileNotFoundError(f"Missing source directory: {source}")

    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied.append(str(destination.relative_to(ROOT)))
    return copied


def sync_coaction_assets() -> dict[str, object]:
    copied_files = _copy_tree(COACTION_SOURCE_ROOT, COACTION_TARGET_ROOT)
    manifest = {
        "benchmark_id": "coaction_venue_risk",
        "source_root": str(COACTION_SOURCE_ROOT.relative_to(ROOT)),
        "target_root": str(COACTION_TARGET_ROOT.relative_to(ROOT)),
        "copied_files": copied_files,
    }
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync benchmark-local data assets from tracked source repos."
    )
    parser.add_argument(
        "--benchmark",
        choices=["coaction_venue_risk"],
        required=True,
        help="Benchmark asset bundle to sync into cases/<benchmark>/data.",
    )
    args = parser.parse_args()

    if args.benchmark == "coaction_venue_risk":
        manifest = sync_coaction_assets()
    else:
        raise ValueError(f"Unsupported benchmark: {args.benchmark}")

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
