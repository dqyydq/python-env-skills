#!/usr/bin/env bash
# Detect NVIDIA GPU presence and the driver's max-supported CUDA version.
# Usage: bash detect_gpu.sh
# Prints either "NO_GPU" or a line like "CUDA_CEILING=12.6" plus the raw nvidia-smi header.

set -euo pipefail

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "NO_GPU"
  echo "nvidia-smi not found — no usable NVIDIA driver on this machine."
  exit 0
fi

echo "---- nvidia-smi header ----"
nvidia-smi | head -n 4

CUDA_CEILING=$(nvidia-smi | grep -oP 'CUDA Version:\s*\K[0-9]+\.[0-9]+' | head -n1 || true)

if [ -z "${CUDA_CEILING:-}" ]; then
  echo "COULD_NOT_PARSE_CUDA_VERSION"
  exit 0
fi

echo "CUDA_CEILING=${CUDA_CEILING}"
echo ""
echo "This is the MAXIMUM CUDA version the installed driver supports."
echo "Pick the newest PyTorch CUDA wheel tag (cuXXX) that is <= this ceiling —"
echo "see references/pytorch-cuda-compatibility.md for the current matrix and"
echo "verify against https://pytorch.org/get-started/locally/ before installing."
