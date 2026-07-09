# #!/usr/bin/env bash
# set -euo pipefail

# source ~/.bashrc
# conda activate verl

# RAY_PORT=$((MASTER_PORT - 10))
# HEAD_IP="${MASTER_ADDR}"

# # IP(,)
# LOCAL_IP=$(hostname -I | awk '{print $1}')

# echo "[Info] PET_NODE_RANK=${PET_NODE_RANK}, HEAD_IP=${HEAD_IP}, LOCAL_IP=${LOCAL_IP}, RAY_PORT=${RAY_PORT}"

# ray stop -f || true
# sleep 2
# rm -rf /tmp/ray || true

# if [ "${PET_NODE_RANK}" -eq 0 ]; then
# echo "[Ray] Starting HEAD at ${LOCAL_IP}:${RAY_PORT} (connect address = ${HEAD_IP}:${RAY_PORT})"
# ray start \
# --head \
# --node-ip-address="${LOCAL_IP}" \
# --port="${RAY_PORT}" \
# --dashboard-host=0.0.0.0

# # gcs / raylet
# sleep 3
# ray status || true

# # head ()
# bash cheese/training/qwen14_grpo.sh
# else
# echo "[Ray] Starting WORKER, connecting to ${HEAD_IP}:${RAY_PORT}, my ip = ${LOCAL_IP}"
# ray start \
# --address="${HEAD_IP}:${RAY_PORT}" \
# --node-ip-address="${LOCAL_IP}" \
# --block
# fi

#!/usr/bin/env bash
set -euo pipefail

source ~/.bashrc
conda activate verl
cd cheese/training

RAY_PORT=$((MASTER_PORT - 10))
HEAD_IP="${MASTER_ADDR}"
LOCAL_IP=$(hostname -I | awk '{print $1}')

#: 2 2, 4 4
EXPECTED_NODES=${EXPECTED_NODES:-6}
WAIT_SEC=${WAIT_SEC:-18000} # 15
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

 # (Alive EXPECTED_NODES)
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
 bash cheese/training/qwen14_grpo.sh

else
 echo "[Ray] Starting WORKER, connecting to ${HEAD_IP}:${RAY_PORT}, my ip = ${LOCAL_IP}"
 ray start \
 --address="${HEAD_IP}:${RAY_PORT}" \
 --node-ip-address="${LOCAL_IP}" \
 --block
fi
