import streamlit as st
import git
import os
import tempfile
import shutil
from pathlib import Path
from gitignore_parser import parse_gitignore
from datetime import datetime, timezone
import stat
from urllib.parse import urlparse

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="GitHub Repo to LLM Context",
    page_icon="🤖",
    layout="wide"
)

# --- Pre-defined Constants ---
# NEW: Expanded list of common files/directories to always ignore
DEFAULT_IGNORE = [
    # General
    ".git", ".idea", ".vscode", "venv", ".env", "node_modules",
    "__pycache__", "dist", "build", "*.pyc", "*.log", "*.swp", ".DS_Store",
    "Thumbs.db",

    # Flutter / Dart
    ".dart_tool/", "build/", ".flutter-plugins", ".flutter-plugins-dependencies",

    # Mobile - Android (Gradle)
    ".gradle/", "app/build/", "captures/", "*.apk", "*.aab", "local.properties",
    "gradlew", "gradlew.bat", "/android/app/debug", "/android/app/profile",
    "/android/app/release",

    # Mobile - iOS (Xcode)
    "Pods/", "ios/Pods/", ".symlinks/", "ios/.symlinks/",
    "**/*.xcodeproj/project.xcworkspace/", "**/xcuserdata/", "ios/Flutter/App.framework",
    "ios/Flutter/Flutter.framework",

    # Mobile - Assets / Resources (often contain binary or boilerplate)
    "**/android/app/src/main/res/drawable*",
    "**/android/app/src/main/res/mipmap*",
    "**/ios/Runner/Assets.xcassets/*",

    # Compiled files
    "*.o", "*.so", "*.a", "*.class", "*.jar", "*.dll", "*.exe",

    # Package manager lock files
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "pubspec.lock",
    "poetry.lock", "Pipfile.lock"
]

# NEW: Expanded and sorted list of common text-based file extensions
COMMON_EXTENSIONS = sorted([
    # Web
    ".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".scss", ".less", ".svelte",
    # Python
    ".py", ".pyw", ".ipynb",
    # Mobile
    ".dart", ".java", ".kt", ".swift",
    # Backend
    ".go", ".rb", ".php", ".rs",
    # Config / Data
    ".json", ".xml", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".properties",
    ".md", ".txt", ".rtf", ".csv",
    # Build / Infra
    ".sh", ".ps1", ".bat", ".dockerfile", "Dockerfile", ".gitignore", "LICENSE",
    ".gradle", "CMakeLists.txt", "*.podspec", "*.project", "*.sln", "*.csproj",
    # Pubspec for Flutter
    "pubspec.yaml", "analysis_options.yaml"
])


# --- Helper Functions (with improvements) ---

def remove_readonly(func, path, exc_info):
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise

def is_text_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            f.read(1024)
        return True
    except (UnicodeDecodeError, IOError):
        return False

def get_repo_metadata(repo):
    try:
        latest_commit = repo.head.commit
        commit_hash = latest_commit.hexsha
        commit_message = latest_commit.message.strip()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
        return commit_hash, commit_message, timestamp
    except Exception as e:
        st.warning(f"Could not read git metadata: {e}")
        return "N/A", "N/A", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")

# CHANGED: Now takes repo_name to display a clean root folder name
def build_file_tree(root_path, repo_name, ignore_matcher, selected_extensions):
    tree_str = f"📂 {repo_name}\n"

    def _tree_generator(dir_path, prefix=""):
        items = sorted(list(dir_path.iterdir()), key=lambda x: (x.is_file(), x.name.lower()))
        
        for i, path in enumerate(items):
            if ignore_matcher(path) or any(part in DEFAULT_IGNORE for part in path.parts):
                continue

            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            
            if path.is_dir():
                yield prefix + connector + "📁 " + path.name
                new_prefix = prefix + ("    " if is_last else "│   ")
                yield from _tree_generator(path, new_prefix)
            elif path.is_file():
                if path.suffix.lower() in selected_extensions or path.name in selected_extensions:
                    yield prefix + connector + "📄 " + path.name

    tree_lines = list(_tree_generator(Path(root_path)))
    return tree_str + "\n".join(tree_lines)


