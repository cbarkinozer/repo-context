# GitHub Repo to LLM Context Generator

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-streamlit-app-url.streamlit.app/) <!--- TODO: Replace with your deployed app URL -->

A Streamlit web application that clones a public GitHub repository and generates a single, well-structured text file. This file is optimized to be used as a comprehensive and clean context for Large Language Models (LLMs) like GPT-4, Claude, or Llama.

## The Problem

When working with Large Language Models on a software project, providing the full context of a repository is challenging:

1.  **Limited Context Windows:** LLMs can't read an entire codebase at once.
2.  **Tedious Manual Work:** Manually copying and pasting dozens of files is slow and error-prone.
3.  **Irrelevant "Noise":** A raw dump includes useless "noise" for an LLM, such as `node_modules`, `__pycache__`, virtual environments, and build artifacts, which wastes precious context space.
4.  **Lack of Structure:** A simple concatenation of files makes it hard for the LLM to distinguish where one file ends and another begins.

This tool solves these problems by creating a clean, structured, and relevant snapshot of your repository's current state.


## ✨ Key Features

*   **Shallow Clone:** Quickly clones only the latest commit of a repository to be fast and resource-efficient.
*   **Intelligent Filtering:**
    *   Automatically respects the repository's `.gitignore` file.
    *   Allows users to select which file extensions to include (e.g., `.py`, `.js`, `.md`).
    *   Excludes common noise directories like `.git`, `venv`, etc. by default.
*   **Rich Metadata Header:** The generated context starts with a helpful header including the repository URL, a timestamp, and the latest commit hash and message. This tells the LLM exactly what "state" it's looking at.
*   **Structured Output:** The output is formatted in clean Markdown with:
    *   A `tree`-like file structure overview.
    *   Clear delimiters (`--- FILE: path/to/file ---`) for each file.
    *   Code blocks with language identifiers for better parsing and syntax highlighting.
*   **Simple Web UI:** Built with Streamlit for a clean, easy-to-use interface. No command line needed.

## 🚀 Live Demo

**Try the app live here:** [https://repo-context.streamlit.app/](https://repo-context.streamlit.app/)

## 📋 How to Use

1.  Navigate to the deployed Streamlit application.
2.  Paste the full URL of a **public** GitHub repository into the text box.
3.  (Optional) Select or de-select the file extensions you want to include in the context.
4.  Click the **"Generate Context"** button.
5.  Wait for the processing to complete. The full context will be displayed on the page.
6.  You can use the **"Copy to Clipboard"** button or the **"Download Context.md"** button to get the output.
7.  Paste this context into your favorite LLM and start your conversation!

## 📝 Example Output Structure

The generated output is a single Markdown file designed to be easily parsed by an LLM.

```markdown
# LLM CONTEXT SNAPSHOT

- **Repository:** https://github.com/user/repo
- **Snapshot Timestamp:** 2023-10-27 10:30:00 UTC
- **Last Commit Hash:** a1b2c3d4e5f6g7h8i9j0
- **Last Commit Message:** "feat: Implement user authentication"

---

# 1. Repository File Structure

/
|-- .gitignore
|-- README.md
|-- requirements.txt
`-- src/
    |-- __init__.py
    |-- main.py
    `-- utils.py


---

# 2. File Contents

--- FILE: README.md ---
```markdown
# My Awesome Project
This is a project that does amazing things...
```

--- FILE: requirements.txt ---
```
streamlit==1.28.0
gitpython==3.1.40
```

--- FILE: src/main.py ---
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
    ```bash
    pip install -r requirements.txt
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
*   **Ignorefile Parsing:** [gitignore-parser](https://pypi.org/project/gitignore-parser/)

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## 💡 Future Ideas

*   Support for private repositories using a GitHub Personal Access Token (PAT).
*   Add a token counter to estimate cost/usage for different LLM APIs.
*   Allow cloning a specific branch or commit hash.
*   Direct integration with an LLM API to summarize the generated context.