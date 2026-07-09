cd /path/to/orthopilot/agent/ortho_agent-fathom
python3 /path/to/orthopilot/agent/ortho_agent-fathom/ortho_agent_trajectory/trajectory_enhancer_r1.py \
  --distill-with-gt \
  --input-dir data/轨迹构建/T1/example \
  --output-jsonl data/轨迹构建/T1/output/search_r1_1203.jsonl \
  --model-url http://YOUR_HOST:YOUR_PORT \
  --executors http://YOUR_HOST:YOUR_PORT

reasoning model
anwser-only sft
