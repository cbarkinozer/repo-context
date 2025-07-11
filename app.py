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
    # Web
    ".html", ".htm", ".xhtml", ".css", ".scss", ".sass", ".less",
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".json", ".jsonc", ".xml",

    # Markdown & text
    ".md", ".markdown", ".txt", ".rtf", ".adoc", ".rst", ".org",

    # Python
    ".py", ".pyw", ".ipynb", ".pyd", ".pyi", ".pyx",

    # Java
    ".java", ".jar", ".jsp", ".gradle", ".properties", "*.project", "*.classpath",

    # Kotlin
    ".kt", ".kts",

    # Swift
    ".swift",

    # Go
    ".go", "go.mod", "go.sum",

    # Ruby
    ".rb", ".erb", ".rake", "Rakefile", ".gemspec", "Gemfile", "Gemfile.lock",

    # PHP
    ".php", ".phtml",

    # Rust
    ".rs", "Cargo.toml", "Cargo.lock",

    # Dart & Flutter
    ".dart", "pubspec.yaml", "analysis_options.yaml", "*.podspec",

    # C / C++ / CMake
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h++",
    "CMakeLists.txt", ".cmake",

    # C#
    ".cs", "*.sln", "*.csproj",

    # Shell / CLI
    ".sh", ".bash", ".zsh", ".ksh", ".fish", ".ps1", ".bat", ".cmd",

    # Containers & Infra
    ".dockerfile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env", ".env.example",

    # Build systems
    "Makefile", "makefile", ".ninja", "build.ninja", "BUILD", "WORKSPACE",

    # JavaScript/Node
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    ".babelrc", ".eslintrc", ".eslintrc.json", ".eslintrc.js", ".prettierrc",
    ".prettierrc.json", ".prettierrc.js", ".stylelintrc", "vite.config.js", "webpack.config.js",

    # Config / Data / DevOps
    ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".env",
    ".editorconfig", ".gitconfig", ".gitattributes", ".gitignore",

    # Dotfiles & Licenses
    "LICENSE", "README.md", "README", "CHANGELOG.md", "CONTRIBUTING.md",

    # Svelte
    ".svelte",

    # Misc
    ".sql", ".db", ".sqlite", ".log", ".csv", ".tsv",
    ".asm", ".wasm", ".vb", ".vbs", ".fs", ".fsx", ".clj", ".cljs", ".edn",
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
        branch_name = repo.active_branch.name
        return commit_hash, commit_message, branch_name
    except Exception as e:
        st.warning(f"Could not read git metadata: {e}")
        return "N/A", "N/A", "N/A"

