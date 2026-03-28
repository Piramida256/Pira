#!/usr/bin/env python3
import requests
import json
import time
import statistics
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from flask import Flask, send_file
import threading

# ========= НАСТРОЙКИ =========
GRAPHQL_URL = "https://hasura.cysic.xyz/v1/graphql"
UPDATE_INTERVAL = 10
MAX_BIDS = 1200
WEI = 10**18
PORT = 5000
# =============================

app = Flask(__name__)

all_bids = []
seen_hashes = set()
last_height = 0


# ========= GRAPHQL =========

def gql(query, variables=None):
    try:
        r = requests.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables or {}},
            timeout=15
        )
        return r.json()
    except:
        return None


def extract_bids(transactions):
    bids = []

    for tx in transactions:
        messages = tx.get("messages")

        if isinstance(messages, str):
            try:
                messages = json.loads(messages)
            except:
                continue

        if not messages:
            continue

        for msg in messages:
            t = msg.get("@type") or msg.get("type", "")

            if "MsgMatch" in t:
                b = msg.get("bid_price") or (
                    msg.get("value", {}).get("bid_price")
                    if isinstance(msg.get("value"), dict)
                    else None
                )

                if b:
                    try:
                        bids.append(int(b) / WEI)
                    except:
                        pass

    return bids


def init():
    global last_height
    d = gql("query{transaction(order_by:{height:desc},limit:1){height}}")
    if d and "data" in d:
        last_height = int(d["data"]["transaction"][0]["height"])


def fetch():
    global last_height

    query = """
    query($h: bigint!) {
      transaction(where:{height:{_gt:$h}}, order_by:{height:asc}) {
        hash
        height
        messages
      }
    }
    """

    d = gql(query, {"h": str(last_height)})
    if not d or "data" not in d:
        return

    for tx in d["data"]["transaction"]:
        h = int(tx["height"])
        if h > last_height:
            last_height = h

        if tx["hash"] in seen_hashes:
            continue

        seen_hashes.add(tx["hash"])

        bids = extract_bids([tx])
        if bids:
            now = datetime.now().strftime("%H:%M:%S")
            for b in bids:
                all_bids.append((b, now))

                if len(all_bids) > MAX_BIDS:
                    all_bids.pop(0)


# ========= GRAPH =========

def plot():
    if len(all_bids) < 2:
        return

    bids = [v for v, _ in all_bids]
    times = [t for _, t in all_bids]

    plt.figure(figsize=(12, 5))
    plt.plot(bids)

    # средняя линия
    if len(bids) >= 10:
        mean = statistics.mean(bids[-10:])
        plt.axhline(mean, linestyle='--')

    step = max(1, len(times)//10)
    plt.xticks(range(0, len(times), step), times[::step], rotation=45)

    plt.title("LIVE Bid Graph (last 1200)")
    plt.xlabel("Time")
    plt.ylabel("Bid")

    plt.tight_layout()
    plt.savefig("bid_graph.png")
    plt.close()


# ========= LOOP =========

def worker():
    init()
    print("📡 Graph server started...")

    while True:
        fetch()
        plot()
        time.sleep(UPDATE_INTERVAL)


# ========= WEB =========

@app.route("/")
def graph():
    return send_file("bid_graph.png", mimetype='image/png')


def run_web():
    app.run(host="0.0.0.0", port=PORT)


# ========= MAIN =========

if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    run_web()
