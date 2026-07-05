# python-env-setup

一个用于 Codex / OpenAI Agents 的 Python 环境配置 skill，专注于使用 `uv` 创建和维护 Python 虚拟环境，并正确处理 PyTorch、CUDA 与 NumPy 之间最容易出错的依赖关系。

该 skill 的核心目标是：避免在有 NVIDIA GPU 的机器上误装 PyTorch CPU-only wheel，避免后续 `uv add` / `uv sync` 把 GPU 版 torch 静默替换回 CPU 版，并在旧版 PyTorch 与 NumPy 2.x 冲突时给出正确的约束。

## 适用场景

- 初始化 Python 项目或虚拟环境
- 使用 `uv` 管理依赖，而不是 conda / miniconda / mamba
- 安装 PyTorch、torchvision、torchaudio
- 根据本机 NVIDIA 驱动支持的 CUDA 上限选择合适的 PyTorch CUDA wheel
- 修复 `torch.cuda.is_available()` 返回 `False`
- 修复 torch 被重新解析成 CPU-only build 的问题
- 处理 NumPy 2.x 与旧版 PyTorch 的 ABI 兼容问题

## 目录结构

```text
python-env-setup/
├── SKILL.md
├── references/
│   ├── numpy-torch-compatibility.md
│   └── pytorch-cuda-compatibility.md
└── scripts/
    └── detect_gpu.sh
```

文件说明：

- `SKILL.md`：skill 主说明文件，定义触发条件和完整工作流。
- `references/pytorch-cuda-compatibility.md`：PyTorch、CUDA wheel tag、驱动 CUDA 上限和 uv 持久化配置参考。
- `references/numpy-torch-compatibility.md`：NumPy 1.x / 2.x 与不同 PyTorch 版本的兼容关系。
- `scripts/detect_gpu.sh`：辅助检测 NVIDIA GPU 和驱动支持的 CUDA 上限。

## 安装到 Codex

将整个目录复制或克隆到 Codex skills 目录中：

```powershell
git clone https://github.com/dqyydq/python-env-skills.git $env:USERPROFILE\.codex\skills\python-env-setup
```

如果你使用的是其他 `CODEX_HOME`，请放到对应的 skills 目录下：

```powershell
git clone https://github.com/dqyydq/python-env-skills.git $env:CODEX_HOME\skills\python-env-setup
```

安装后，Codex 会通过 `SKILL.md` 的 frontmatter 自动识别该 skill。

## 使用方式

在 Codex 中直接提出与 Python 环境相关的需求即可，例如：

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

## 工作流概览

该 skill 会指导 Codex 按以下流程处理环境：

1. 判断项目是 CPU-only 环境，还是需要 PyTorch / CUDA。
2. 使用 `uv` 初始化项目和管理依赖。
3. GPU 项目先检测 `nvidia-smi`，读取驱动支持的 CUDA 上限。
4. 根据 PyTorch 官方页面确认当前可用的 torch / torchvision / torchaudio 版本和 CUDA wheel tag。
5. 将 PyTorch CUDA index 写入 `pyproject.toml`，避免后续同步时回退到 CPU wheel。
6. 根据 PyTorch 版本决定是否需要 pin `numpy<2`。
7. 安装后运行验证命令，确认 CUDA 版 torch 生效。

## uv 与 PyTorch CUDA 的关键配置

对于需要 GPU 的项目，不能只临时执行一次带 `--index-url` 的安装命令。更稳妥的方式是把 PyTorch CUDA wheel index 固化到 `pyproject.toml`：

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

然后再运行：

```bash
uv add torch torchvision torchaudio
```

安装完成后验证：

```bash
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.version.cuda)"
```

在支持 CUDA 的 NVIDIA GPU 机器上，期望结果是：

- `torch.cuda.is_available()` 为 `True`
- `torch.version.cuda` 不是 `None`

## 重要原则

- 只使用 `uv`，不使用 conda、miniconda 或 mamba。
- CPU-only 项目不配置 PyTorch CUDA index。
- GPU 项目不要凭记忆填写 CUDA tag，需要查看 PyTorch 官方当前版本信息。
- `nvidia-smi` 显示的 CUDA Version 是驱动支持的上限，不等于必须安装的 CUDA 版本。
- `uv pip install --index-url ...` 适合一次性安装；项目长期维护应使用 `pyproject.toml` 的 `[tool.uv.sources]` 固定来源。
- 旧版 PyTorch 可能需要 `numpy<2`，具体见 `references/numpy-torch-compatibility.md`。

## 发布说明

这个仓库是一个 skill 源目录，不是普通 Python 包。它不需要通过 `pip install` 安装，也不要求包含 `setup.py`、`pyproject.toml` 或包入口文件。只要目录中包含有效的 `SKILL.md`，并放置在 Codex 可发现的 skills 路径下即可使用。