@st.cache_data(ttl=600)
def generate_context_from_repo(repo_url, selected_extensions):
    temp_dir = tempfile.mkdtemp()
    
    try:
        st.info(f"Cloning {repo_url}...")
        repo = git.Repo.clone_from(repo_url, temp_dir, depth=1)
        st.info("Repository cloned successfully.")

        repo_root = Path(temp_dir)
        
        # NEW: Parse repo name from URL for cleaner display
        parsed_url = urlparse(repo_url)
        repo_name = Path(parsed_url.path).stem

        # --- Metadata ---
        commit_hash, commit_message, timestamp = get_repo_metadata(repo)

        gitignore_path = repo_root / '.gitignore'
        ignore_matcher = parse_gitignore(gitignore_path, base_dir=repo_root) if gitignore_path.exists() else lambda x: False

        context_parts = []
        
        header = f"""# LLM CONTEXT SNAPSHOT
- **Repository:** {repo_url}
- **Snapshot Timestamp:** {timestamp}
- **Last Commit Hash:** {commit_hash}
- **Last Commit Message:** {commit_message}
---
"""
        context_parts.append(header)

        st.info("Generating file structure...")
        # CHANGED: Pass repo_name to the tree builder
        file_tree = build_file_tree(repo_root, repo_name, ignore_matcher, selected_extensions)
        context_parts.append("# 1. Repository File Structure\n\n" + file_tree + "\n\n---\n")
        
        st.info("Reading and concatenating file contents...")
        context_parts.append("# 2. File Contents\n")
        
        file_count = 0
        for path in sorted(repo_root.rglob('*')):
            if path.is_file() and not ignore_matcher(path) and not any(part in DEFAULT_IGNORE for part in path.parts):
                if path.suffix.lower() in selected_extensions or path.name in selected_extensions:
                    if not is_text_file(path):
                        continue
                    
                    # CHANGED: Use .as_posix() to ensure forward slashes
                    relative_path = path.relative_to(repo_root).as_posix()
                    context_parts.append(f"--- FILE: {relative_path} ---\n")
                    try:
                        content = path.read_text(encoding='utf-8')
                        lang = path.suffix.lstrip('.').lower()
                        context_parts.append(f"```{lang}\n{content}\n```\n")
                        file_count += 1
                    except Exception as e:
                        context_parts.append(f"[Could not read file: {e}]\n")
        repo.close()

        if file_count == 0:
            st.warning("No files matched the selected extensions. The context will be minimal.")

        st.success(f"Context generated! Found {file_count} relevant files.")
        return "\n".join(context_parts)

    except git.GitCommandError as e:
        return f"Error: Could not clone repository. Is the URL correct and the repository public?\nDetails: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    finally:
        shutil.rmtree(temp_dir, onerror=remove_readonly)


# --- Streamlit App UI (No changes needed here) ---
st.title("🤖 GitHub Repo to LLM Context Generator")
st.markdown("""
Paste a public GitHub repository URL to generate a single, comprehensive text file. 
This file contains the repository's structure and the content of key files, optimized for providing context to a Large Language Model (LLM).
""")

repo_url = st.text_input(
    "Enter a public GitHub repository URL",
    placeholder="https://github.com/streamlit/streamlit"
)

st.subheader("⚙️ Configuration")
selected_extensions = st.multiselect(
    "Select file extensions to include:",
    options=COMMON_EXTENSIONS, # Uses the new sorted list
    default=[ext for ext in COMMON_EXTENSIONS if ext in [".py", ".md", ".json", ".yaml", ".toml", ".js", ".html", "pubspec.yaml", ".dart"]]
)

if st.button("🚀 Generate Context", use_container_width=True):
    if repo_url:
        with st.spinner("Hold on... The robots are cloning the repo and analyzing the files..."):
            full_context = generate_context_from_repo(repo_url, selected_extensions)
        
        if full_context.startswith("Error:"):
            st.error(full_context)
        else:
            st.success("Context successfully generated!")
            
            st.download_button(
                label="📥 Download Context.md",
                data=full_context,
                file_name=f"{urlparse(repo_url).path.split('/')[-1]}_context.md",
                mime="text/markdown",
                use_container_width=True
            )
            
            st.markdown("### Generated Context Preview:")
            st.code(full_context, language='markdown', line_numbers=True)

    else:
        st.warning("Please enter a GitHub repository URL to begin.")