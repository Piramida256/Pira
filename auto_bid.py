import time
import subprocess
import yaml
from pathlib import Path

# === CONFIG ===
CONFIG_PATH = Path("./config.yaml")
CHECK_INTERVAL = 60                 # проверка каждые 1 минуту
IDLE_TIME_REQUIRED = 8 * 60        # GPU idle ≥ 8 минут
GPU_IDLE_THRESHOLD = 10             # GPU idle, % загрузки
BID_PERCENT_STEP = 0.06             # уменьшение bid на 6%
MIN_BID = 0.0019
PM2_PROCESS_NAME = "cysic-prover"
# =================

idle_start_time = None


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def get_gpu_utilization():
    try:
        result = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"]
        )
        return int(result.decode().strip())
    except Exception:
        return None


def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False)


def get_current_bid():
    try:
        cfg = load_config()
        return float(cfg.get("bid", 0))
    except Exception:
        return None


def restart_prover():
    log("[PM2] ******************************* Перезапуск прувера *******************************")
    subprocess.run(
        ["pm2", "restart", PM2_PROCESS_NAME],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def decrease_bid_and_restart():
    cfg = load_config()
    current_bid = float(cfg.get("bid", 0))

    new_bid = max(current_bid * (1 - BID_PERCENT_STEP), MIN_BID)
    new_bid = round(new_bid, 4)

    if new_bid < current_bid - 1e-6:
        cfg["bid"] = new_bid
        save_config(cfg)
        log(f"[BID ↓] {current_bid:.4f} → {new_bid:.4f}")
        restart_prover()
    else:
        log("[BID ↓] bid уже на минимуме")


def main():
    global idle_start_time

    log(
        "Auto-bid script started | "
        "GPU простой ≥ X минут → уменьшение bid"
    )

    while True:
        gpu_load = get_gpu_utilization()
        now = time.time()

        if gpu_load is None:
            log("[WARN] Cannot read GPU load")
            time.sleep(CHECK_INTERVAL)
            continue

        current_bid = get_current_bid()
        bid_str = f"{current_bid:.4f}" if current_bid is not None else "N/A"

        # === GPU IDLE ===
        if gpu_load <= GPU_IDLE_THRESHOLD:
            if idle_start_time is None:
                idle_start_time = now

            elapsed = int(now - idle_start_time)
            remaining = max(0, IDLE_TIME_REQUIRED - elapsed)
            remaining_min = remaining // 60

            log(
                f"[GPU] Load: {gpu_load}%, "
                f"Текущая bid: {bid_str}, "
                f"Уменьшение bid через {remaining_min} минут"
            )

            if elapsed >= IDLE_TIME_REQUIRED:
                log("[GPU] GPU простой ≥ X минут → уменьшаем bid")
                decrease_bid_and_restart()
                idle_start_time = now

                        # === GPU BUSY ===
        else:
            if idle_start_time is not None:
                log(
                    f"[GPU] Load: {gpu_load}%, "
                    f"Текущая bid: {bid_str}, "
                    f"Таймер уменьшения bid сброшен"
                )
            else:
                log(
                    f"[GPU] Load: {gpu_load}%, "
                    f"Текущая bid: {bid_str}"
                )

            idle_start_time = None

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
