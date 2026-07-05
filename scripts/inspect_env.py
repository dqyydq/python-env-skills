#!/usr/bin/env python3
"""Read-only inspection for uv/Python/PyTorch/NVIDIA environments."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(command: list[str], cwd: Path | None = None) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        return {
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "error": str(exc)}


def env_python(project: Path) -> Path | None:
    candidates = [
        project / ".venv" / "bin" / "python",
        project / ".venv" / "Scripts" / "python.exe",
    ]
    return next((path for path in candidates if path.exists()), None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".", help="Project directory")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    py = env_python(project)

    report: dict[str, Any] = {
        "project": str(project),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "system_python": sys.version,
        "files": {
            name: (project / name).exists()
            for name in (
                "pyproject.toml",
                "uv.lock",
                "uv.toml",
                "requirements.txt",
                ".python-version",
                ".venv",
                "constraints-accelerator.txt",
                ".torch-env-lock.json",
            )
        },
        "uv": run(["uv", "--version"], project) if shutil.which("uv") else None,
        "nvidia_smi": run(["nvidia-smi"], project) if shutil.which("nvidia-smi") else None,
        "nvidia_query": (
            run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,compute_cap",
                    "--format=csv,noheader",
                ],
                project,
            )
            if shutil.which("nvidia-smi")
            else None
        ),
        "virtualenv_python": str(py) if py else None,
    }

    if py:
        code = r'''
import json
out = {}
try:
    import numpy as np
    out["numpy"] = np.__version__
except Exception as exc:
    out["numpy_error"] = repr(exc)
try:
    import torch
    out.update({
        "torch": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    })
except Exception as exc:
    out["torch_error"] = repr(exc)
for name in ("torchvision", "torchaudio"):
    try:
        module = __import__(name)
        out[name] = module.__version__
    except Exception as exc:
        out[f"{name}_error"] = repr(exc)
print(json.dumps(out, ensure_ascii=False))
'''
        result = run([str(py), "-c", code], project)
        if result.get("returncode") == 0:
            try:
                report["environment"] = json.loads(result["stdout"])
            except json.JSONDecodeError:
                report["environment_raw"] = result
        else:
            report["environment_error"] = result

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
