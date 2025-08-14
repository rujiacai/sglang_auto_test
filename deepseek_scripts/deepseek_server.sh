SGLANG_USE_AITER=1 \
python3 -m sglang.launch_server \
--model-path /data/models/DeepSeek-R1/ \
--port 30000 \
--host 0.0.0.0 \
--served-model-name deepseek-r1 \
--tp-size 8 \
--trust-remote-code \
--chunked-prefill-size 130172 \
--max-running-requests 128 \
--mem-fraction-static 0.85 \
# --enable-torch-compile \
# --enable-ep-moe \
# --dp-size 8 \
# --enable-dp-attention \
#--moe-dense-tp-size 1
#--disable-cuda-graph \
#2>&1 | tee -a ${LOG}.log
