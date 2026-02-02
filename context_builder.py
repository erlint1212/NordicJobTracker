import os

# Files to include
EXTENSIONS = {'.gd', '.tscn', '.py', '.nix'}
# Folders to ignore
IGNORE_DIRS = {'.git', '.godot', '__pycache__', '.import'}

def print_project_context():
    print("=== PROJECT DUMP START ===")
    for root, dirs, files in os.walk("."):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in EXTENSIONS:
                path = os.path.join(root, file)
                # Normalized path for clarity
                clean_path = path.replace("./", "")
                
                print(f"\n==========================================")
                print(f"FILE: {clean_path}")
                print(f"==========================================")
                
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        print(content)
                except Exception as e:
                    print(f"[Error reading file: {e}]")
                    
    print("\n=== PROJECT DUMP END ===")

if __name__ == "__main__":
    print_project_context()
