import asyncio
from app.core.engine import SkyAlertAsyncEngine


def main():
    engine = SkyAlertAsyncEngine()
    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        asyncio.run(engine.shutdown())


if __name__ == "__main__":
    main()

