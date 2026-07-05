# 常见故障处理

## 1. 安装其他包后，GPU PyTorch 变成 CPU 版

检查：

```bash
uv run python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
uv pip tree
```

修复顺序：

1. 检查 `pyproject.toml` 是否把 `torch`、`torchvision`、`torchaudio` 全部固定到同一显式 CUDA 索引。
2. 检查版本是否精确配套。
3. `uv lock --dry-run` 查看谁要求改变 torch。
4. 重新锁定并同步：`uv lock && uv sync`。
5. venv 模式使用原 CUDA 命令加 `--reinstall`。

## 2. `torch.cuda.is_available()` 为 False

区分三种情况：

- `torch.version.cuda is None`：安装的是 CPU wheel，重装正确 CUDA wheel。
- `torch.version.cuda` 有值但不可用：检查 NVIDIA 驱动、容器 GPU 透传、WSL、设备权限。
- 可用但自定义扩展失败：检查本机 CUDA Toolkit、编译器和扩展构建目标；这与运行官方 wheel 是不同层次的问题。

## 3. NumPy ABI 错误

```bash
uv pip install --reinstall "numpy==1.26.4"
uv pip check
```

若 Python 3.13 无法安装 NumPy 1.26.4，创建 Python 3.12/3.11 环境，不要默认从源码编译。

## 4. `uv` 解析时想升级/降级 torch

- 在 `pyproject.toml` 使用精确版本。
- 使用 `tool.uv.sources` 将 PyTorch 包固定到显式索引。
- 不要使用全局 `--upgrade`。
- 先 `--dry-run`。
- 简单 venv 使用 `-c constraints-accelerator.txt`。

## 5. 一个第三方包强制依赖错误的 torch 版本

先检查该包元数据：

```bash
uv pip install --dry-run -c constraints-accelerator.txt <package>
```

处理选项：

1. 安装兼容的该包版本。
2. 升降 PyTorch，并重新从官方矩阵选择完整三件套。
3. 最后手段：`--no-deps` 安装该包，再手工安装其真实依赖并运行测试。

不得在未验证 API/ABI 兼容性的情况下无视严格 torch 版本要求。

## 6. 清理缓存后仍拿到错误 wheel

```bash
uv cache clean torch
uv cache clean torchvision
uv cache clean torchaudio
uv pip install --refresh --reinstall <exact trio> --index-url <official index>
```

清缓存不是第一步；先检查索引和锁文件。
