---
name: python-env-setup
description: Sets up Python virtual environments with uv (never conda/miniconda/mamba) for two kinds of projects — (1) lightweight CPU-only environments with no torch/GPU dependencies, and (2) GPU-accelerated environments needing torch/torchvision/torchaudio matched to the machine's NVIDIA driver CUDA ceiling. Always use this skill when the user asks to set up a Python project or venv, initialize a uv project, install PyTorch/torch/CUDA, or mentions deep learning / GPU training setup. Also use it any time the user reports torch installing the CPU-only build despite having a GPU, `torch.cuda.is_available()` returning False, torch silently reverting to CPU after installing another package, or numpy/torch version conflicts (e.g. "A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x", "Numpy is not available"). Do not use conda, miniconda, or mamba for any part of this — uv only.
---

# Python Environment Setup (uv-based)

## Overview

This skill creates Python environments with `uv` and, for GPU projects, pins PyTorch
to the correct CUDA build so it never silently falls back to a CPU-only wheel — the
single most common failure mode in this workflow. It also resolves numpy/torch
version conflicts.

Two reference files back this skill:
- `references/pytorch-cuda-compatibility.md` — torch ⇄ CUDA wheel-tag matrix, driver/CUDA
  compatibility, and how to look up the *current* matrix live (versions ship every few months,
  so don't rely purely on memorized numbers).
- `references/numpy-torch-compatibility.md` — which numpy major version each torch
  release requires.

Read the relevant reference file before writing any install command — do not guess
CUDA tags or numpy pins from memory.

## Step 1 — Ask which environment type is needed

If it isn't already obvious from context, ask the user directly (one short question):

> "Does this project need PyTorch / GPU support, or is it a plain CPU-only environment
> (no torch, no CUDA)?"

If a tappable-choice tool is available in this client, offer exactly two options:
**"CPU-only (no torch)"** and **"GPU / PyTorch (CUDA)"**. Otherwise just ask in plain text.
Don't ask anything else up front — everything else (CUDA version, torch version) is
detected or looked up, not asked.

## Step 2 — Confirm uv is installed, never conda

```bash
uv --version || curl -LsSf https://astral.sh/uv/install.sh | sh
```

If you find an existing `environment.yml`, `conda`/`miniconda` references, or an active
conda env in the project, tell the user you're migrating dependency management to uv and
proceed — do not create or extend a conda environment, even if one already exists.

Initialize the project (skip if a `pyproject.toml` already exists):

```bash
uv init --python 3.11   # pick the Python version the user needs; ask only if truly ambiguous
```

This gives you a `pyproject.toml` and a `.venv` managed entirely by uv.

## Step 3a — CPU-only path

Nothing special is needed. Just add packages normally:

```bash
uv add numpy pandas scikit-learn ...   # whatever the user needs
```

Skip everything below about CUDA indexes — a CPU-only project should never reference
`download.pytorch.org` at all.

## Step 3b — GPU / PyTorch path

### Detect the GPU and driver's max supported CUDA version

```bash
nvidia-smi
```

The top-right of the output header shows `CUDA Version: XX.Y` — this is the **maximum**
CUDA version the installed driver supports, not necessarily the CUDA version to install.
If `nvidia-smi` isn't found, there is no usable NVIDIA GPU/driver on this machine; tell the
user and fall back to the CPU-only path (or stop and ask how they want to proceed).

(`scripts/detect_gpu.sh` wraps this check and prints `CUDA_CEILING=XX.Y` or `NO_GPU` if you
want a quick script instead of parsing `nvidia-smi` output by hand.)

### Pick the torch version and matching CUDA wheel tag

1. Open `references/pytorch-cuda-compatibility.md` for the known-good matrix and the
   general rule for picking a CUDA tag ≤ the driver's reported CUDA version.
2. Because PyTorch ships new versions every few months, **verify against the live page**
   before finalizing: web-search or fetch `https://pytorch.org/get-started/previous-versions/`
   (or `https://pytorch.org/get-started/locally/` for the newest release) to confirm the
   exact current `torch==X torchvision==Y torchaudio==Z` triple and index URL for the
   chosen CUDA tag — do not hand-assemble version numbers from memory.
3. Translate the official command into a uv command by adding `uv` in front and replacing
   `pip install` with `uv pip install` (or use the `pyproject.toml` method below for a
   persistent fix):

   ```bash
   # official site says:
   #   pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu126
   # translate to:
   uv pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu126
   ```

### Make the CUDA index permanent (prevents silent CPU fallback)

`uv pip install --index-url ...` only fixes the *current* install. The very common failure —
installing another package later, or running `uv sync`/`uv add`, silently re-resolves torch
from PyPI (which only has CPU wheels for Linux/Windows) and **replaces your GPU build with a
CPU-only build** — happens because the CUDA index was never recorded in the project. Fix this
by pinning torch (and torchvision/torchaudio) to the CUDA index inside `pyproject.toml`, not
just on the command line:

```toml
[[tool.uv.index]]
name = "pytorch-cu126"
url = "https://download.pytorch.org/whl/cu126"
explicit = true          # only torch-family packages use this index; everything else stays on PyPI

[tool.uv.sources]
torch = [{ index = "pytorch-cu126" }]
torchvision = [{ index = "pytorch-cu126" }]
torchaudio = [{ index = "pytorch-cu126" }]
```

Then run `uv add torch torchvision torchaudio` (or `uv sync`) — uv will now always resolve
these three from the pinned CUDA index, on this project, permanently. See
`references/pytorch-cuda-compatibility.md` for the macOS/CPU-fallback marker pattern if the
project must also run on machines without a GPU.

If the user only needs a one-off `uv pip install` (no `pyproject.toml`/project workflow), the
`--index-url` command above is sufficient — the persistence step is specifically for
`uv add` / `uv sync` / `uv lock` workflows.

### Resolve numpy/torch conflicts

Check `references/numpy-torch-compatibility.md` and pin numpy accordingly, e.g.:

```bash
uv add "numpy<2" torch...   # for older torch builds that require numpy 1.x
```

or leave numpy unconstrained for torch ≥2.3.1, which supports numpy 2.x.

### Verify the install actually has CUDA

Always verify after install — a "successful" `uv add`/`uv pip install` can still hand you
a CPU-only wheel if the index wasn't pinned correctly:

```bash
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.version.cuda)"
```

`torch.cuda.is_available()` must be `True` and `torch.version.cuda` must be non-`None` on a
GPU box. If it's `False`/`None`, torch resolved from PyPI instead of the CUDA index — re-check
the `[tool.uv.sources]`/`explicit = true` config above, and re-run `uv sync --reinstall-package torch`.

## Common pitfalls (checklist)

- **CPU wheel silently installed**: almost always means torch wasn't pinned to an
  `explicit = true` CUDA index in `pyproject.toml`, so a later `uv add`/`uv sync` re-resolved
  it from PyPI. Fix with the `[tool.uv.sources]` block above.
- **`nvidia-smi`'s CUDA version ≠ install command's CUDA tag**: that's expected — the
  driver-reported CUDA version is a ceiling, not a target. Pick the newest CUDA tag PyTorch
  currently ships that is ≤ that ceiling (see reference file).
- **numpy import errors after installing torch**: check
  `references/numpy-torch-compatibility.md` — older torch builds (<2.3.1) require `numpy<2`.
- **`uv add torch` with no index config picks CPU wheels on Linux/Windows**: PyPI's own
  `torch` package is CPU-only for those platforms; GPU builds only exist on
  `download.pytorch.org`, which is why the index must be configured explicitly.
- **Never use conda/miniconda/mamba** for any part of this, even if the user's machine
  already has it installed or an `environment.yml` exists — migrate to uv instead.
