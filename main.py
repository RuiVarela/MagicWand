from core import *

async def main():
    keep_running = True

    while keep_running:
        core = Core()

        await core.setup()
        await core.pump()
        await core.teardown()

        keep_running = core.restart

        if keep_running:
            print("Restarting server")


if __name__ == "__main__":
    asyncio.run(main())
