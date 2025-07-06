# GitHub Repo to LLM Context Generator

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://repo-context.streamlit.app/)

An intelligent context generator for Large Language Models. This tool analyzes a public **or private** GitHub repository, extracts key information, and formats it into a single, comprehensive text file.

You can use this when:  
* You've closed the Gemini 2.5 chat in the Aistudio tab and there's no chat history available.
* Your conversation with the LLM is going in circles. For example, repeating the same explanations or stuck in a dead end during model debugging.
* You have questions about a repository, whether related to its implementation or its dependencies.

## The Problem

When working with Large Language Models on a software project, providing the full context of a repository is challenging:

1.  **Limited Context Windows:** LLMs can't read an entire codebase at once.
2.  **Tedious Manual Work:** Manually copying and pasting dozens of files is slow and error-prone.
3.  **Irrelevant "Noise":** A raw dump includes useless "noise" for an LLM, such as `node_modules`, `__pycache__`, virtual environments, and build artifacts, which wastes precious context space.
4.  **Lack of Structure:** A simple concatenation of files makes it hard for the LLM to distinguish where one file ends and another begins.

This tool solves these problems by creating a clean, intelligent, and structured snapshot of your repository's current state.

## ✨ Key Features

*   **Private Repository Support:** Securely analyze private repositories using a GitHub Personal Access Token (PAT).
*   **Automated Dependency Analysis:** Automatically detects the tech stack and lists all dependencies from files like `requirements.txt`, `package.json`, `pyproject.toml`, and `pubspec.yaml`.
*   **Intelligent File Tagging:** Uses heuristics to add informative tags to files, such as `[⭐ Likely Project Entry Point]` or `[📦 Container Definition]`, to guide the LLM's focus.
*   **Code Statistics:** Provides a quick overview of each file's complexity with line, character, and function/class counts.
*   **Intelligent Filtering:** Automatically respects the repository's `.gitignore` file and excludes a comprehensive list of common non-essential files and directories.
*   **Rich Metadata Header:** The generated context starts with a helpful header including the repository URL, a timestamp, and the latest commit details.
*   **Shallow Clone:** Quickly clones only the latest commit of a repository to be fast and resource-efficient.

## 🚀 Live Demo

**Try the app live here:** [https://repo-context.streamlit.app/](https://repo-context.streamlit.app/)

## 📋 How to Use

1.  Navigate to the deployed Streamlit application.
2.  Paste the full URL of a public or private GitHub repository into the text box.
3.  **For private repositories,** expand the "🔑 Private Repository Access" section and paste your Personal Access Token (PAT).
4.  (Optional) De-select any file extensions you wish to exclude from the context. All common extensions are included by default.
5.  Click the **"🚀 Generate Intelligent Context"** button.
6.  Wait for the processing to complete. The full context will be displayed on the page.
7.  Use the **"📥 Download Context.md"** button to save the output and feed it to your favorite LLM!

## 📝 Example Output Structure

The generated output is a single, enriched Markdown file designed to be easily parsed by an LLM.

```markdown
# LLM CONTEXT SNAPSHOT
- **Repository:** https://github.com/user/my-python-app
- **Snapshot Timestamp:** 2024-05-18 10:30:00 UTC
- **Last Commit Hash:** a1b2c3d4e5f6g7h8i9j0
- **Last Commit Message:** "feat: Implement user authentication"
- **Detected Technology Stack:** Python
---

# 1. Project Dependencies Analysis

**Dependencies (`requirements.txt`):**
```
streamlit==1.33.0
gitpython==3.1.43
pyyaml==6.0.1
```

---
# 2. Repository File Structure

```
📂 my-python-app
├── 📄 .gitignore
├── 📄 app.py
├── 📄 README.md
└── 📄 requirements.txt
```

---
# 3. File Contents

--- FILE: README.md [📖 Documentation] (Lines: 25 | Chars: 850) ---
```markdown
# My Awesome Project
This is a project that does amazing things...
```

--- FILE: app.py [⭐ Likely Project Entry Point] (Lines: 152 | Chars: 4891 | Funcs/Classes: 6) ---
```python
import streamlit as st
from utils import helper_function

st.title("My App")
# ... rest of the file content
```
---

## 💻 Running Locally

To run this application on your local machine, follow these steps.

**Prerequisites:**
*   Python 3.8+
*   Git command-line tool

**Setup:**

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
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

3.  **Install the dependencies:**
    The application has additional dependencies for parsing different configuration files.
    ```bash
    pip install -r requirements.txt
    ```
    Your `requirements.txt` should contain:
    ```
    streamlit
    GitPython
    gitignore-parser
    tomli
    PyYAML
    ```

4.  **Run the Streamlit app:**
    ```bash
    streamlit run app.py
    ```

The application should now be running and accessible in your web browser at `http://localhost:8501`.

## 🛠️ Technologies Used

*   **Framework:** [Streamlit](https://streamlit.io/)
*   **Language:** Python 3
*   **Git Operations:** [GitPython](https://gitpython.readthedocs.io/en/stable/)
*   **File Parsing:** [gitignore-parser](https://pypi.org/project/gitignore-parser/), [tomli](https://pypi.org/project/tomli/), [PyYAML](https://pypi.org/project/PyYAML/)

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## 💡 Future Ideas

*   **Token Counter:** Add a `tiktoken`-based counter to estimate API costs for different models.
*   **Branch/Commit Selection:** Allow cloning a specific branch or commit hash for historical analysis.
*   **Direct AI Summary:** Integrate an optional LLM call to generate a high-level summary of the generated context.
*   **Broader Git Service Support:** Add specific helpers for GitLab and BitBucket private repo authentication.