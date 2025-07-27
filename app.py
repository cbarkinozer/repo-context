# app.py
import streamlit as st

st.set_page_config(
    page_title="Repo Context Tools",
    page_icon="🛠️",
    layout="wide"
)

st.title("Welcome to Repo Context Tools! 🛠️")
st.markdown("""
This application provides a suite of tools for analyzing GitHub repositories.

Use the navigation sidebar on the left to select a tool:

- **Repo Context Generator:** Creates a detailed, LLM-consumable text file from a repository's contents.
- **Repo Comparison:** Analyzes and compares multiple repositories based on the GitHub Project Quality & Success (GPQS) metric.

### What is GPQS?
The **GitHub Project Quality & Success (GPQS)** score is a weighted metric designed to provide a holistic view of a project's quality and health. It considers factors like community engagement, development activity, code quality, documentation, and project management.


**GPQS Score** =
(0.35 * **Community Engagement Score**) +
(0.35 * **Development Activity Score**) +
(0.15 * **Code Quality Score**) +
(0.10 * **Documentation Score**) +
(0.05 * **Project Management Score**)

Where

### Detailed Score Breakdown:

*   **Community Engagement Score** (Weight: 35%)
    *   Measures project popularity and its ability to attract collaborators.
    *   `= (0.4 * Star & Watcher Score) + (0.3 * Fork Score) + (0.3 * Contributor Score)`

*   **Development Activity Score** (Weight: 35%)
    *   Measures the recent momentum and maintenance of the project.
    *   `= (0.5 * Commit & Release Score) + (0.5 * Codebase Recency Score)`
        *   `Commit & Release Score` is based on the number of commits and releases in the last year.
        *   `Codebase Recency Score` is based on the time since the last commit.

*   **Code Quality Score** (Weight: 15%)
    *   Focuses on strong, verifiable signals of quality practices. This score is simplified to be more robust and less prone to detection errors.
    *   `= (0.5 * CI/CD Score) + (0.5 * Testing Score)`
        *   **CI/CD Score:** 100 points if a `.github/workflows` directory exists, 0 otherwise.
        *   **Testing Score:** 100 points if common test directories (`tests/`, `spec/`, `src/test/`, etc.) or file patterns (`*_test.py`, `*.spec.js`, etc.) are found *anywhere* in the repository's file tree, 0 otherwise.

*   **Documentation Score** (Weight: 10%)
    *   Prioritizes a high-quality README as the most critical piece of documentation for user adoption.
    *   `= (0.7 * README Score) + (0.3 * Community Files Score)`
        *   **README Score:** A tiered score from 0-100 based on the `README.md` file size, which acts as a proxy for its completeness (e.g., >10KB = 100 points).
        *   **Community Files Score:** A sum of points for the presence of "good citizen" files: `LICENSE` (50 pts), `CONTRIBUTING.md` (30 pts), and `CODE_OF_CONDUCT.md` (20 pts).

*   **Project Management Score** (Weight: 5%)
    *   Provides a minor signal about the project's responsiveness. It has a low weight as it can be noisy and varies widely between projects.
    *   This score is based on a weighted average of the **Pull Request acceptance rate** and the **average time to merge PRs and close issues**.
        
**Select a page from the sidebar to get started!**
""")