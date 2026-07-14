import asyncio
from notebooklm.client import NotebookLMClient

async def main():
    async with NotebookLMClient.from_storage("experiments/gcp_storage_state.json") as client:
        notebooks = await client.notebooks.list()
        print(f"Success! Found {len(notebooks)} notebooks")

asyncio.run(main())
