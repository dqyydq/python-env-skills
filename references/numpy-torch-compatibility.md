# NumPy <-> PyTorch Compatibility Reference

NumPy 2.0 changed its C API in June 2024. Older binary wheels, including older PyTorch releases and many third-party scientific packages, can fail at runtime even when installation succeeds.

## Conservative defaults

| PyTorch range | Default NumPy strategy | Notes |
|---|---|---|
| `torch <= 2.1` | `numpy<2` | NumPy tensor interop is not reliable with NumPy 2.x. |
| `torch 2.2.x` to `2.4.x` | Prefer `numpy<2` | Some combinations work, but older binary extensions often do not. Relax only when the project needs NumPy 2 and verification passes. |
| Newer torch | `numpy>=1.26,<3` after testing | Still prefer `numpy<2` if the project has old OpenCV, SciPy, audio/video wheels, or custom C/C++ extensions. |

Common compatibility fallback:

```text
numpy==1.26.4
```

NumPy 1.26.4 supports Python 3.9 through 3.12. If a Python 3.13 environment must use NumPy 1.x, create a Python 3.12 or 3.11 environment instead of compiling old NumPy from source by default.

## Error signatures

- `RuntimeError: Numpy is not available` during `.numpy()` / `torch.from_numpy(...)`: use `numpy<2` for older torch.
- `A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x`: some compiled dependency was built against NumPy 1.x; identify that package before changing torch.
- `_ARRAY_API not found`: usually a NumPy 2 ABI issue in a compiled extension.

## uv fixes

```bash
uv pip install --reinstall "numpy==1.26.4"
uv pip check
```

Project mode:

```bash
uv add "numpy<2"
uv lock
uv sync
```

## Verification

```bash
uv run python -c "import numpy as np, torch; x=np.arange(3); t=torch.from_numpy(x); print(np.__version__, torch.__version__, t.numpy())"
```
