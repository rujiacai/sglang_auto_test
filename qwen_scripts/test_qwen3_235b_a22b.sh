ISL=6144
OSL=1024
RATIO=1.0
PORT=30000

SYS_TIME=$(date "+%Y%m%d_%H%M")

#CONCURRENCY="4 8 10 16 32 40 64 80 128"
CONCURRENCY="8 16 32"
#CONCURRENCY="200 256 512"
for CON in $CONCURRENCY; do
    if [ $CON -le 32 ]; then
      PROMPTS=64
    elif [ $CON -le 128 ]; then
      PROMPTS=256
    else
      PROMPTS=$((CON * 2))
    fi
    LOG="qwen3_${SYS_TIME}_${ISL}_${OSL}_${CON}"
    python3 -m sglang.bench_serving \
	    --dataset-name random \
	    --dataset-path /data/ShareGPT_V3_unfiltered_cleaned_split.json \
	    --model /data/models/Qwen3-235B-A22B \
	    --random-input-len $ISL \
	    --random-output-len $OSL \
	    --num-prompt $PROMPTS \
	    --random-range-ratio $RATIO \
	    --max-concurrency $CON \
	    --host 0.0.0.0 \
	    --port $PORT \
	    --seed $(date +%s)
done 2>&1 | tee -a ${LOG}.log
