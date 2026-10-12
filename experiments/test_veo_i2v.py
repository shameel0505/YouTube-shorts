import subprocess
import os

def test_veo_i2v():
    print("🖼️ -> 🎬 Testing Google Veo Image-to-Video via gflow-cli...")
    
    os.makedirs("output/experiments", exist_ok=True)
    
    # Step 1: Generate the base image using Imagen 3
    image_prompt = "A futuristic cyberpunk city alleyway at night, neon lights reflecting in puddles, photorealistic"
    print(f"\n[1/2] Generating base image for prompt: '{image_prompt}'")
    
    # We run gflow image t2i. Note: Image generation is FREE (0 credits).
    img_cmd = [
        "gflow", "image", "t2i", image_prompt,
        "--aspect", "9:16",
        "--out-dir", "./output/experiments"
    ]
    
    try:
        subprocess.run(img_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Image generation failed with exit code: {e.returncode}")
        return

    # To animate the image, we would normally grab the newly created file name.
    # Since gflow-cli outputs it to the folder, let's grab the newest image in that folder.
    images = [f for f in os.listdir("output/experiments") if f.endswith(".png")]
    if not images:
        print("❌ Could not find the generated image.")
        return
        
    latest_image = max(images, key=lambda f: os.path.getctime(os.path.join("output/experiments", f)))
    image_path = os.path.join("./output/experiments", latest_image)
    
    print(f"\n✅ Base image created: {image_path}")
    
    # Step 2: Animate the image using Veo
    video_prompt = "The camera slowly pushes forward through the alleyway, neon lights flicker, rain falls"
    print(f"\n[2/2] Animating the image using Veo...")
    print(f"Video Prompt: {video_prompt}")
    
    vid_cmd = [
        "gflow", "video", "i2v", image_path, video_prompt,
        "--out-dir", "./output/experiments"
    ]
    
    try:
        subprocess.run(vid_cmd, check=True)
        print("\n✅ Success! Check the ./output/experiments folder for your new video.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Video generation failed with exit code: {e.returncode}")

if __name__ == "__main__":
    test_veo_i2v()
