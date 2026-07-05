# PyTorch <-> CUDA Compatibility Reference

Snapshot date: 2026-07-05. Treat this file as orientation only. Before finalizing an install command, verify exact versions and wheel tags on the official PyTorch pages:

- `https://pytorch.org/get-started/locally/`
- `https://pytorch.org/get-started/previous-versions/`

The current official previous-versions page lists PyTorch 2.11.0 wheels for CUDA 12.6, CUDA 12.8, CUDA 13.0, ROCm 7.2, and CPU, with the trio `torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0`.

## Recent wheel snapshot

| PyTorch | torchvision | torchaudio | Official accelerator indexes |
|---|---:|---:|---|
| 2.11.0 | 0.26.0 | 2.11.0 | cu126, cu128, cu130, rocm7.2, cpu |
| 2.10.0 | 0.25.0 | 2.10.0 | cu126, cu128, cu130, rocm7.1, cpu |
| 2.9.1 | 0.24.1 | 2.9.1 | cu126, cu128, cu130, rocm6.4, cpu |
| 2.9.0 | 0.24.0 | 2.9.0 | cu126, cu128, cu130, rocm6.4, cpu |
| 2.8.0 | 0.23.0 | 2.8.0 | cu126, cu128, cu129, cpu |
| 2.7.1 | 0.22.1 | 2.7.1 | cu118, cu126, cu128, cpu |
| 2.7.0 | 0.22.0 | 2.7.0 | cu118, cu126, cu128, cpu |
| 2.6.0 | 0.21.0 | 2.6.0 | cu118, cu124, cu126, cpu |
| 2.5.1 | 0.20.1 | 2.5.1 | cu118, cu121, cu124, cpu |
| 2.4.1 | 0.19.1 | 2.4.1 | cu118, cu121, cu124, cpu |
| 2.3.1 | 0.18.1 | 2.3.1 | cu118, cu121, cpu |

## Pick a CUDA backend

1. Run `nvidia-smi` and read the header's `CUDA Version: XX.Y`. This is the maximum CUDA version the installed driver supports.
2. Pick only from the wheel tags officially published for the target PyTorch version.
3. Choose the newest official CUDA wheel tag that is not newer than the driver ceiling.
4. Do not invent tags such as `cu127` just because the machine reports CUDA 12.7.
5. PyTorch wheels usually bundle their CUDA runtime; a matching local CUDA Toolkit is only needed for compiling custom CUDA extensions.

## Translate official commands to uv

Official PyTorch command:

```bash
pip install torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cu130
```

uv one-off equivalent:

```bash
uv pip install torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cu130
```

## Persistent uv project configuration

For project workflows, configure the index permanently. uv's PyTorch guide recommends `explicit = true` so this index is used only by packages explicitly assigned to it.

```toml
[[tool.uv.index]]
name = "pytorch-cu130"
url = "https://download.pytorch.org/whl/cu130"
explicit = true

[tool.uv.sources]
torch = [{ index = "pytorch-cu130", marker = "sys_platform == 'linux' or sys_platform == 'win32'" }]
torchvision = [{ index = "pytorch-cu130", marker = "sys_platform == 'linux' or sys_platform == 'win32'" }]
torchaudio = [{ index = "pytorch-cu130", marker = "sys_platform == 'linux' or sys_platform == 'win32'" }]
```

macOS has no CUDA wheels, so use markers for cross-platform projects or fall back to PyPI on macOS.

## uv pip shortcut

Recent uv versions support automatic backend selection for the `uv pip` interface:

```bash
uv pip install torch --torch-backend=auto
```

Use it only for one-off installs or discovery. For a project that will run `uv lock` or `uv sync`, still add the persistent `[tool.uv.sources]` and `[[tool.uv.index]]` entries.
