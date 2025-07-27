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


### How GPQS is calculated?
**GPQS Score** =
(0.25 * **Community Engagement Score**) +
(0.25 * **Development Activity Score**) +
(0.20 * **Code Quality Score**) +
(0.15 * **Documentation & Usability Score**) +
(0.15 * **Project Management Score**)

Where

- **Community Engagement Score** = (0.4 * min(100, log10(Stars + Watchers + 1) * 20)) + (0.3 * min(100, log10(Forks + 1) * 25)) + (0.3 * min(100, log10(Total Contributors + 1) * 30))  
- **Development Activity Score** = (0.5 * in(100, (Commits in last year / 50) + (Releases in last year * 10))) + (0.5 * max(0, 100 - (Days since last commit * 2)))  
- **Code Quality Score** = (0.4 * (50 points each for existence of CI file and test files)) +(0.3 * (100 for linter configuration file existence else 0))) +(0.3 * max(0, 100 - (Number of critical alerts * 10) - (Number of high alerts * 5)))  
- **Documentation & Usability Score** = (0.5 * (presence and completeness of README.md and CONTRIBUTING.md files))) +(0.3 * (100 for documentation website else 0))) +(0.2 * (33,33 point for each CODE_OF_CONDUCT.md, LICENSE, and an issue/PR template files)))  
- **Project Management Score** = (0.6 * (0.6 * Issue Closure Rate) + (0.4 * (100 / (Avg days to close issue + 1)))) + (0.4 * (0.5 * (Merged PRs / (Merged + Closed Unmerged PRs)) * 100) + (0.5 * (100 / (Avg days to merge PR + 1))))  

        
**Select a page from the sidebar to get started!**
""")