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
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

# Conditional imports for dependency parsing
try:
    import tomli
except ImportError:
    tomli = None
try:
    import yaml
except ImportError:
    yaml = None


# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="GitHub Repo to LLM Context",
    page_icon="🤖",
    layout="wide"
)

# --- Pre-defined Constants ---
DEFAULT_IGNORE = [
    ".git", ".idea", ".vscode", "venv", ".env", "node_modules",
    "__pycache__", "dist", "build", "*.pyc", "*.log", "*.swp", ".DS_Store",
    "Thumbs.db", ".dart_tool/", "build/", ".flutter-plugins",
    ".flutter-plugins-dependencies", ".gradle/", "app/build/", "captures/",
    "*.apk", "*.aab", "local.properties", "gradlew", "gradlew.bat",
    "/android/app/debug", "/android/app/profile", "/android/app/release",
    "Pods/", "ios/Pods/", ".symlinks/", "ios/.symlinks/",
    "**/*.xcodeproj/project.xcworkspace/", "**/xcuserdata/",
    "ios/Flutter/App.framework", "ios/Flutter/Flutter.framework",
    "**/android/app/src/main/res/drawable*",
    "**/android/app/src/main/res/mipmap*",
    "**/ios/Runner/Assets.xcassets/*", "*.o", "*.so", "*.a", "*.class",
    "*.jar", "*.dll", "*.exe", "package-lock.json", "yarn.lock",
    "pnpm-lock.yaml", "pubspec.lock", "poetry.lock"
]
COMMON_EXTENSIONS = sorted([
    ".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".scss", ".less", ".svelte",
    ".py", ".pyw", ".ipynb", ".dart", ".java", ".kt", ".swift", ".go", ".rb",
    ".php", ".rs", ".json", ".xml", ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".conf", ".properties", ".md", ".txt", ".rtf", ".csv", ".sh", ".ps1",
    ".bat", ".dockerfile", "Dockerfile", ".gitignore", "LICENSE", ".gradle",
    "CMakeLists.txt", "*.podspec", "*.project", "*.sln", "*.csproj",
    "pubspec.yaml", "analysis_options.yaml"
])
KEY_FILE_HEURISTICS = {
    "⭐ Likely Project Entry Point": ["main.py", "app.py", "index.js", "main.js", "index.ts", "main.ts", "index.html", "__main__.py"],
    "📦 Container Definition": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
    "🔧 Project Configuration": ["vite.config.js", "webpack.config.js", "babel.config.js", "tsconfig.json", "pyproject.toml", "setup.py"],
    "✅ Test File": ["*_test.py", "*.spec.js", "*.spec.ts", "*.test.js", "*.test.ts"],
    "📖 Documentation": ["README.md", "CONTRIBUTING.md", "LICENSE"]
}

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

def construct_auth_url(repo_url, token):
    if not token:
        return repo_url
    parsed_url = urlparse(repo_url)
    auth_url = parsed_url._replace(netloc=f"oauth2:{token}@{parsed_url.netloc}")
    return auth_url.geturl()

def get_repo_metadata(repo):
    try:
        latest_commit = repo.head.commit
        commit_hash = latest_commit.hexsha
        commit_message = latest_commit.message.strip()
        return commit_hash, commit_message
    except Exception as e:
        st.warning(f"Could not read git metadata: {e}")
        return "N/A", "N/A"

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
            elif path.is_file() and (path.suffix.lower() in selected_extensions or path.name in selected_extensions):
                yield prefix + connector + "📄 " + path.name
    tree_lines = list(_tree_generator(Path(root_path)))
    return tree_str + "\n".join(tree_lines)


