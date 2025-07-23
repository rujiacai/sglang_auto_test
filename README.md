# sctipts
单个test
```bash
python3 run_sglang_test.py --start-script ./qwen3_235b_a22b_fp8_server.sh --test-scripts ./test_qwen3_235b_a22b_fp8.sh ./test_gsm8k.sh
```
多个任务test
```bash
python3 run_multi_sglang_tests.py --config test_config.json --report test_report.json
```