#!/usr/bin/env python3
"""
天锋PRO 守护进程
每5分钟心跳写入 /tmp/tianfeng-daemon.txt
检查 tianfeng status 返回正常
简单的"我还活着"健康检查
"""
import os
import subprocess
import sys
import time
import logging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.expanduser("~/lgox-ops/logs")
HEARTBEAT_FILE = "/tmp/tianfeng-daemon.txt"
TIANFENG_CLI = os.path.expanduser("~/bin/tianfeng")
INTERVAL = 300  # 5 minutes

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TIANFENG-DAEMON] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, "tianfeng-daemon.log")),
    ],
)
logger = logging.getLogger(__name__)


def write_heartbeat():
    """Write heartbeat timestamp to /tmp/tianfeng-daemon.txt"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(HEARTBEAT_FILE, "w") as f:
        f.write(f"heartbeat: {timestamp}\n")


def check_health() -> bool:
    """Run tianfeng status and check it returns normally"""
    try:
        result = subprocess.run(
            [sys.executable, TIANFENG_CLI, "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("Health check OK")
            return True
        else:
            logger.warning(
                "Health check returned code %d: %s",
                result.returncode,
                result.stderr[:200],
            )
            return False
    except subprocess.TimeoutExpired:
        logger.error("Health check timed out after 30s")
        return False
    except FileNotFoundError:
        logger.error("tianfeng CLI not found at %s", TIANFENG_CLI)
        return False
    except Exception as e:
        logger.error("Health check exception: %s", e)
        return False


def main():
    logger.info("天锋PRO daemon starting (interval=%ds)", INTERVAL)

    while True:
        try:
            write_heartbeat()
            check_health()
        except Exception as e:
            logger.error("Unexpected error in main loop: %s", e)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
