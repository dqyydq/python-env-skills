# PyTorch ⇄ CUDA Compatibility Reference

PyTorch ships a new minor/patch version roughly every 2–3 months, and drops support for
old CUDA wheel tags while adding new ones. **This table is a snapshot for orientation, not
a source of truth.** Before finalizing an install command, verify the exact current
versions and tags by checking (via web search / fetch):

- `https://pytorch.org/get-started/locally/` — current stable release, all CUDA tags
- `https://pytorch.org/get-started/previous-versions/` — every past release + exact
  `torch==X torchvision==Y torchaudio==Z --index-url ...` command for each

## How to pick the right CUDA tag

1. Run `nvidia-smi`. The header shows `CUDA Version: XX.Y` — this is the **maximum** CUDA
   toolkit version the installed *driver* supports. It is not the CUDA version you must
   install; it's a ceiling.
2. Pick the **newest CUDA wheel tag that PyTorch currently publishes which is ≤ that
   ceiling**. Installing a wheel built for an older CUDA than the driver supports is fine
   (backward compatible); installing one built for a newer CUDA than the driver supports
   will fail or silently not use the GPU.
3. If unsure or the driver is old, prefer the second-newest tag (e.g. cu121 instead of
   cu126) — driver/toolkit edge cases are common on older cloud images.

## Snapshot matrix (recent releases, verify before use)

| torch version | torchvision | torchaudio | CUDA tags available | numpy requirement |
|---|---|---|---|---|
| 2.11.0 | 0.26.0 | 2.11.0 | cu126, cu128, cu130, rocm7.2 | numpy 2.x |
| 2.6.0 | 0.21.0 | 2.6.0 | cu118, cu124, cu126 | numpy 2.x |
| 2.5.1 / 2.5.0 | 0.20.x | 2.5.x | cu118, cu121, cu124 | numpy 2.x |
| 2.4.1 / 2.4.0 | 0.19.x | 2.4.x | cu118, cu121, cu124 | numpy 2.x |
| 2.3.x | 0.18.x | 2.3.x | cu118, cu121 | numpy<2 for 2.3.0; numpy 2.x OK from 2.3.1 |
| 2.1.x / 2.0.x | 0.16.x / 0.15.x | 2.1.x / 2.0.x | cu117, cu118, cu121 | numpy<2 required |
| ≤1.13 | — | — | cu116, cu117 | numpy<2 required |

CPU-only wheels exist for every torch version at `--index-url https://download.pytorch.org/whl/cpu`.
ROCm (AMD) tags exist for recent versions at `.../whl/rocmX.Y` — same uv-pinning pattern applies.

## uv command translation

Whatever command the PyTorch site gives you, translate mechanically:

```bash
# site says:
pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu126
# uv one-off install:
uv pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu126
```

For project-based workflows (`uv add`, `uv sync`, `uv lock`), a one-off `--index-url` isn't
persistent — the next `uv sync` can silently re-resolve torch from PyPI and downgrade it to
a CPU wheel. Pin it permanently in `pyproject.toml` instead:

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

`explicit = true` is important: without it, uv may also start pulling unrelated packages
from the PyTorch index if PyPI is unreachable or a version isn't found there, which is
almost never what you want.

### Cross-platform projects (GPU on Linux, CPU on macOS)

PyTorch doesn't publish CUDA wheels for macOS. Use environment markers so the same
`pyproject.toml` works everywhere:

```toml
[[tool.uv.index]]
name = "pytorch-cu126"
url = "https://download.pytorch.org/whl/cu126"
explicit = true

[tool.uv.sources]
torch = [
    { index = "pytorch-cu126", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
torchvision = [
    { index = "pytorch-cu126", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
```

On macOS, torch/torchvision fall through to plain PyPI (CPU-only, which is the only option
Apple Silicon has anyway — MPS acceleration is built into the standard wheel).

### Switchable CPU/GPU builds via extras (advanced)

If the same project needs to support both a CPU-only variant and a specific CUDA variant
(e.g. CI runs CPU, dev machines run GPU), use `[project.optional-dependencies]` + a
`conflicts` table — see the "Using uv with PyTorch" guide at docs.astral.sh/uv for the full
extras-based pattern. Only reach for this if the user explicitly needs both variants from
one repo; for a single-purpose environment, the plain `[tool.uv.sources]` pin above is
simpler and preferred.

### Quick shortcut: `--torch-backend=auto`

Newer uv versions support `uv pip install torch --torch-backend=auto`, which detects the
installed CUDA/ROCm driver and picks the matching backend automatically. This only works
with the `uv pip` interface (not `uv add`/`uv sync`/`uv lock`), so it's convenient for a
quick one-off install but does not replace the `pyproject.toml` pinning above for a project
that will be `uv sync`'d again later — always still add the persistent pin for anything
that isn't a throwaway environment.
