# python-env-setup

Codex / OpenAI Agents skill for creating, inspecting, and repairing Python environments with `uv`.

It focuses on the failure modes that usually cost the most time:

- accidentally installing CPU-only PyTorch on a machine with an NVIDIA GPU
- later `uv add` / `uv sync` replacing CUDA torch with CPU torch
- choosing a CUDA wheel tag that the installed driver cannot support
- mixing older PyTorch or binary extensions with NumPy 2.x
- modifying an existing project without preserving its `pyproject.toml`, `uv.lock`, indexes, and constraints

Only `uv` is used. Conda, miniconda, mamba, and micromamba are intentionally out of scope.

## Contents

```text
python-env-setup/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── numpy-torch-compatibility.md
│   ├── pytorch-cuda-compatibility.md
│   └── troubleshooting.md
└── scripts/
    ├── create_uv_env.py
    ├── detect_gpu.sh
    ├── inspect_env.py
    └── torch_guard.py
```

## Install

Clone the repository into your Codex skills directory:

```powershell
git clone https://github.com/dqyydq/python-env-skills.git $env:USERPROFILE\.codex\skills\python-env-setup
```

If `CODEX_HOME` is set, use that skills directory instead:

```powershell
git clone https://github.com/dqyydq/python-env-skills.git $env:CODEX_HOME\skills\python-env-setup
```

## Example prompts

```text
帮我用 uv 初始化这个 Python 项目
```

```text
帮我安装 GPU 版 PyTorch，并确认 torch.cuda.is_available() 是 True
```

```text
我有 NVIDIA 显卡，但安装 torch 后只能跑 CPU，帮我修一下
```

```text
安装依赖后报 RuntimeError: Numpy is not available，帮我处理 NumPy 和 torch 的版本冲突
```

## Workflow summary

The skill guides Codex to:

1. Decide whether the project is CPU-only or NVIDIA GPU / PyTorch CUDA.
2. Inspect the existing project before changing files.
3. Use `uv` to create or reuse a local `.venv`.
4. For GPU environments, verify the official PyTorch version trio and CUDA index before installing.
5. Persist PyTorch CUDA sources in `pyproject.toml` using `[[tool.uv.index]]` and `[tool.uv.sources]` with `explicit = true`.
6. Protect simpler venv / requirements workflows with constraints.
7. Validate with `uv pip check`, `uv pip tree`, NumPy interop, and CUDA availability checks.

## Helper scripts

`scripts/inspect_env.py` prints a read-only JSON report for uv, Python, project files, NVIDIA driver state, and installed torch/numpy packages.

```bash
python scripts/inspect_env.py --project .
```

`scripts/torch_guard.py` snapshots a known-good torch installation and checks whether later dependency changes replaced it.

```bash
uv run python scripts/torch_guard.py snapshot --backend cu126
uv run python scripts/torch_guard.py check
```

`scripts/create_uv_env.py` is an interactive helper for creating a CPU or GPU environment. Its PyTorch compatibility matrix is a conservative offline snapshot; when internet access is available, confirm the final GPU install command against the official PyTorch pages first.

```bash
python scripts/create_uv_env.py
```

## Key uv / PyTorch CUDA config

For durable GPU projects, do not rely only on a one-time `--index-url`. Persist the accelerator index:

```toml
[[tool.uv.index]]
name = "pytorch-cu130"
url = "https://download.pytorch.org/whl/cu130"
explicit = true

[tool.uv.sources]
torch = [{ index = "pytorch-cu130" }]
torchvision = [{ index = "pytorch-cu130" }]
torchaudio = [{ index = "pytorch-cu130" }]
```

Then pin the exact torch, torchvision, and torchaudio versions and run:

```bash
uv lock --dry-run
uv lock
uv sync
```

## Notes

This repository is a skill source directory, not a Python package. It does not need `pip install`, `setup.py`, or package entry points. Codex discovers it from the `SKILL.md` frontmatter when the directory is placed under a skills path.
