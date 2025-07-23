#!/bin/bash
export MODEL=Qwen3-235B-A22B-FP8
SGLANG_USE_AITER=1 \
python3 -m sglang.launch_server \
  --model-path /data/models/$MODEL/ \
  --port 30000 \
  --host 0.0.0.0 \
  --served-model-name $MODEL \
  --max-prefill-tokens 32768 --chunked-prefill-size 32768  \
  --context-len 32768 \
  --max-running-requests 512 \
  --tp 8 --trust-remote-code \
  --disable-radix-cache --page-size 64 \
  --enable-ep-moe
