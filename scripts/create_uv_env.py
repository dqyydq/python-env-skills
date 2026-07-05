#!/usr/bin/env python3
"""Interactive creator for a general CPU env or NVIDIA GPU PyTorch env.

This helper intentionally uses a conservative, offline compatibility snapshot.
The SKILL.md instructs the agent to refresh mappings from the official PyTorch
page before execution whenever internet access is available.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

MATRIX = {
    "2.11.0": {"vision": "0.26.0", "audio": "2.11.0", "cuda": ["cu126", "cu128", "cu130"]},
    "2.10.0": {"vision": "0.25.0", "audio": "2.10.0", "cuda": ["cu126", "cu128", "cu130"]},
    "2.9.1": {"vision": "0.24.1", "audio": "2.9.1", "cuda": ["cu126", "cu128", "cu130"]},
    "2.9.0": {"vision": "0.24.0", "audio": "2.9.0", "cuda": ["cu126", "cu128", "cu130"]},
    "2.8.0": {"vision": "0.23.0", "audio": "2.8.0", "cuda": ["cu126", "cu128", "cu129"]},
    "2.7.1": {"vision": "0.22.1", "audio": "2.7.1", "cuda": ["cu118", "cu126", "cu128"]},
    "2.7.0": {"vision": "0.22.0", "audio": "2.7.0", "cuda": ["cu118", "cu126", "cu128"]},
    "2.6.0": {"vision": "0.21.0", "audio": "2.6.0", "cuda": ["cu118", "cu124", "cu126"]},
    "2.5.1": {"vision": "0.20.1", "audio": "2.5.1", "cuda": ["cu118", "cu121", "cu124"]},
    "2.4.1": {"vision": "0.19.1", "audio": "2.4.1", "cuda": ["cu118", "cu121", "cu124"]},
    "2.3.1": {"vision": "0.18.1", "audio": "2.3.1", "cuda": ["cu118", "cu121"]},
    "2.2.2": {"vision": "0.17.2", "audio": "2.2.2", "cuda": ["cu118", "cu121"]},
}


def run(command: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command))
    result = subprocess.run(command, cwd=cwd, text=True, check=False)
    if check and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result


def prompt(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or (default or "")


def version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def detect_driver_cuda() -> str | None:
    if not shutil.which("nvidia-smi"):
        return None
    result = subprocess.run(["nvidia-smi"], text=True, capture_output=True, check=False)
    match = re.search(r"CUDA Version:\s*(\d+\.\d+)", result.stdout)
    return match.group(1) if match else None


def backend_number(backend: str) -> tuple[int, int]:
    digits = backend.removeprefix("cu")
    return int(digits[:-1]), int(digits[-1])


def suggest_backend(options: Iterable[str], driver_cuda: str | None) -> str:
    opts = list(options)
    if not driver_cuda:
        return opts[0]
    maximum = tuple(int(x) for x in driver_cuda.split(".")[:2])
    eligible = [item for item in opts if backend_number(item) <= maximum]
    return eligible[-1] if eligible else opts[0]


def env_python(project: Path) -> Path:
    windows = project / ".venv" / "Scripts" / "python.exe"
    unix = project / ".venv" / "bin" / "python"
    return windows if windows.exists() else unix


def parse_packages(raw: str) -> list[str]:
    return [item for item in re.split(r"[\s,]+", raw.strip()) if item]


def main() -> int:
    if not shutil.which("uv"):
        print("uv was not found in PATH. Install uv first, then rerun.", file=sys.stderr)
        return 1

    print("1. 通用 CPU 环境（默认不安装 PyTorch）")
    print("2. NVIDIA GPU / PyTorch 环境")
    mode = prompt("请选择", "1")
    if mode not in {"1", "2"}:
        print("Invalid selection", file=sys.stderr)
        return 2

    project = Path(prompt("项目目录", ".")).expanduser().resolve()
    python_version = prompt("Python 版本", "3.11")
    project.mkdir(parents=True, exist_ok=True)

    venv = project / ".venv"
    if venv.exists():
        reuse = prompt(".venv 已存在，是否复用？(y/n)", "y").lower()
        if reuse not in {"y", "yes"}:
            print("为安全起见，本脚本不会自动删除现有环境。请指定新目录。", file=sys.stderr)
            return 3
    else:
        run(["uv", "venv", "--python", python_version], project)

    (project / ".python-version").write_text(python_version + "\n", encoding="utf-8")

    if mode == "1":
        packages = parse_packages(prompt("要安装的包（空格或逗号分隔，可留空）", ""))
        if packages:
            run(["uv", "pip", "install", "--dry-run", *packages], project)
            run(["uv", "pip", "install", *packages], project)
        run(["uv", "pip", "check"], project)
        print(f"CPU environment ready: {project / '.venv'}")
        return 0

    driver_cuda = detect_driver_cuda()
    print("检测到的驱动最高 CUDA:", driver_cuda or "未检测到")
    versions = sorted(MATRIX, key=version_key, reverse=True)
    print("离线矩阵中的 PyTorch 版本:", ", ".join(versions))
    torch_version = prompt("PyTorch 版本", versions[0])
    if torch_version not in MATRIX:
        print("该版本不在离线矩阵中。请先从官方 previous-versions 页面确认后更新脚本。", file=sys.stderr)
        return 4

    item = MATRIX[torch_version]
    suggested = suggest_backend(item["cuda"], driver_cuda)
    print("该版本可用后端:", ", ".join(item["cuda"]))
    backend = prompt("CUDA wheel", suggested)
    if backend not in item["cuda"]:
        print("所选后端不是该 PyTorch 版本的官方 wheel。", file=sys.stderr)
        return 5

    numpy_choice = prompt("NumPy 策略：1=兼容优先(numpy<2), 2=现代(numpy<3)", "1")
    numpy_spec = "numpy<2" if numpy_choice == "1" else "numpy<3"

    command = [
        "uv", "pip", "install",
        f"torch=={torch_version}",
        f"torchvision=={item['vision']}",
        f"torchaudio=={item['audio']}",
        "--index-url", f"https://download.pytorch.org/whl/{backend}",
    ]
    print("将执行官方命令的 uv 版本：")
    print(" ".join(command))
    confirmed = prompt("确认执行？(y/n)", "y").lower()
    if confirmed not in {"y", "yes"}:
        print("Cancelled")
        return 0

    run(command, project)
    run(["uv", "pip", "install", numpy_spec], project)

    constraints = project / "constraints-accelerator.txt"
    constraints.write_text(
        "\n".join(
            [
                f"torch=={torch_version}",
                f"torchvision=={item['vision']}",
                f"torchaudio=={item['audio']}",
                numpy_spec,
                "",
            ]
        ),
        encoding="utf-8",
    )

    packages = parse_packages(prompt("其他项目依赖（空格或逗号分隔，可留空）", ""))
    if packages:
        dry = ["uv", "pip", "install", "--dry-run", "-c", str(constraints), *packages]
        install = ["uv", "pip", "install", "-c", str(constraints), *packages]
        run(dry, project)
        run(install, project)

    run(["uv", "pip", "check"], project)

    py = env_python(project)
    verification = r'''
import json
import numpy as np
import torch
import torchvision
import torchaudio
x = np.arange(6, dtype=np.float32).reshape(2, 3)
y = torch.from_numpy(x).cpu().numpy()
assert np.array_equal(x, y)
out = {
    "torch": torch.__version__,
    "torchvision": torchvision.__version__,
    "torchaudio": torchaudio.__version__,
    "numpy": np.__version__,
    "torch_cuda_build": torch.version.cuda,
    "cuda_available": torch.cuda.is_available(),
    "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
}
print(json.dumps(out, ensure_ascii=False))
if torch.version.cuda is None:
    raise SystemExit("CPU wheel detected; expected CUDA wheel")
'''
    result = subprocess.run([str(py), "-c", verification], cwd=project, text=True, capture_output=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode

    state = {
        "backend": backend,
        "install_command": command,
        "constraints": str(constraints),
        "verification": json.loads(result.stdout),
    }
    (project / ".torch-env-lock.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("GPU environment ready.")
    print("以后安装依赖请使用：")
    print(f"uv pip install -c {constraints.name} <package>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
