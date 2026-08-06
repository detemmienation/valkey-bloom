#!/usr/bin/env python3
"""
Interactive TopK Demo for final presentation.
Shows each command, waits for Enter, then executes via valkey-cli and prints raw output.

Usage:
    python3 demo.py
"""

import subprocess
import time
import os
import sys
import signal
import atexit

# ─── Config ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_BIN = os.path.join(SCRIPT_DIR, "tests/build/binaries/unstable/valkey-server")
CLI_BIN = os.path.join(SCRIPT_DIR, "tests/build/binaries/unstable/valkey-cli")
MODULE_PATH = os.path.join(SCRIPT_DIR, "target/release/libvalkey_bloom.so")
PORT = 7399

# ─── Server lifecycle ─────────────────────────────────────────────────────────
server_proc = None

def cleanup():
    global server_proc
    if server_proc:
        server_proc.terminate()
        server_proc.wait()
        print("\n[server stopped]")

atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

def start_server():
    global server_proc
    cmd = [
        SERVER_BIN,
        "--port", str(PORT),
        "--loadmodule", MODULE_PATH,
        "--save", "",
        "--daemonize", "no",
        "--loglevel", "warning",
    ]
    server_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    print(f"[valkey-server started on port {PORT}, module loaded]")

# ─── CLI execution ────────────────────────────────────────────────────────────

def cli(*args):
    """Execute a command via valkey-cli with formatted output (numbered, typed)."""
    cmd = [CLI_BIN, "-p", str(PORT), "--no-raw"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.rstrip("\n")

def cli_pipe(commands):
    """Execute multiple commands via valkey-cli pipe mode (for bulk loading).
    Each command is a string like 'TOPK.INCRBY key item 5 item2 3'."""
    input_data = "\n".join(commands) + "\n"
    cmd = [CLI_BIN, "-p", str(PORT), "--pipe"]
    subprocess.run(cmd, input=input_data, capture_output=True, text=True)

# ─── Interactive helpers ──────────────────────────────────────────────────────

def wait():
    """Wait for user to press Enter."""
    input()

def section(title):
    """Print a section header and wait."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    wait()

def run(cmd_str):
    """Display a command, wait for Enter, execute via valkey-cli, wait again, print result."""
    print(f"\n> {cmd_str}")
    wait()
    args = cmd_str.split()
    output = cli(*args)
    print(output)
    wait()
    return output

def comment(text):
    """Print a comment/explanation line."""
    print(f"\n# {text}")

# ─── Demo scenarios ───────────────────────────────────────────────────────────

def demo_basic():
    """Scenario 1: Small k with basic commands and eviction"""
    # section("Scenario 1: Basic Commands & Eviction (k=3)")
    cli("FLUSHALL")

    comment("Create a TopK sketch: track top 3, width=50, depth=4, decay=0.9")
    run("TOPK.RESERVE fruits 3 50 4 0.9")

    comment("Add items")
    run("TOPK.ADD fruits apple banana cherry apple apple banana")

    comment("List current top-k with counts")
    run("TOPK.LIST fruits WITHCOUNT")

    comment("INCRBY: add 'durian' and evict the lowest")
    run("TOPK.INCRBY fruits durian 10")

    comment("Top-k after eviction: cherry is evicted")
    run("TOPK.LIST fruits WITHCOUNT")

    comment("Query membership")
    run("TOPK.QUERY fruits apple durian cherry")

    comment("Count: estimated frequency for each item")
    run("TOPK.COUNT fruits apple durian cherry")

    comment("Info: sketch parameters and stats")
    run("TOPK.INFO fruits")


def demo_large_k():
    """Scenario 2: Large k with eviction"""
    section("Scenario 2: Large K with Eviction (k=10)")
    cli("FLUSHALL")

    comment("Create a TopK sketch: track top 10")
    run("TOPK.RESERVE trending 10 256 5 0.9")

    comment("Add trending topics with view counts")
    run("TOPK.INCRBY trending AI 9000 Python 7500 Rust 6000 Docker 4800 Linux 4200")
    run("TOPK.INCRBY trending AWS 3500 Redis 3000 Kafka 2400 React 1800 SQL 1200")

    comment("Current top-10")
    run("TOPK.LIST trending WITHCOUNT")

    comment("A new topic 'Bitcoin' goes viral with 20000 views")
    run("TOPK.INCRBY trending Bitcoin 20000")

    comment("Top-10 after: Bitcoin is #1, lowest item evicted")
    run("TOPK.LIST trending WITHCOUNT")

    comment("Multiple new topics spike at once")
    run("TOPK.INCRBY trending Valkey 15000 TopK 12000 ElastiCache 10000")

    comment("Updated top-10 - new entries pushed out cold ones")
    run("TOPK.LIST trending WITHCOUNT")

    comment("Query: which topics are still tracked?")
    run("TOPK.QUERY trending AI Bitcoin SQL Valkey Go")

    comment("Count: estimated frequency")
    run("TOPK.COUNT trending Bitcoin AI Valkey SQL")

    comment("Info")
    run("TOPK.INFO trending")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not os.path.exists(SERVER_BIN):
        print(f"ERROR: valkey-server not found at {SERVER_BIN}")
        sys.exit(1)
    if not os.path.exists(CLI_BIN):
        print(f"ERROR: valkey-cli not found at {CLI_BIN}")
        sys.exit(1)
    if not os.path.exists(MODULE_PATH):
        print(f"ERROR: module not found at {MODULE_PATH}")
        print("Run: cargo build --release")
        sys.exit(1)

    start_server()

    try:
        demo_basic()
        # demo_large_k()
    finally:
        print("\n" + "=" * 60)
        print("  Demo complete!")
        print("=" * 60)
