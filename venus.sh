#!/bin/bash
export VENUS_PROVER_GRPC_PORT=7000
export VENUS_DIR="/root/venus_v0_1_6"
export VENUS_OUT_DIR="/dev/shm/venus_tmp"
export RUST_LOG=info

mkdir -p "$VENUS_OUT_DIR"
exec ~/cysic-prover/venus_prover_server
