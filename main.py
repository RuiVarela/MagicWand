from core import *

async def main():
    keep_running = True

    while keep_running:
        core = Core()

        await core.pump()

        keep_running = core.restart


if __name__ == "__main__":
    asyncio.run(main())
