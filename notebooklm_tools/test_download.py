import asyncio
import os
from notebooklm import NotebookLMClient
from dotenv import load_dotenv

load_dotenv()

async def download_existing_video():
    notebook_id = "350d2f17-bd86-4290-94c6-810df4eff3a2"
    task_id = "028e5cda-c2ad-4d5f-8592-bde72ed42227"
    
    print(f"Connecting to NotebookLM to check on Video Task {task_id}...")

    try:
        async with NotebookLMClient.from_storage() as client:
            print("Checking status... (Will wait up to 15 more minutes if it is still generating)")
            
            # Wait for it to finish with a longer timeout
            # The previous run timed out at 300s, let's give it 900s
            await client.artifacts.wait_for_completion(notebook_id, task_id, timeout=900.0)
            
            # Download the result
            output_file = "notebook_cinematic_test_output.mp4"
            print("Video is ready! Downloading...")
            await client.artifacts.download_video(notebook_id, output_file)
            print(f"\nSuccess! Video saved as '{output_file}' in the current directory.")
            
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(download_existing_video())
