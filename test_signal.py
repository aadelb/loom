import asyncio
import signal
import time

async def _shutdown():
    print("Shutting down")

def _handle_signal(sig, frame):
    print("Signal received")
    try:
        loop = asyncio.get_running_loop()
        print("Loop found")
        loop.create_task(_shutdown())
    except RuntimeError:
        print("No loop found")
        asyncio.run(_shutdown())

signal.signal(signal.SIGINT, _handle_signal)

async def main():
    print("Running loop")
    await asyncio.sleep(5)

asyncio.run(main())
