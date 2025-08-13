# app.py
import streamlit as st

st.set_page_config(
    page_title="Repo Analysis & Comparison Tools",
    page_icon="🛠️",
    layout="wide"
)

st.title("Welcome to Repo Analysis & Comparison Tools! 🛠️")
st.markdown("""
This application provides a suite of tools for analyzing and comparing software projects and developer tools.

Use the navigation sidebar on the left to select a tool:

- **Repo Context Generator:** Creates a detailed, LLM-consumable text file from a repository's contents.
- **Tool & Repo Comparison:** Analyzes and compares tools and repositories using the powerful **GitHub Project Quality & Success (GPQS)** score.

---

### Understanding the GPQS Score

The **GitHub Project Quality & Success (GPQS)** score (on a 0-100 scale) provides a deep-dive analysis into the health and quality of a project. For open-source projects, it analyzes the GitHub repository directly. For closed-source tools, it calculates a limited score based on public community signals.

**GPQS Score** =
(0.35 * **Community Engagement Score**) +
(0.35 * **Development Activity Score**) +
(0.15 * **Code Quality Score**) +
(0.10 * **Documentation Score**) +
(0.05 * **Project Management Score**)

<details>
<summary>Click to see the detailed GPQS breakdown</summary>

*   **Community Engagement Score** (Weight: 35%)
    *   Measures project popularity and its ability to attract collaborators, combining both on-platform and off-platform signals.
    *   **On-Platform signals** include Stars, Forks, and Contributor counts.
    *   **Off-Platform signals** include Google Trends search interest and YouTube video mentions.

*   **Development Activity Score** (Weight: 35%)
    *   Measures the recent momentum and maintenance of the project.
    *   Based on commit frequency, release cadence, and time since the last commit.

*   **Code Quality Score** (Weight: 15%)
    *   Focuses on strong, verifiable signals of quality practices.
    *   Based on the presence of CI/CD workflows and a testing infrastructure.

*   **Documentation Score** (Weight: 10%)
    *   Prioritizes a high-quality README and the presence of community health files (`LICENSE`, `CONTRIBUTING.md`, etc.).

*   **Project Management Score** (Weight: 5%)
    *   Provides a minor signal about the project's responsiveness.
    *   Based on PR acceptance rate and the average time to merge PRs and close issues.
</details>

<br>

**Select a page from the sidebar to get started!**
""")