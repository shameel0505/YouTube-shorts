import subprocess
import os

def test_veo_t2v():
    print("🎬 Testing Google Veo Text-to-Video via gflow-cli...")
    
    # Ensure output directory exists
    os.makedirs("output/experiments", exist_ok=True)
    
    # Prompt for a highly cinematic YouTube Shorts (9:16) scene
    prompt = "A lone astronaut standing on the edge of a massive, glowing canyon on an alien world, staring up at a gigantic, swirling purple nebula in the night sky. Epic space odyssey, cinematic, IMAX 70mm, hyper-realistic, awe-inspiring."
    
    print(f"Prompt: {prompt}")
    print("This will take 60-180 seconds and will consume ~1 Google Flow credit...")
    
    import dotenv
    dotenv.load_dotenv()
    
    # We use the creative-director tool to enhance the prompt automatically!
    # Pass the Gemini key so the tool can work, and turn off headless mode so we can see the crash
    env = os.environ.copy()
    env["GFLOW_CLI_GEMINI_API_KEY"] = env.get("GEMINI_API_KEY", "")
    env["GFLOW_CLI_HEADLESS"] = "0"
    
    cmd = [
        "gflow", "video", "t2v", prompt,
        "--aspect", "9:16",
        "--tool", "creative-director:style=cinematic",
        "--profile", "youtube",
        "--out-dir", "./output/experiments"
    ]
    
    try:
        # Run the command and capture output to the terminal
        subprocess.run(cmd, env=env, check=True)
        print("✅ Success! Check the ./output/experiments folder for your new video.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Generation failed with exit code: {e.returncode}")
        print("Did you run setup_gflow.sh and authenticate first?")
        
if __name__ == "__main__":
    # Ensure we run this from the venv
    test_veo_t2v()
