# #!/usr/bin/env bash
# set -euo pipefail

# source ~/.bashrc
# conda activate verl

# RAY_PORT=$((MASTER_PORT - 10))
# HEAD_IP="${MASTER_ADDR}"

# # 取本机真实 IP（不同平台可能略有差异，这个一般最稳）
# LOCAL_IP=$(hostname -I | awk '{print $1}')

# echo "[Info] PET_NODE_RANK=${PET_NODE_RANK}, HEAD_IP=${HEAD_IP}, LOCAL_IP=${LOCAL_IP}, RAY_PORT=${RAY_PORT}"

# ray stop -f || true
# sleep 2
# rm -rf /tmp/ray || true

# if [ "${PET_NODE_RANK}" -eq 0 ]; then
#   echo "[Ray] Starting HEAD at ${LOCAL_IP}:${RAY_PORT} (connect address = ${HEAD_IP}:${RAY_PORT})"
#   ray start \
#     --head \
#     --node-ip-address="${LOCAL_IP}" \
#     --port="${RAY_PORT}" \
#     --dashboard-host=0.0.0.0

#   # 给 gcs / raylet 一点时间起来
#   sleep 3
#   ray status || true

#   # 只在 head 上启动训练（避免每个节点都跑一遍脚本）
#   bash /path/to/orthopilot/shr/train/qwen14_grpo.sh
# else
#   echo "[Ray] Starting WORKER, connecting to ${HEAD_IP}:${RAY_PORT}, my ip = ${LOCAL_IP}"
#   ray start \
#     --address="${HEAD_IP}:${RAY_PORT}" \
#     --node-ip-address="${LOCAL_IP}" \
#     --block
# fi

#!/usr/bin/env bash
set -euo pipefail

source ~/.bashrc
conda activate verl
cd /path/to/orthopilot/shr/train

RAY_PORT=$((MASTER_PORT - 10))
HEAD_IP="${MASTER_ADDR}"
LOCAL_IP=$(hostname -I | awk '{print $1}')

# 你期望的节点数：想等 2 就设 2，想等 4 就设 4
EXPECTED_NODES=${EXPECTED_NODES:-6}
WAIT_SEC=${WAIT_SEC:-18000}     # 最多等 15 分钟
SLEEP_SEC=${SLEEP_SEC:-5}

echo "[Info] PET_NODE_RANK=${PET_NODE_RANK}, HEAD_IP=${HEAD_IP}, LOCAL_IP=${LOCAL_IP}, RAY_PORT=${RAY_PORT}"
echo "[Info] EXPECTED_NODES=${EXPECTED_NODES}, WAIT_SEC=${WAIT_SEC}s"

ray stop -f || true
sleep 2
rm -rf /tmp/ray || true

if [ "${PET_NODE_RANK}" -eq 0 ]; then
  echo "[Ray] Starting HEAD at ${LOCAL_IP}:${RAY_PORT} (workers connect to ${HEAD_IP}:${RAY_PORT})"
  ray start \
    --head \
    --node-ip-address="${LOCAL_IP}" \
    --port="${RAY_PORT}" \
    --dashboard-host=0.0.0.0

  sleep 3
  ray status || true

  echo "[Ray] Waiting for ${EXPECTED_NODES} nodes to join..."

  # 等待所有节点注册进来（Alive 节点数达到 EXPECTED_NODES）
  EXPECTED_NODES="${EXPECTED_NODES}" WAIT_SEC="${WAIT_SEC}" SLEEP_SEC="${SLEEP_SEC}" python - <<'PY'
import os, time
import ray

expected = int(os.environ["EXPECTED_NODES"])
wait_sec = int(os.environ["WAIT_SEC"])
sleep_sec = int(os.environ["SLEEP_SEC"])

ray.init(address="auto")

t0 = time.time()
while True:
    alive = [n for n in ray.nodes() if n.get("Alive")]
    n_alive = len(alive)

    if n_alive >= expected:
        print(f"[Ray] OK: {n_alive}/{expected} nodes alive.")
        for n in alive:
            print(" -", n.get("NodeName"), n.get("NodeID"))
        break

    if time.time() - t0 > wait_sec:
        print(f"[Ray] TIMEOUT: only {n_alive}/{expected} nodes alive after {wait_sec}s.")
        for n in alive:
            print(" -", n.get("NodeName"), n.get("NodeID"))
        raise SystemExit(2)

    print(f"[Ray] Waiting... {n_alive}/{expected} alive")
    time.sleep(sleep_sec)
PY

  echo "[Ray] All nodes ready, starting training..."
  bash /path/to/orthopilot/shr/train/qwen14_grpo.sh 

else
  echo "[Ray] Starting WORKER, connecting to ${HEAD_IP}:${RAY_PORT}, my ip = ${LOCAL_IP}"
  ray start \
    --address="${HEAD_IP}:${RAY_PORT}" \
    --node-ip-address="${LOCAL_IP}" \
    --block
fi
