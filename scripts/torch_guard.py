#!/usr/bin/env python3
"""Snapshot and verify that a CUDA PyTorch environment was not replaced."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

STATE_FILE = ".torch-env-lock.json"


def collect() -> dict[str, Any]:
    data: dict[str, Any] = {"python": sys.version.split()[0]}
    try:
        import numpy as np

        data["numpy"] = np.__version__
    except Exception as exc:
        data["numpy_error"] = repr(exc)

    try:
        import torch

        data.update(
            {
                "torch": torch.__version__,
                "torch_cuda_build": torch.version.cuda,
                "cuda_available": torch.cuda.is_available(),
                "gpu_name": torch.cuda.get_device_name(0)
                if torch.cuda.is_available()
                else None,
            }
        )
    except Exception as exc:
        data["torch_error"] = repr(exc)

    for name in ("torchvision", "torchaudio"):
        try:
            module = __import__(name)
            data[name] = module.__version__
        except Exception as exc:
            data[f"{name}_error"] = repr(exc)
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot")
    snap.add_argument("--backend", required=True, help="cpu, cu126, cu128, ...")
    snap.add_argument("--state", default=STATE_FILE)

    check = sub.add_parser("check")
    check.add_argument("--state", default=STATE_FILE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state_path = Path(args.state)
    current = collect()

    if args.command == "snapshot":
        expected = {"backend": args.backend, "packages": current}
        state_path.write_text(
            json.dumps(expected, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(expected, ensure_ascii=False, indent=2))
        return 0

    if not state_path.exists():
        print(f"State file not found: {state_path}", file=sys.stderr)
        return 3

    expected = json.loads(state_path.read_text(encoding="utf-8"))
    backend = str(expected.get("backend", ""))
    old = expected.get("packages", {})
    problems: list[str] = []

    for key in ("torch", "torchvision", "torchaudio"):
        if old.get(key) != current.get(key):
            problems.append(f"{key}: expected {old.get(key)!r}, got {current.get(key)!r}")

    if backend.startswith("cu"):
        if current.get("torch_cuda_build") is None:
            problems.append("Expected a CUDA build, but torch.version.cuda is None (CPU wheel detected).")
        expected_cuda = backend.removeprefix("cu")
        expected_cuda = f"{expected_cuda[:-1]}.{expected_cuda[-1]}" if len(expected_cuda) >= 3 else expected_cuda
        actual_cuda = str(current.get("torch_cuda_build") or "")
        if actual_cuda and not actual_cuda.startswith(expected_cuda):
            problems.append(
                f"CUDA build changed: expected backend {backend}, torch reports {actual_cuda}."
            )
    elif backend == "cpu" and current.get("torch_cuda_build") is not None:
        problems.append("Expected CPU build, but a CUDA build is installed.")

    print(json.dumps({"expected": expected, "current": current, "problems": problems}, ensure_ascii=False, indent=2))
    return 2 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
