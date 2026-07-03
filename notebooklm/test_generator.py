import asyncio
import os
from notebooklm import NotebookLMClient
from dotenv import load_dotenv

load_dotenv()

async def test_video_generation():
    print("Testing NotebookLM Video Generation...")
    notebook_id = os.environ.get("NOTEBOOKLM_NOTEBOOK_ID")
    
    if not notebook_id or notebook_id == "your-notebook-id-here":
        print("Error: Please set a valid NOTEBOOKLM_NOTEBOOK_ID in your .env file.")
        return

    # Initialize the client (automatically uses the ~/.notebooklm/profiles/default/storage_state.json)
    try:
        async with NotebookLMClient.from_storage() as client:
            print(f"Connected successfully! Using Notebook ID: {notebook_id}")
            
            # Start generating the video
            status = await client.artifacts.generate_cinematic_video(
                notebook_id,
                instructions="Cinematic documentary style, moody atmospheric lighting, photorealistic imagery."
            )
            print(f"Video generation started (Task ID: {status.task_id}). Waiting for completion... (This can take 3-10 minutes)")
            
            # Wait for it to finish
            await client.artifacts.wait_for_completion(notebook_id, status.task_id)
            
            # Download the result
            output_file = "notebook_cinematic_test_output.mp4"
            await client.artifacts.download_video(notebook_id, output_file)
            print(f"\nSuccess! Video saved as '{output_file}' in the current directory.")
            
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(test_video_generation())
