import asyncio
from notebooklm import NotebookLMClient

async def run():
    async with NotebookLMClient.from_storage() as c:
        print("sources:", [x for x in dir(c.sources) if not x.startswith("_")])
        print("notebooks:", [x for x in dir(c.notebooks) if not x.startswith("_")])

if __name__ == "__main__":
    asyncio.run(run())
