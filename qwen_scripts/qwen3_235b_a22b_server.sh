SGLANG_USE_AITER=0 \
python3 -m sglang.launch_server \
--model-path /data/models/Qwen3-235B-A22B/ \
--port 30000 \
--host 0.0.0.0 \
--served-model-name Qwen3-235B-A22B \
--tp-size 8 \
--trust-remote-code \
--chunked-prefill-size 130172 \
--max-running-requests 128 \
--mem-fraction-static 0.85 \
--dp-size 8 \
--enable-dp-attention \
--enable-ep-moe \
--enable-torch-compile \
