# GitHub Repo to LLM Context Generator

[![PyPI Version](https://img.shields.io/pypi/v/repo-context-generator.svg)](https://pypi.org/project/repo-context-generator/)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://repo-context.streamlit.app/)

An intelligent context generator for Large Language Models. This tool analyzes a public **or private** GitHub repository, extracts key information, and formats it into a single, comprehensive text file. It is available as a command-line tool and as a web UI.

You can use this when:
*   You need to provide context to a Large Language Model without a "chat history" feature.
*   Your conversation with an LLM is going in circles and you need to restart with full context.
*   You have questions about a repository's implementation, dependencies, or structure.

## The Problem

When working with Large Language Models on a software project, providing the full context of a repository is challenging:

1.  **Limited Context Windows:** LLMs can't read an entire codebase at once.
2.  **Tedious Manual Work:** Manually copying and pasting dozens of files is slow and error-prone.
3.  **Irrelevant "Noise":** A raw dump includes useless "noise" for an LLM, such as `node_modules`, `__pycache__`, and build artifacts, which wastes precious context space.
4.  **Lack of Structure:** A simple concatenation of files makes it hard for the LLM to distinguish where one file ends and another begins.

This tool solves these problems by creating a clean, intelligent, and structured snapshot of your repository's current state.

## ✨ Key Features

*   **Dual Interface:** Use the friendly [web UI](https://repo-context.streamlit.app/) or the powerful command-line tool (`repo-context`) for easy integration into scripts.
*   **Pip Installable:** Easily install the tool with a single command: `pip install repo-context-generator`.
*   **Private Repository Support:** Securely analyze private repositories using a GitHub Personal Access Token (PAT).
*   **Automated Dependency Analysis:** Detects tech stacks (`Python`, `JavaScript`, etc.) and lists dependencies from common package files.
*   **Intelligent File Tagging:** Adds heuristic tags like `[⭐ Likely Project Entry Point]` to guide the LLM's focus.
*   **Intelligent Filtering:** Automatically respects the repository's `.gitignore` file and excludes common non-essential files.
*   **Rich Metadata Header:** The context starts with a header including the repo URL, timestamp, and latest commit details.

## ⚙️ Installation

Install the package directly from PyPI:

```bash
pip install repo-context-generator
```

## 🚀 Usage

You can use the tool via the **Web UI** or the **Command-Line**.

### 🖥️ Command-Line Interface

Once installed, you can use the `repo-context` command in your terminal.

**1. Generate context and print to console:**

```bash
repo-context "https://github.com/user/repo"
```

**2. Save context to a file:**

```bash
repo-context "https://github.com/user/repo/tree/main" -o my_project_context.md
```

**3. Analyze a private repository:**
You can provide a token via the `--token` flag or the `GITHUB_TOKEN` environment variable.

```bash
# Using a flag
repo-context "https://github.com/private-user/private-repo" --token YOUR_GITHUB_PAT

# Or by setting an environment variable
export GITHUB_TOKEN="YOUR_GITHUB_PAT"
repo-context "https://github.com/private-user/private-repo"
```

**4. See all available options:**

```bash
repo-context --help
```

### 🌐 Web UI

**Try the app live here:** [https://repo-context.streamlit.app/](https://repo-context.streamlit.app/)

1.  Navigate to the deployed Streamlit application.
2.  Paste the full URL of a public or private GitHub repository.
3.  **For private repositories,** expand the "🔑 Private Repository Access" section and paste your Personal Access Token (PAT).
4.  Configure any optional settings, like file extensions or line limits.
5.  Click the **"🚀 Generate Intelligent Context"** button.
6.  Use the **"📥 Download Context.md"** button to save the output.

---

## 📝 Example Output Structure

The generated output is a single, enriched Markdown file designed to be easily parsed by an LLM.

```markdown
# LLM CONTEXT SNAPSHOT
- **Repository Source:** https://github.com/user/my-python-app
- **Branch:** main
- **Snapshot Timestamp:** 2025-07-19 20:55:00 UTC
- **Last Commit Hash:** a1b2c3d4e5f6g7h8i9j0
- **Last Commit Message:** "feat: Implement user authentication"
- **Detected Technology Stack:** Python
```
---

# 1. Project Dependencies Analysis

**Dependencies (`requirements.txt`):**
```txt
streamlit==1.33.0
gitpython==3.1.43
pyyaml==6.0.1
```

# 2. Repository File Structure

```txt
📂 my-python-app
├── 📄 .gitignore
├── 📄 app.py
├── 📄 README.md
└── 📄 requirements.txt
```

---
# 3. File Contents

--- FILE: app.py [⭐ Likely Project Entry Point] (Lines: 152 | Chars: 4891 | Funcs/Classes: 6) ---
```python
import streamlit as st
# ... rest of the file content
```
---

## 💻 Running for Development

To contribute to this project or run the web UI locally, follow these steps.

**Prerequisites:**
*   Python 3.8+
*   Git command-line tool

**Setup:**

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/cbarkinozer/repo-context.git
    cd repo-context
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install the project in editable mode:**
    This command reads the `pyproject.toml` file and installs all necessary dependencies, including Streamlit.
    ```bash
    pip install -e .
    ```

4.  **Run the Streamlit app:**
    ```bash
    streamlit run app.py
    ```
The application should now be running at `http://localhost:8501`.

## 🛠️ Technologies Used

*   **Framework:** [Streamlit](https://streamlit.io/)
*   **Language:** Python 3
*   **CLI:** `argparse`
*   **Git Operations:** [GitPython](https://gitpython.readthedocs.io/en/stable/)
*   **File Parsing:** [gitignore-parser](https://pypi.org/project/gitignore-parser/), [tomli](https://pypi.org/project/tomli/), [PyYAML](https://pypi.org/project/PyYAML/)

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.