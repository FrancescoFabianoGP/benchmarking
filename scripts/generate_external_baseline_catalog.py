from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from harness.external_baseline_repos import write_external_repo_catalog
from harness.external_baseline_wrappers import wrapper_manifest


def main() -> None:
    repo_catalog_path = ROOT / "cases" / "coaction_venue_risk" / "external_repo_catalog.json"
    wrapper_manifest_path = ROOT / "cases" / "coaction_venue_risk" / "external_wrapper_manifest.json"

    write_external_repo_catalog(repo_catalog_path)
    wrapper_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with wrapper_manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(wrapper_manifest(), handle, indent=2)

    print(
        json.dumps(
            {
                "external_repo_catalog": str(repo_catalog_path),
                "external_wrapper_manifest": str(wrapper_manifest_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
