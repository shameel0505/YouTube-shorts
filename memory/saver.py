import os
import subprocess

def push_memory_to_github():
    """
    Commits the memory folder to GitHub to save state across Render restarts.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("⚠️ GITHUB_TOKEN not found in environment. Cannot save memory to GitHub.")
        return False
        
    print("💾 Auto-saving memory to GitHub...")
    
    try:
        # Check if it's a git repo, if not init
        try:
            subprocess.run(["git", "status"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("   Not a git repository. Initializing...")
            subprocess.run(["git", "init"], check=True)
            subprocess.run(["git", "remote", "add", "origin", f"https://{token}@github.com/shameel0505/YouTube-shorts.git"], check=True)
            subprocess.run(["git", "fetch", "origin", "feature/spacing-logic"], check=True)
            subprocess.run(["git", "reset", "--mixed", "origin/feature/spacing-logic"], check=True)

        # 1. Configure git user (required to commit)
        subprocess.run(["git", "config", "--global", "user.name", "Render Bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "bot@render.com"], check=True)
        
        # 2. Add the token to the origin URL so we can push without SSH keys
        repo_url = f"https://{token}@github.com/shameel0505/YouTube-shorts.git"
        subprocess.run(["git", "remote", "set-url", "origin", repo_url], check=True)
        
        # 3. Add memory folder
        subprocess.run(["git", "add", "memory/"], check=True)
        
        # 4. Check if there are any changes to commit
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if "memory/" not in status.stdout:
            print("   No memory changes to save.")
            return True
            
        # 5. Commit
        subprocess.run(["git", "commit", "-m", "chore: auto-save bot memory [skip ci]"], check=True)
        
        # 6. Push to the feature branch
        subprocess.run(["git", "push", "origin", "HEAD:feature/spacing-logic"], check=True)
        
        print("   ✅ Memory successfully pushed to GitHub!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to push memory to GitHub: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during github push: {e}")
        return False

if __name__ == "__main__":
    push_memory_to_github()
