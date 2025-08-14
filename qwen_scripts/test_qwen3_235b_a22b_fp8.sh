#!/bin/bash
export MODEL=Qwen3-235B-A22B-FP8
python3 -m sglang.bench_serving --backend sglang \
  --model /data/models/$MODEL \
  --dataset-name random \
  --dataset-path /data/ShareGPT_V3_unfiltered_cleaned_split.json \
  --random-input 4096 \
  --random-output 1 \
  --random-range-ratio 1 \
  --num-prompts 100 \
  --output-file "result/qwen3_prefill.jsonl" \
  --request-rate 5 \
  --seed $(date +%s) \
  --max-concurrency 8