def analyze_dependencies(repo_root):
    tech_stack = set()
    dep_details = []
    if (repo_root / "requirements.txt").exists():
        tech_stack.add("Python")
        content = (repo_root / "requirements.txt").read_text()
        dep_details.append("**Dependencies (`requirements.txt`):**\n```\n" + content + "\n```")
    if (repo_root / "pyproject.toml").exists() and tomli:
        tech_stack.add("Python")
        try:
            content = tomli.loads((repo_root / "pyproject.toml").read_text())
            deps = content.get("project", {}).get("dependencies", [])
            if deps: dep_details.append("**Dependencies (`pyproject.toml`):**\n- " + "\n- ".join(deps))
        except tomli.TOMLDecodeError: dep_details.append("**Dependencies (`pyproject.toml`):**\n- *Could not parse file.*")
    if (repo_root / "package.json").exists():
        tech_stack.add("JavaScript/TypeScript")
        try:
            content = json.loads((repo_root / "package.json").read_text())
            deps, dev_deps = content.get("dependencies", {}), content.get("devDependencies", {})
            if deps: dep_details.append("**Dependencies (`package.json`):**\n- " + "\n- ".join(deps.keys()))
            if dev_deps: dep_details.append("**Dev Dependencies (`package.json`):**\n- " + "\n- ".join(dev_deps.keys()))
        except json.JSONDecodeError: dep_details.append("**Dependencies (`package.json`):**\n- *Could not parse file.*")
    if (repo_root / "pubspec.yaml").exists() and yaml:
        tech_stack.add("Flutter/Dart")
        try:
            content = yaml.safe_load((repo_root / "pubspec.yaml").read_text())
            deps = content.get("dependencies", {})
            if deps: dep_details.append("**Dependencies (`pubspec.yaml`):**\n- " + "\n- ".join(deps.keys()))
        except yaml.YAMLError: dep_details.append("**Dependencies (`pubspec.yaml`):**\n- *Could not parse file.*")

    if not tech_stack: return "Undetermined", "No common dependency files were found."
    return ", ".join(sorted(list(tech_stack))), "\n\n".join(dep_details)

def get_file_heuristic_tag(file_path):
    file_name = file_path.name
    for tag, patterns in KEY_FILE_HEURISTICS.items():
        for pattern in patterns:
            if (pattern.startswith('*') and file_name.endswith(pattern[1:])) or (pattern.endswith('*') and file_name.startswith(pattern[:-1])) or (pattern == file_name):
                return f"[{tag}]"
    return ""

def get_code_statistics(content, extension):
    lines, chars = len(content.splitlines()), len(content)
    count = 0
    if extension in ['.py', '.pyw']: count = len(re.findall(r'^\s*(def|class)\s', content, re.MULTILINE))
    elif extension in ['.js', '.jsx', '.ts', '.tsx']: count = len(re.findall(r'^\s*(function|class|const|let|var)\s+.*\s*(=>|\()', content, re.MULTILINE))
    elif extension in ['.java', '.kt', '.cs', '.go', '.rs', '.swift']: count = len(re.findall(r'^\s*(public|private|protected|internal)?\s*(class|struct|func|fn|fun|void|static)\s', content, re.MULTILINE))
    label = "Funcs/Classes" if count > 0 else ""
    stats_str = f"(Lines: {lines} | Chars: {chars}" + (f" | {label}: {count}" if label else "") + ")"
    return stats_str


