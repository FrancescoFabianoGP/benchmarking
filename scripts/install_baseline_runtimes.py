from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_ROOT = ROOT / ".baseline_envs"
UV_CACHE_DIR = ROOT / ".uv-cache"
PYTHON_VERSION = "3.11"
ZEUS_PYTHON_VERSION = "3.13"
METAGPT_HOME = ENV_ROOT / "metagpt-home"


@dataclass(frozen=True)
class FrameworkSpec:
    framework_id: str
    env_dir: Path
    editable_installs: list[Path]
    python_version: str = PYTHON_VERSION
    extra_packages: list[str] = field(default_factory=list)


FRAMEWORK_SPECS = {
    "langgraph": FrameworkSpec(
        framework_id="langgraph",
        env_dir=ENV_ROOT / "langgraph",
        editable_installs=[
            ROOT / "baselines" / "langgraph" / "libs" / "sdk-py",
            ROOT / "baselines" / "langgraph" / "libs" / "checkpoint",
            ROOT / "baselines" / "langgraph" / "libs" / "prebuilt",
            ROOT / "baselines" / "langgraph" / "libs" / "langgraph",
        ],
    ),
    "autogen": FrameworkSpec(
        framework_id="autogen",
        env_dir=ENV_ROOT / "autogen",
        editable_installs=[
            ROOT / "baselines" / "autogen" / "python" / "packages" / "autogen-core",
            ROOT / "baselines" / "autogen" / "python" / "packages" / "autogen-agentchat",
            ROOT / "baselines" / "autogen" / "python" / "packages" / "autogen-ext",
        ],
        extra_packages=[
            "openai>=1.93",
            "tiktoken>=0.8.0",
            "aiofiles",
        ],
    ),
    "metagpt": FrameworkSpec(
        framework_id="metagpt",
        env_dir=ENV_ROOT / "metagpt",
        editable_installs=[
            ROOT / "baselines" / "metagpt",
        ],
    ),
    "zeus": FrameworkSpec(
        framework_id="zeus",
        env_dir=ENV_ROOT / "zeus",
        editable_installs=[
            ROOT / "GP_components" / "zeus-service" / "growth-protocol-ai-sdk",
            ROOT / "GP_components" / "zeus-service",
        ],
        python_version=ZEUS_PYTHON_VERSION,
    ),
}

BASELINE_TO_FRAMEWORK = {
    "single_agent_data_analyst": "langgraph",
    "react_agent": "autogen",
    "autogen_multi_agent": "autogen",
    "metagpt_sop_agent": "metagpt",
    "multi_agent_analyst_coder_critic": "metagpt",
    "gp_zeus_venue_risk": "zeus",
}


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(UV_CACHE_DIR)
    return env


def _run(cmd: list[str]) -> None:
    print(f"+ {shlex.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT, env=_subprocess_env())


def install_framework(spec: FrameworkSpec, recreate: bool = False) -> None:
    ENV_ROOT.mkdir(parents=True, exist_ok=True)
    UV_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _run(["uv", "python", "install", spec.python_version])
    env_python = spec.env_dir / "bin" / "python"
    if recreate or not env_python.exists():
        venv_cmd = ["uv", "venv", str(spec.env_dir), "--python", spec.python_version]
        if recreate:
            venv_cmd.append("--clear")
        _run(venv_cmd)
    else:
        print(f"= Reusing existing virtualenv at {spec.env_dir}", flush=True)
    install_cmd = [
        "uv",
        "pip",
        "install",
        "--python",
        str(env_python),
    ]
    for path in spec.editable_installs:
        install_cmd.extend(["-e", str(path)])
    install_cmd.extend(spec.extra_packages)
    _run(install_cmd)
    if spec.framework_id == "metagpt":
        config_dir = METAGPT_HOME / ".metagpt"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config2.yaml").write_text(
            '\n'.join(
                [
                    "llm:",
                    '  api_type: "openai"',
                    '  model: "local-noop-model"',
                    '  base_url: "https://api.openai.com/v1"',
                    '  api_key: "local-noop-key"',
                ]
            )
            + "\n",
            encoding="utf-8",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install repo-local framework runtimes for external benchmark baselines."
    )
    parser.add_argument(
        "--framework",
        action="append",
        choices=sorted(FRAMEWORK_SPECS),
        help="Install one or more framework runtimes directly.",
    )
    parser.add_argument(
        "--baseline",
        action="append",
        choices=sorted(BASELINE_TO_FRAMEWORK),
        help="Install the framework runtime needed by one or more baseline IDs.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Install all known framework runtimes.",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate any existing framework virtualenvs before installing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_frameworks: set[str] = set()

    if args.all or (not args.framework and not args.baseline):
        selected_frameworks.update(FRAMEWORK_SPECS)
    if args.framework:
        selected_frameworks.update(args.framework)
    if args.baseline:
        selected_frameworks.update(BASELINE_TO_FRAMEWORK[baseline] for baseline in args.baseline)

    for framework_id in sorted(selected_frameworks):
        install_framework(FRAMEWORK_SPECS[framework_id], recreate=args.recreate)


if __name__ == "__main__":
    main()
