# NumPy ⇄ PyTorch Compatibility Reference

NumPy 2.0 (released June 2024) changed its C API in a way that isn't ABI-compatible with
binaries compiled against NumPy 1.x. PyTorch wheels built before it adapted will crash or
error on `.numpy()` / `.from_numpy()` calls when NumPy 2.x is installed alongside them.

## Rule of thumb

| torch version | numpy requirement | Notes |
|---|---|---|
| torch ≤ 2.1.x | `numpy<2` | Installable alongside numpy 2.x, but any `.numpy()`/`.from_numpy()` call fails at runtime — not an install-time error, so it looks like it "worked" until you actually convert a tensor. |
| torch 2.2.x | `numpy<2` | Still built against the old NumPy ABI. |
| torch 2.3.0 | `numpy<2` | Still incompatible; fixed in the very next patch release. |
| torch ≥ 2.3.1 | numpy 1.x or 2.x both fine | PyTorch wheels from 2.3.1 onward are compiled against the NumPy 2.0 C API, which is backward compatible with 1.x. |
| torch ≥ 2.4 | numpy 1.x or 2.x both fine | Fully stable numpy 2.x support. |

## Typical error signatures and what they mean

- `RuntimeError: Numpy is not available` when calling `.numpy()` on a tensor →
  torch was built pre-2.3.1 and numpy 2.x is installed. Pin `numpy<2`.
- `A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x as it may crash` →
  some *other* compiled dependency (not torch itself) still needs numpy 1.x — check which
  package raised it, not just torch.
- Silent wrong results / segfaults with no clear error → worth checking numpy/torch pairing
  even if nothing explicitly complained, especially after any package upgrade.

## How to pin correctly with uv

```bash
# torch < 2.3.1
uv add "numpy<2" torch==2.1.0 ...

# torch >= 2.3.1 — no numpy pin needed, but you can still pin for reproducibility
uv add numpy torch==2.5.1 ...
```

If a *different* dependency in the project (not torch) requires `numpy<2`, that constraint
wins even if torch itself would tolerate numpy 2.x — uv's resolver will enforce the
intersection automatically as long as both constraints are declared; if you see a
resolution conflict, check which package still caps numpy and whether a newer version of
that package lifts the cap before forcing a downgrade.

## Verifying after install

```bash
uv run python -c "import numpy, torch; print('numpy', numpy.__version__); print('torch', torch.__version__); import torch; t = torch.arange(3); print(t.numpy())"
```

If the last line raises `RuntimeError: Numpy is not available`, the numpy/torch pairing is
wrong — re-check the table above.