# --- MODIFIED ---
# This function is rewritten to be more robust and correctly handle various GitHub URL formats,
# including those with branches but no subdirectories.
def parse_github_url(url):
    """
    Parses a GitHub URL to extract base repo URL, branch, and subdirectory.
    Handles:
    - https://github.com/user/repo
    - https://github.com/user/repo.git
    - https://github.com/user/repo/tree/branch_name
    - https://github.com/user/repo/tree/branch_name/path/to/subdir
    """
    url = url.rstrip('/')
    # Regex to capture user, repo, branch, and optional subdirectory
    branch_pattern = re.match(r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(?:/(.*))?$", url)
    if branch_pattern:
        user, repo_name, branch, subdirectory = branch_pattern.groups()
        base_repo_url = f"https://github.com/{user}/{repo_name.replace('.git', '')}.git"
        return base_repo_url, branch, subdirectory

    # Regex for standard repo URLs without a specified branch
    repo_pattern = re.match(r"https://github\.com/([^/]+)/([^/]+)(\.git)?$", url)
    if repo_pattern:
        user, repo_name, _ = repo_pattern.groups()
        base_repo_url = f"https://github.com/{user}/{repo_name}.git"
        return base_repo_url, None, None # No branch or subdir specified

    # Fallback for any other git URL format
    return url, None, None


def build_file_tree(root_path, display_name, ignore_matcher, selected_extensions):
    tree_str = f"📂 {display_name}\n"
    def _tree_generator(dir_path, prefix=""):
        items_to_process = []
        try:
            for p in dir_path.iterdir():
                # Check against both the gitignore matcher and the hardcoded default ignore list
                if not ignore_matcher(p.resolve()) and not any(part in DEFAULT_IGNORE for part in p.parts):
                    items_to_process.append(p)
        except FileNotFoundError:
             st.warning(f"Directory not found during tree build: {dir_path}. It might have been ignored.")
             return

        items = sorted(items_to_process, key=lambda x: (x.is_file(), x.name.lower()))

        for i, path in enumerate(items):
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
        content = (repo_root / "requirements.txt").read_text(encoding='utf-8', errors='ignore')
        dep_details.append("**Dependencies (`requirements.txt`):**\n```\n" + content + "\n```")
    if (repo_root / "pyproject.toml").exists() and tomli:
        tech_stack.add("Python")
        try:
            content = tomli.loads((repo_root / "pyproject.toml").read_text(encoding='utf-8', errors='ignore'))
            deps = content.get("project", {}).get("dependencies", [])
            if deps: dep_details.append("**Dependencies (`pyproject.toml`):**\n- " + "\n- ".join(deps))
        except tomli.TOMLDecodeError: dep_details.append("**Dependencies (`pyproject.toml`):**\n- *Could not parse file.*")
    if (repo_root / "package.json").exists():
        tech_stack.add("JavaScript/TypeScript")
        try:
            content = json.loads((repo_root / "package.json").read_text(encoding='utf-8', errors='ignore'))
            deps, dev_deps = content.get("dependencies", {}), content.get("devDependencies", {})
            if deps: dep_details.append("**Dependencies (`package.json`):**\n- " + "\n- ".join(deps.keys()))
            if dev_deps: dep_details.append("**Dev Dependencies (`package.json`):**\n- " + "\n- ".join(dev_deps.keys()))
        except json.JSONDecodeError: dep_details.append("**Dependencies (`package.json`):**\n- *Could not parse file.*")
    if (repo_root / "pubspec.yaml").exists() and yaml:
        tech_stack.add("Flutter/Dart")
        try:
            content = yaml.safe_load((repo_root / "pubspec.yaml").read_text(encoding='utf-8', errors='ignore'))
            deps = content.get("dependencies", {})
            if deps: dep_details.append("**Dependencies (`pubspec.yaml`):**\n- " + "\n- ".join(deps.keys()))
        except yaml.YAMLError: dep_details.append("**Dependencies (`pubspec.yaml`):**\n- *Could not parse file.*")

    if not tech_stack: return "Undetermined", "No common dependency files were found. If this is a subdirectory, dependency files might be in the parent directory."
    return ", ".join(sorted(list(tech_stack))), "\n\n".join(dep_details)

def get_file_heuristic_tag(file_path):
    file_name = file_path.name
    for tag, patterns in KEY_FILE_HEURISTICS.items():
        for pattern in patterns:
            if (pattern.startswith('*') and file_name.endswith(pattern[1:])) or (pattern.endswith('*') and file_name.startswith(pattern[:-1])) or (pattern == file_name):
                return f"[{tag}]"
    return ""

def get_code_statistics(content, extension, line_count):
    chars = len(content)
    count = 0
    if extension in ['.py', '.pyw']: count = len(re.findall(r'^\s*(def|class)\s', content, re.MULTILINE))
    elif extension in ['.js', '.jsx', '.ts', '.tsx']: count = len(re.findall(r'^\s*(function|class|const|let|var)\s+.*\s*(=>|\()', content, re.MULTILINE))
    elif extension in ['.java', '.kt', '.cs', '.go', '.rs', '.swift']: count = len(re.findall(r'^\s*(public|private|protected|internal)?\s*(class|struct|func|fn|fun|void|static)\s', content, re.MULTILINE))
    label = "Funcs/Classes" if count > 0 else ""
    stats_str = f"(Lines: {line_count} | Chars: {chars}" + (f" | {label}: {count}" if label else "") + ")"
    return stats_str


# --- Main Function ---
@st.cache_data(ttl=300)
def generate_context_from_repo(repo_url, selected_extensions, file_line_limit=3000, token=None, user_timezone="UTC"):
    temp_dir = tempfile.mkdtemp()

    try:
        truncated_files = []
        try:
            tz = ZoneInfo(user_timezone)
        except ZoneInfoNotFoundError:
            st.warning(f"Invalid timezone '{user_timezone}' provided. Falling back to UTC.")
            tz = timezone.utc

        local_now = datetime.now(tz)
        timestamp = local_now.strftime("%Y-%m-%d %H:%M:%S %Z")

        base_repo_url, branch, subdirectory = parse_github_url(repo_url)
        if not base_repo_url:
            return "Error: Could not parse the provided GitHub URL. Please check the format."

        clone_url = construct_auth_url(base_repo_url, token)

        if token:
            st.info("Using Personal Access Token for private repository access.")

        repo = None
        analysis_root = Path(temp_dir)
        repo_display_name = ""

        if subdirectory:
            st.info(f"Performing sparse checkout for subdirectory: '{subdirectory}' on branch '{branch}'...")
            repo = git.Repo.init(temp_dir)
            origin = repo.create_remote('origin', clone_url)
            repo.config_writer().set_value("core", "sparseCheckout", "true").release()

            sparse_checkout_file = Path(repo.git_dir) / "info" / "sparse-checkout"
            # Include common root-level config files in sparse checkout
            sparse_content = [
                f"{subdirectory}/*",
                "/.gitignore", "/README.md", "/package.json", "/pyproject.toml", "/requirements.txt"
            ]
            sparse_checkout_file.write_text("\n".join(sparse_content), encoding="utf-8")

            try:
                st.info(f"Fetching from branch: {branch}...")
                origin.fetch(refspec=branch, depth=1)
                repo.git.checkout(branch)
                st.info("Sparse checkout successful.")
            except git.GitCommandError as e:
                if f"'{branch}'" in str(e) and "not found in upstream" in str(e):
                    return f"Error: The branch '{branch}' was not found in the repository. Please check the branch name in the URL.\nDetails: {e}"
                else:
                    return f"Error: An error occurred during git fetch/checkout. Please check the URL and branch name.\nDetails: {e}"

            analysis_root = Path(temp_dir) / subdirectory
            repo_display_name = f"{Path(urlparse(base_repo_url).path).stem}/{subdirectory}"
        else:
            # --- MODIFIED ---
            # This block now correctly uses the 'branch' variable when cloning the whole repo.
            clone_args = {'depth': 1}
            if branch:
                clone_args['branch'] = branch
                st.info(f"Cloning full repository from branch: '{branch}'...")
            else:
                st.info(f"Cloning full repository from default branch...")

            repo = git.Repo.clone_from(clone_url, temp_dir, **clone_args)
            analysis_root = Path(temp_dir)
            repo_display_name = Path(urlparse(base_repo_url).path).stem
            st.info("Repository cloned successfully.")

        st.info("Analyzing dependencies and project structure...")
        commit_hash, commit_message, active_branch = get_repo_metadata(repo)

        tech_stack, dep_details = analyze_dependencies(Path(temp_dir))

        gitignore_path = Path(temp_dir) / '.gitignore'
        ignore_matcher = parse_gitignore(gitignore_path, base_dir=Path(temp_dir)) if gitignore_path.exists() else lambda x: False

        context_parts = []
        header = f"""# LLM CONTEXT SNAPSHOT
- **Repository Source:** {repo_url}
- **Branch:** {active_branch}
- **Snapshot Timestamp:** {timestamp}
- **Last Commit Hash:** {commit_hash}
- **Last Commit Message:** {commit_message}
- **Detected Technology Stack:** {tech_stack}
---
"""
        context_parts.append(header)
        context_parts.append(f"# 1. Project Dependencies Analysis\n\n{dep_details}\n\n---")

        st.info("Generating file structure...")
        file_tree = build_file_tree(analysis_root, repo_display_name, ignore_matcher, selected_extensions)
        context_parts.append(f"# 2. Repository File Structure\n\n```\n{file_tree}\n```\n\n---")

        st.info("Reading and analyzing file contents...")
        context_parts.append("# 3. File Contents\n")

        file_count = 0
        for path in sorted(analysis_root.rglob('*')):
            if path.is_file() and not ignore_matcher(path.resolve()) and not any(part in DEFAULT_IGNORE for part in path.parts):
                if path.suffix.lower() in selected_extensions or path.name in selected_extensions:
                    if not is_text_file(path): continue

                    relative_path = path.relative_to(analysis_root).as_posix()

                    try:
                        original_content = path.read_text(encoding='utf-8', errors='ignore')
                    except Exception as e:
                        st.warning(f"Could not read file {relative_path}: {e}")
                        continue

                    lines = original_content.splitlines()
                    original_line_count = len(lines)
                    content_for_output = original_content

                    stats_str = get_code_statistics(original_content, path.suffix.lower(), original_line_count)

                    if file_line_limit > 0 and original_line_count > file_line_limit:
                        truncated_files.append((relative_path, original_line_count))
                        content_for_output = "\n".join(lines[:file_line_limit])
                        content_for_output += f"\n\n... [File truncated at {file_line_limit} lines. Original file had {original_line_count} lines.] ..."

                    heuristic_tag = get_file_heuristic_tag(path)
                    context_parts.append(f"--- FILE: {relative_path} {heuristic_tag} {stats_str} ---\n")
                    lang = path.suffix.lstrip('.').lower()
                    context_parts.append(f"```{lang}\n{content_for_output}\n```\n")
                    file_count += 1
        repo.close()

        if truncated_files:
            truncated_files_list = "\n".join([f"- `{path}` (original: {lines} lines)" for path, lines in truncated_files])
            truncated_files_section = f"""---
# 4. Truncated Files

The following files were truncated because they exceeded the line limit of {file_line_limit} lines:
{truncated_files_list}
"""
            context_parts.append(truncated_files_section)

        if file_count == 0: st.warning("No files matched the selected extensions. The context will be minimal.")
        truncation_info = f" Truncated {len(truncated_files)} files due to the line limit." if truncated_files else ""
        st.success(f"Context generated! Found and analyzed {file_count} relevant files.{truncation_info}")
        return "\n".join(context_parts)

    except git.GitCommandError as e:
        error_message = str(e)
        if "Authentication failed" in error_message or "could not read Username" in error_message:
            return f"Error: Authentication failed. Please check your Personal Access Token and its permissions.\nDetails: {error_message}"
        elif "could not resolve host" in error_message.lower():
            return f"Error: Could not resolve host. Please check the repository URL and your internet connection.\nDetails: {error_message}"
        elif "not found" in error_message.lower():
            return f"Error: Repository or branch not found. Please check the URL, including the branch name for subdirectory URLs.\nDetails: {error_message}"
        else:
            return f"Error: Could not clone repository. Is the URL correct and the repository public (or is your token valid)?\nDetails: {error_message}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onerror=remove_readonly)


# --- Streamlit App UI ---
st.title("🤖 GitHub Repo to LLM Context Generator")
st.markdown("An intelligent context generator for Large Language Models. This tool analyzes a public **or private** GitHub repository and formats it into a single, comprehensive text file.")

repo_url = st.text_input(
    "Enter a GitHub repository URL (public or private)",
    placeholder="https://github.com/user/repo/tree/branch_name",
    help="You can provide a URL to a specific branch or subdirectory (e.g., https://github.com/user/repo/tree/main/src/app)."
)

with st.expander("🔑 Private Repository Access"):
    access_token = st.text_input(
        "GitHub Personal Access Token (PAT)",
        type="password",
        help="Create a token at https://github.com/settings/tokens. The 'repo' scope is required for private repositories."
    )

st.subheader("⚙️ Configuration")

col1, col2 = st.columns(2)
with col1:
    all_timezones = sorted(list(available_timezones()))
    default_tz = "Europe/Istanbul"
    try:
        default_ix = all_timezones.index(default_tz)
    except ValueError:
        default_ix = all_timezones.index("UTC")

    selected_timezone = st.selectbox(
        "🕒 Select your timezone for timestamps:",
        options=all_timezones,
        index=default_ix,
        help="The snapshot timestamp in the generated file will use this timezone."
    )

with col2:
    file_line_limit = st.number_input(
        "📝 File Line Limit (0 for no limit)",
        min_value=0,
        value=3000,
        step=100,
        help="Files exceeding this number of lines will be truncated. Set to 0 to disable the limit."
    )

selected_extensions = st.multiselect(
    "Select file extensions to include:",
    options=COMMON_EXTENSIONS,
    default=COMMON_EXTENSIONS
)

if st.button("🚀 Generate Intelligent Context", use_container_width=True):
    if repo_url:
        with st.spinner("Hold on... The robots are cloning, analyzing, and building the context..."):
            full_context = generate_context_from_repo(
                repo_url,
                selected_extensions,
                file_line_limit=file_line_limit,
                token=access_token,
                user_timezone=selected_timezone
            )

        if full_context.startswith("Error:"):
            st.error(full_context)
        else:
            st.success("Intelligent context successfully generated!")

            base_repo_url, branch, subdirectory = parse_github_url(repo_url)
            repo_name = Path(urlparse(base_repo_url).path).stem
            file_name_parts = [repo_name]
            if branch:
                file_name_parts.append(branch.replace('/', '_'))
            if subdirectory:
                file_name_parts.append(subdirectory.replace('/', '_'))
            
            file_name = "_".join(file_name_parts) + "_context.md"

            st.download_button(
                label="📥 Download Context.md",
                data=full_context,
                file_name=file_name,
                mime="text/markdown",
                use_container_width=True
            )
            st.markdown("### Generated Context Preview:")
            st.text_area("Context", full_context, height=500, label_visibility="collapsed")
    else:
        st.warning("Please enter a GitHub repository URL to begin.")