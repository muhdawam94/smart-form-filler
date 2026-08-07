"""
Add a new Groq API key to .env
Usage: python add_groq_key.py gsk_xxxxxxxxxxxxx
"""
import sys
import os

def add_key(new_key):
    new_key = new_key.strip()
    if not new_key.startswith("gsk_"):
        print(f"[ERROR] Invalid key format: {new_key[:20]}...")
        print("Groq keys start with 'gsk_'")
        return False
    
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        print("[ERROR] .env file not found")
        return False
    
    with open(env_path, "r") as f:
        content = f.read()
    
    # Check if GROQ_API_KEYS exists
    if "GROQ_API_KEYS=" in content:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("GROQ_API_KEYS="):
                existing_keys = line.split("=", 1)[1].strip()
                if new_key in existing_keys.split(","):
                    print(f"[INFO] Key already exists: {new_key[:20]}...")
                    return True
                lines[i] = f"GROQ_API_KEYS={existing_keys},{new_key}"
                break
        content = "\n".join(lines)
    elif "GROQ_API_KEY=" in content:
        # Migrate from single key to multi-key
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("GROQ_API_KEY="):
                old_key = line.split("=", 1)[1].strip()
                lines[i] = f"# Single key (kept for backup)\n# GROQ_API_KEY={old_key}\nGROQ_API_KEYS={old_key},{new_key}"
                break
        content = "\n".join(lines)
    else:
        content += f"\nGROQ_API_KEYS={new_key}\n"
    
    with open(env_path, "w") as f:
        f.write(content)
    
    print(f"[OK] Added key: {new_key[:20]}...")
    
    # Count total keys
    total = len([k for k in content.split("GROQ_API_KEYS=")[1].split("\n")[0].split(",") if k.strip()])
    print(f"[OK] Total keys: {total}")
    print(f"[INFO] Bot will auto-detect new key within 60 seconds (no restart needed)")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_groq_key.py <groq_api_key>")
        print("Get free keys at: https://console.groq.com/keys")
        sys.exit(1)
    
    add_key(sys.argv[1])
