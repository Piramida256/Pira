#!/bin/bash

LOG1="/root/.pm2/logs/cysic-prover-error.log"
LOG2="/root/.pm2/logs/cysic-prover-out.log"

PROVER_PID=""
TAIL_PID=""

start_prover() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') Starting host_cuda_prover..."
    RUST_LOG=info ./host_cuda_prover &
    PROVER_PID=$!
    echo "$(date '+%Y-%m-%d %H:%M:%S') PID: $PROVER_PID"
}

kill_prover() {
    if [ -n "$PROVER_PID" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Stopping host_cuda_prover..."
        kill "$PROVER_PID" 2>/dev/null
        wait "$PROVER_PID" 2>/dev/null
    fi
}

cleanup() {
    echo ""
    echo "$(date '+%Y-%m-%d %H:%M:%S') Caught Ctrl+C, cleaning up..."

    kill_prover

    if [ -n "$TAIL_PID" ]; then
        kill "$TAIL_PID" 2>/dev/null
    fi

    exit 0
}

# trap Ctrl+C
trap cleanup SIGINT

start_prover

# run tail in background
tail -n0 -F "$LOG1" "$LOG2" &
TAIL_PID=$!

# process logs
tail -n0 -F "$LOG1" "$LOG2" | while read line
do
    if echo "$line" | grep -q "start setup service"; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Detected 'start setup service'"

        sleep 8

        kill_prover

        while ss -ltn sport = :3000 | grep -q ':3000'; do
            sleep 0.5
        done

        sleep 1
        start_prover
    fi
done