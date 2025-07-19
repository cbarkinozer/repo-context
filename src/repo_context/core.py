# src/repo_context/core.py

import git
import os
import tempfile
import shutil
from pathlib import Path
from gitignore_parser import parse_gitignore
from datetime import datetime
import stat
from urllib.parse import urlparse
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Conditional imports for dependency parsing
try:
    import tomli
except ImportError:
    tomli = None
try:
    import yaml
except ImportError:
    yaml = None

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
    """Error handler for shutil.rmtree.
    
    If the error is due to an access error (read-only file),
    it attempts to change the file's permissions and re-exectute the function.
    Otherwise, it raises the error.
    """
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise

def is_text_file(path):
    """Check if a file is likely a text file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            f.read(1024) # Read a small portion to check for encoding errors
        return True
    except (UnicodeDecodeError, IOError):
        return False

def construct_auth_url(repo_url, token):
    """Construct a git URL with an embedded OAuth token for authentication."""
    if not token:
        return repo_url
    parsed_url = urlparse(repo_url)
    auth_url = parsed_url._replace(netloc=f"oauth2:{token}@{parsed_url.netloc}")
    return auth_url.geturl()

def get_repo_metadata(repo):
    """Extract metadata from the git repository."""
    try:
        latest_commit = repo.head.commit
        commit_hash = latest_commit.hexsha
        commit_message = latest_commit.message.strip()
        branch_name = repo.active_branch.name
        return commit_hash, commit_message, branch_name
    except Exception as e:
        print(f"Warning: Could not read git metadata: {e}")
        return "N/A", "N/A", "N/A"

def parse_github_url(url):
    """
    Parses a GitHub URL to extract base repo URL, branch, and subdirectory.
    """
    url = url.rstrip('/')
    branch_pattern = re.match(r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(?:/(.*))?$", url)
    if branch_pattern:
        user, repo_name, branch, subdirectory = branch_pattern.groups()
        base_repo_url = f"https://github.com/{user}/{repo_name.replace('.git', '')}.git"
        return base_repo_url, branch, subdirectory

    repo_pattern = re.match(r"https://github\.com/([^/]+)/([^/]+)(\.git)?$", url)
    if repo_pattern:
        user, repo_name, _ = repo_pattern.groups()
        base_repo_url = f"https://github.com/{user}/{repo_name}.git"
        return base_repo_url, None, None

    return url, None, None

def build_file_tree(root_path, display_name, ignore_matcher, selected_extensions):
    """Generate a string representation of the file tree."""
    tree_str = f"📂 {display_name}\n"
    def _tree_generator(dir_path, prefix=""):
        items_to_process = []
        try:
            for p in dir_path.iterdir():
                if not ignore_matcher(p.resolve()) and not any(part in DEFAULT_IGNORE for part in p.parts):
                    items_to_process.append(p)
        except FileNotFoundError:
             print(f"Warning: Directory not found during tree build: {dir_path}.")
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
    """Analyze dependency files to determine tech stack and list dependencies."""
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
    """Apply a heuristic tag to a file based on its name."""
    file_name = file_path.name
    for tag, patterns in KEY_FILE_HEURISTICS.items():
        for pattern in patterns:
            if (pattern.startswith('*') and file_name.endswith(pattern[1:])) or \
               (pattern.endswith('*') and file_name.startswith(pattern[:-1])) or \
               (pattern == file_name):
                return f"[{tag}]"
    return ""

def get_code_statistics(content, extension, line_count):
    """Generate a statistics string for a file (lines, chars, functions/classes)."""
    chars = len(content)
    count = 0
    if extension in ['.py', '.pyw']: count = len(re.findall(r'^\s*(def|class)\s', content, re.MULTILINE))
    elif extension in ['.js', '.jsx', '.ts', '.tsx']: count = len(re.findall(r'^\s*(function|class|const|let|var)\s+.*\s*(=>|\()', content, re.MULTILINE))
    elif extension in ['.java', '.kt', '.cs', '.go', '.rs', '.swift']: count = len(re.findall(r'^\s*(public|private|protected|internal)?\s*(class|struct|func|fn|fun|void|static)\s', content, re.MULTILINE))
    label = "Funcs/Classes" if count > 0 else ""
    stats_str = f"(Lines: {line_count} | Chars: {chars}" + (f" | {label}: {count}" if label else "") + ")"
    return stats_str


# --- Main Logic Function ---
def generate_context_from_repo(repo_url, selected_extensions, file_line_limit=3000, token=None, user_timezone="UTC"):
    """
    Clones a repository, analyzes its content, and returns a single
    markdown string with the structured context.
    """
    temp_dir = tempfile.mkdtemp()

    try:
        truncated_files = []
        try:
            tz = ZoneInfo(user_timezone)
        except ZoneInfoNotFoundError:
            print(f"Warning: Invalid timezone '{user_timezone}' provided. Falling back to UTC.")
            tz = ZoneInfo("UTC")

        timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
        base_repo_url, branch, subdirectory = parse_github_url(repo_url)
        if not base_repo_url:
            return "Error: Could not parse the provided GitHub URL. Please check the format."

        clone_url = construct_auth_url(base_repo_url, token)
        if token:
            print("Info: Using Personal Access Token for private repository access.")

        repo = None
        analysis_root = Path(temp_dir)
        repo_display_name = ""

        if subdirectory:
            print(f"Info: Performing sparse checkout for subdirectory: '{subdirectory}' on branch '{branch}'...")
            repo = git.Repo.init(temp_dir)
            origin = repo.create_remote('origin', clone_url)
            repo.config_writer().set_value("core", "sparseCheckout", "true").release()

            sparse_checkout_file = Path(repo.git_dir) / "info" / "sparse-checkout"
            sparse_content = [f"{subdirectory}/*", "/.gitignore", "/README.md", "/package.json", "/pyproject.toml", "/requirements.txt"]
            sparse_checkout_file.write_text("\n".join(sparse_content), encoding="utf-8")

            try:
                print(f"Info: Fetching from branch: {branch}...")
                origin.fetch(refspec=branch, depth=1)
                repo.git.checkout(branch)
                print("Info: Sparse checkout successful.")
            except git.GitCommandError as e:
                if f"'{branch}'" in str(e) and "not found in upstream" in str(e):
                    return f"Error: The branch '{branch}' was not found in the repository. Please check the branch name in the URL.\nDetails: {e}"
                else:
                    return f"Error: An error occurred during git fetch/checkout. Please check the URL and branch name.\nDetails: {e}"

            analysis_root = Path(temp_dir) / subdirectory
            repo_display_name = f"{Path(urlparse(base_repo_url).path).stem}/{subdirectory}"
        else:
            clone_args = {'depth': 1}
            if branch:
                clone_args['branch'] = branch
                print(f"Info: Cloning full repository from branch: '{branch}'...")
            else:
                print("Info: Cloning full repository from default branch...")

            repo = git.Repo.clone_from(clone_url, temp_dir, **clone_args)
            analysis_root = Path(temp_dir)
            repo_display_name = Path(urlparse(base_repo_url).path).stem
            print("Info: Repository cloned successfully.")

        print("Info: Analyzing dependencies and project structure...")
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
        
        print("Info: Generating file structure...")
        file_tree = build_file_tree(analysis_root, repo_display_name, ignore_matcher, selected_extensions)
        context_parts.append(f"# 2. Repository File Structure\n\n```\n{file_tree}\n```\n\n---")

        print("Info: Reading and analyzing file contents...")
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
                        print(f"Warning: Could not read file {relative_path}: {e}")
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
            context_parts.append(f"---\n# 4. Truncated Files\n\nThe following files were truncated:\n{truncated_files_list}\n")

        if file_count == 0: print("Warning: No files matched the selected extensions. The context will be minimal.")
        truncation_info = f" Truncated {len(truncated_files)} files." if truncated_files else ""
        print(f"Success: Context generated! Analyzed {file_count} files.{truncation_info}")
        return "\n".join(context_parts)

    except git.GitCommandError as e:
        error_message = str(e)
        if "Authentication failed" in error_message or "could not read Username" in error_message:
            return f"Error: Authentication failed. Check your Personal Access Token.\nDetails: {error_message}"
        elif "could not resolve host" in error_message.lower():
            return f"Error: Could not resolve host. Check the repository URL and your internet connection.\nDetails: {error_message}"
        elif "not found" in error_message.lower():
            return f"Error: Repository or branch not found. Check the URL.\nDetails: {error_message}"
        else:
            return f"Error: Could not clone repository. Is the URL correct?\nDetails: {error_message}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onerror=remove_readonly)