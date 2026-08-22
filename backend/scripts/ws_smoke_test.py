"""End-to-end WS broadcast test.

Runs uvicorn, the WebSocket client AND the async refresh cycle all on the
same asyncio loop — exactly how production behaves (AsyncIOScheduler lives on
uvicorn's loop), which is what makes the broadcast thread-safe.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
import websockets

from app.main import app
from app.scheduler import refresh_cycle_async

received = []
hello_seen = asyncio.Event()
done = asyncio.Event()


async def ws_client():
    async with websockets.connect("ws://127.0.0.1:8014/ws/live-updates") as ws:
        msg = json.loads(await ws.recv())
        assert msg["type"] == "hello", msg
        print("[client] hello OK")
        hello_seen.set()
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=25))
            received.append(msg)
            print(f"[client] {msg['type']} -> {str(msg.get('payload', {}))[:80]}")
            if msg["type"] == "sync_complete":
                done.set()
                return


async def trigger():
    await hello_seen.wait()
    await asyncio.sleep(1)
    print("[test] triggering refresh_cycle_async")
    await refresh_cycle_async()


async def main():
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8014, log_level="error"))
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(5)  # let the server come up (lifespan seeds, scheduler starts)
    await asyncio.gather(ws_client(), trigger())
    server_task.cancel()


asyncio.run(main())

ok = done.is_set() and any(m["type"] == "price_update" for m in received)
print(f"[test] RESULT: received={len(received)} events, price_updates="
      f"{sum(1 for m in received if m['type']=='price_update')}, sync="
      f"{sum(1 for m in received if m['type']=='sync_complete')}")
print("[test] PASS" if ok else "[test] FAIL")
