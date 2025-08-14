#!/bin/bash
CONCURRENCY="4 8 16 32"
for CON in $CONCURRENCY; do
    PROMPTS=$((CON * 10))
    python3 -m sglang.bench_serving \
        --dataset-name random \
        --dataset-path /data/ShareGPT_V3_unfiltered_cleaned_split.json \
        --model /data/models/DeepSeek-R1/ \
        --random-input-len 4096 \
        --random-output-len 2048  \
        --num-prompt $PROMPTS \
        --random-range-ratio 1 \
        --max-concurrency $CON \
        --warmup-requests $CON \
        --seed $(date +%s) \
        --output-file "result/deepseek.jsonl"
done