# --- Main Function ---
@st.cache_data(ttl=300)
def generate_context_from_repo(repo_url, selected_extensions, token=None, user_timezone="UTC"): # Changed param name for clarity
    temp_dir = tempfile.mkdtemp()
    
    try:
        try:
            tz = ZoneInfo(user_timezone)
        except ZoneInfoNotFoundError:
            st.warning(f"Invalid timezone '{user_timezone}' provided. Falling back to UTC.")
            tz = timezone.utc
        
        local_now = datetime.now(tz)
        timestamp = local_now.strftime("%Y-%m-%d %H:%M:%S %Z")

        clone_url = construct_auth_url(repo_url, token)
        if token:
            st.info("Using Personal Access Token for private repository access.")
        
        st.info(f"Cloning repository...")
        git.Repo.clone_from(clone_url, temp_dir, depth=1)
        st.info("Repository cloned successfully.")

        repo_root = Path(temp_dir)
        repo_name = Path(urlparse(repo_url).path).stem

        st.info("Analyzing dependencies and project structure...")
        repo = git.Repo(temp_dir)
        commit_hash, commit_message = get_repo_metadata(repo)
        tech_stack, dep_details = analyze_dependencies(repo_root)
        
        gitignore_path = repo_root / '.gitignore'
        ignore_matcher = parse_gitignore(gitignore_path, base_dir=repo_root) if gitignore_path.exists() else lambda x: False

        context_parts = []
        header = f"""
        # LLM CONTEXT SNAPSHOT
        - **Repository:** {repo_url}
        - **Snapshot Timestamp:** {timestamp}
        - **Last Commit Hash:** {commit_hash}
        - **Last Commit Message:** {commit_message}
        - **Detected Technology Stack:** {tech_stack}
        ---
        """
        context_parts.append(header)
        context_parts.append(f"# 1. Project Dependencies Analysis\n\n{dep_details}\n\n---")
        
        st.info("Generating file structure...")
        file_tree = build_file_tree(repo_root, repo_name, ignore_matcher, selected_extensions)
        context_parts.append(f"# 2. Repository File Structure\n\n```\n{file_tree}\n```\n\n---")
        
        st.info("Reading and analyzing file contents...")
        context_parts.append("# 3. File Contents\n")
        
        file_count = 0
        for path in sorted(repo_root.rglob('*')):
            if path.is_file() and not ignore_matcher(path) and not any(part in DEFAULT_IGNORE for part in path.parts):
                if path.suffix.lower() in selected_extensions or path.name in selected_extensions:
                    if not is_text_file(path): continue
                    relative_path = path.relative_to(repo_root).as_posix()
                    content = path.read_text(encoding='utf-8')
                    stats_str = get_code_statistics(content, path.suffix.lower())
                    heuristic_tag = get_file_heuristic_tag(path)
                    context_parts.append(f"--- FILE: {relative_path} {heuristic_tag} {stats_str} ---\n")
                    lang = path.suffix.lstrip('.').lower()
                    context_parts.append(f"```{lang}\n{content}\n```\n")
                    file_count += 1
        repo.close()

        if file_count == 0: st.warning("No files matched the selected extensions. The context will be minimal.")
        st.success(f"Context generated! Found and analyzed {file_count} relevant files.")
        return "\n".join(context_parts)

    except git.GitCommandError as e:
        error_message = str(e)
        if "Authentication failed" in error_message or "could not read Username" in error_message:
            return f"Error: Authentication failed. Please check your Personal Access Token and its permissions.\nDetails: {error_message}"
        else:
            return f"Error: Could not clone repository. Is the URL correct and the repository public (or is your token valid)?\nDetails: {error_message}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    finally:
        shutil.rmtree(temp_dir, onerror=remove_readonly)


# --- Streamlit App UI ---
st.title("🤖 GitHub Repo to LLM Context Generator")
st.markdown("An intelligent context generator for Large Language Models. This tool analyzes a public **or private** GitHub repository and formats it into a single, comprehensive text file.")

repo_url = st.text_input(
    "Enter a GitHub repository URL (public or private)",
    placeholder="https://github.com/user/repo"
)

with st.expander("🔑 Private Repository Access"):
    access_token = st.text_input(
        "GitHub Personal Access Token (PAT)",
        type="password",
        help="Create a token at https://github.com/settings/tokens. The 'repo' scope is required for private repositories."
    )

st.subheader("⚙️ Configuration")

# Create a timezone selector for the user
col1, col2 = st.columns(2)
with col1:
    # Get a sorted list of all available IANA timezones
    all_timezones = sorted(list(available_timezones()))
    default_tz = "Europe/Istanbul"
    # Find the index of the default timezone to pre-select it
    try:
        default_ix = all_timezones.index(default_tz)
    except ValueError:
        default_ix = all_timezones.index("UTC") # Fallback if default not found

    selected_timezone = st.selectbox(
        "🕒 Select your timezone for timestamps:",
        options=all_timezones,
        index=default_ix,
        help="The snapshot timestamp in the generated file will use this timezone."
    )

with col2:
    # This just adds some space, but you could put another config option here
    pass

selected_extensions = st.multiselect(
    "Select file extensions to include:",
    options=COMMON_EXTENSIONS,
    default=COMMON_EXTENSIONS
)

if st.button("🚀 Generate Intelligent Context", use_container_width=True):
    if repo_url:
        with st.spinner("Hold on... The robots are cloning, analyzing, and building the context..."):
            # Pass the user-selected timezone to the function
            full_context = generate_context_from_repo(
                repo_url,
                selected_extensions,
                token=access_token,
                user_timezone=selected_timezone
            )
        
        if full_context.startswith("Error:"):
            st.error("Failure!")
        else:
            st.success("Intelligent context successfully generated!")
            repo_name = Path(urlparse(repo_url).path).stem
            st.download_button(
                label="📥 Download Context.md",
                data=full_context,
                file_name=f"{repo_name}_context.md",
                mime="text/markdown",
                use_container_width=True
            )
            st.markdown("### Generated Context Preview:")
            st.text_area("Context", full_context, height=500, label_visibility="collapsed")
    else:
        st.warning("Please enter a GitHub repository URL to begin.")