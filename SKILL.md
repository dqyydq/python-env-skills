---
name: python-env-setup
description: Create, inspect, and repair Python environments with uv only, never conda/miniconda/mamba. Use when the user asks to initialize a Python project, create a venv, install dependencies, migrate dependency management to uv, install PyTorch/torchvision/torchaudio, choose a CUDA wheel for NVIDIA GPUs, fix CPU-only torch being installed on a GPU machine, repair `torch.cuda.is_available()` returning False, prevent later `uv add`/`uv sync` from replacing CUDA torch with CPU torch, or resolve NumPy/PyTorch ABI errors such as "Numpy is not available", "_ARRAY_API not found", or "A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x".
---

# Python Environment Setup (uv)

## Core Rules

- Use `uv` for all environment and dependency work. Do not use conda, miniconda, mamba, micromamba, or system Python mutation.
- Prefer a project-local `.venv`.
- Before modifying an existing project, inspect `pyproject.toml`, `uv.lock`, `uv.toml`, `requirements*.txt`, `.python-version`, and `.venv/`; merge with existing configuration instead of overwriting it.
- For GPU/PyTorch work, do not guess version triples or CUDA tags from memory. Verify the official PyTorch command from `https://pytorch.org/get-started/locally/` or `https://pytorch.org/get-started/previous-versions/`, then translate `pip install ...` to `uv pip install ...`.
- For persistent projects, do not rely only on a one-off `--index-url`; pin torch-family packages to an explicit uv index in `pyproject.toml`.
- After any dependency change, run verification. GPU environments must prove that `torch.version.cuda` is not `None` and, when an NVIDIA GPU is available, `torch.cuda.is_available()` is `True`.

## First Decision

If the environment type is not obvious, ask one concise question:

```text
Should this be a CPU-only Python environment, or an NVIDIA GPU / PyTorch CUDA environment?
```

If the project directory, Python version, dependency source, target PyTorch version, or CUDA backend is already clear from context or local files, do not ask again. Otherwise gather only the missing values.

## Inspection

Run read-only checks before changing anything:

```bash
uv --version
uv python list
python --version
```

For a richer report, use:

```bash
python scripts/inspect_env.py --project .
```

For GPU work also run:

```bash
nvidia-smi
nvidia-smi --query-gpu=name,driver_version,compute_cap --format=csv,noheader
```

`nvidia-smi` reports the maximum CUDA version supported by the driver. It is a ceiling, not the CUDA toolkit version to install.

## CPU-Only Workflow

Create or reuse the uv environment:

```bash
uv venv --python 3.11
```

For project mode:

```bash
uv init --python 3.11
uv add <packages>
uv lock
uv sync
```

Do not add PyTorch or a PyTorch index unless the user explicitly asks for CPU PyTorch. If they do, use the official CPU index and exact official package versions.

## NVIDIA GPU / PyTorch Workflow

Read `references/pytorch-cuda-compatibility.md` before selecting a backend. If NumPy or binary-extension errors are relevant, also read `references/numpy-torch-compatibility.md`. For repair cases, read `references/troubleshooting.md`.

1. Detect the NVIDIA driver ceiling with `nvidia-smi`.
2. Choose a PyTorch version and only one of the CUDA wheel tags officially published for that exact version.
3. Prefer the newest official CUDA wheel tag that is not newer than the driver ceiling.
4. Translate the official PyTorch command mechanically:

```bash
uv pip install torch==<T> torchvision==<V> torchaudio==<A> --index-url https://download.pytorch.org/whl/<backend>
```

Do not run bare `uv add torch`, bare `uv pip install torch`, or `pip install torch` in GPU mode.

## Persistent CUDA Index Pin

For any project that will later use `uv add`, `uv lock`, `uv sync`, or repeated dependency changes, write the CUDA index into `pyproject.toml`:

```toml
[[tool.uv.index]]
name = "pytorch-cu126"
url = "https://download.pytorch.org/whl/cu126"
explicit = true

[tool.uv.sources]
torch = [{ index = "pytorch-cu126" }]
torchvision = [{ index = "pytorch-cu126" }]
torchaudio = [{ index = "pytorch-cu126" }]
```

Then pin the exact torch, torchvision, and torchaudio versions in `[project].dependencies`, run `uv lock --dry-run`, then `uv lock` and `uv sync`.

If the project already has `[tool.uv.sources]` or `[[tool.uv.index]]`, merge entries carefully. Do not create duplicate tables or remove private indexes.

## Simple venv / requirements Protection

When the project is intentionally not using `pyproject.toml`, create a constraint file such as `constraints-accelerator.txt`:

```text
torch==<T>
torchvision==<V>
torchaudio==<A>
numpy<2
```

Install later dependencies with:

```bash
uv pip install --dry-run -c constraints-accelerator.txt <package>
uv pip install -c constraints-accelerator.txt <package>
```

Avoid broad `--upgrade`. Do not uninstall or replace PyTorch just to install a model package.

## NumPy Strategy

Use `references/numpy-torch-compatibility.md` for the exact reasoning. Conservative defaults:

- `torch <= 2.1`: use `numpy<2`.
- `torch 2.2.x` to `2.4.x`: prefer `numpy<2` unless the project explicitly needs NumPy 2 and passes tests.
- Newer torch versions can usually use `numpy>=1.26,<3`, but old OpenCV, SciPy, audio/video libraries, or custom C/C++ extensions may still require `numpy<2`.
- Common fallback: `numpy==1.26.4`, but it supports Python 3.9 through 3.12. If Python 3.13 needs NumPy 1.x, use Python 3.12 or 3.11.

## Guard and Verify

Before installing a risky new package in a GPU environment:

```bash
uv run python scripts/torch_guard.py snapshot --backend cu126
```

After the change:

```bash
uv run python scripts/torch_guard.py check
```

Always run:

```bash
uv pip check
uv pip tree
```

GPU verification:

```bash
uv run python - <<'PY'
import numpy as np
import torch

print("torch", torch.__version__)
print("torch CUDA build", torch.version.cuda)
print("CUDA available", torch.cuda.is_available())
print("NumPy", np.__version__)

x = np.arange(6, dtype=np.float32).reshape(2, 3)
t = torch.from_numpy(x)
assert np.array_equal(x, t.cpu().numpy())

if torch.version.cuda is None:
    raise SystemExit("CPU wheel detected; expected CUDA wheel")
if not torch.cuda.is_available():
    raise SystemExit("CUDA wheel is installed, but no CUDA device is currently available")
print("GPU", torch.cuda.get_device_name(0))
PY
```

## Optional Helper

For a guided local setup, use:

```bash
python scripts/create_uv_env.py
```

This helper is intentionally conservative and uses an offline compatibility snapshot. When internet access is available, refresh the PyTorch command from the official PyTorch pages before running GPU installs.

## Completion Report

Report the environment type, project directory, Python version, uv commands run, package versions, CUDA backend, `torch.version.cuda`, GPU name when available, `uv pip check` result, and the exact command the user should use for future dependency additions.
