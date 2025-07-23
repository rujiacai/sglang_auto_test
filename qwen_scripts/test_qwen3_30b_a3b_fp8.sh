#!/bin/bash
export MODEL=Qwen3-30B-A3B-FP8
python3 -m sglang.bench_serving --backend sglang \
  --model /data/models/$MODEL \
  --dataset-name random \
  --dataset-path /data/ShareGPT_V3_unfiltered_cleaned_split.json \
  --random-input 4096 \
  --random-output 1 \
  --random-range-ratio 1 \
  --num-prompts 1
