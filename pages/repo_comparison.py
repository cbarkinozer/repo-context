# pages/repo_comparison.py

import streamlit as st
import pandas as pd
from urllib.parse import urlparse

from src.repo_context.gpqs_calculator import run_comparison_analysis, TOOL_MAPPING

st.set_page_config(
    page_title="Tool & Repo Comparison",
    page_icon="⭐",
    layout="wide"
)

st.title("⭐ AI Tool & GitHub Repo Comparison")
st.markdown("""
Analyze and compare popular AI developer tools and public GitHub repositories using the **GitHub Project Quality & Success (GPQS)** score.
This score now includes broader web popularity signals for a more holistic view.
""")

st.subheader("1. Select from Close Source Projects")
available_tools = list(TOOL_MAPPING.keys())
selected_tools = st.multiselect(
    "Deselect any tools you wish to exclude from the analysis:",
    options=available_tools,
    default=available_tools,
    label_visibility="collapsed"
)

st.subheader("2. Add Open Source GitHub Repositories")
custom_repo_urls_text = st.text_area(
    "Paste one public GitHub repository URL per line to add it to the comparison:",
    placeholder="https://github.com/facebook/react\nhttps://github.com/torvalds/linux",
    height=100,
    label_visibility="collapsed"
)

with st.expander("🔑 API Keys (Highly Recommended for Accurate Results)"):
    st.info("""
    Provide API keys to avoid rate limits and get complete data.
    You can add them to a `.env` file in the project root for them to be loaded automatically.
    - `GITHUB_ACCESS_TOKEN`: Create at https://github.com/settings/tokens
    - `YOUTUBE_API_KEY`: Get from the Google Cloud Console
    """)
    gh_token = st.text_input("GitHub Personal Access Token (PAT)", type="password", placeholder="Loaded from .env if present")
    yt_key = st.text_input("YouTube Data API v3 Key", type="password", placeholder="Loaded from .env if present")

if 'scores' not in st.session_state:
    st.session_state.scores = None
    st.session_state.raw_data = None

if st.button("🚀 Analyze and Compare", use_container_width=True):
    tools_to_run = {tool: TOOL_MAPPING[tool] for tool in selected_tools}
    custom_urls = [url.strip() for url in custom_repo_urls_text.split('\n') if url.strip()]
    for url in custom_urls:
        try:
            path_parts = urlparse(url).path.strip('/').split('/')
            if len(path_parts) >= 2:
                repo_path = f"{path_parts[0]}/{path_parts[1]}"
                repo_name = path_parts[1]
                tools_to_run[repo_name] = { # Use repo name as key for display
                    "repo": repo_path, "trends_term": repo_name, "youtube_term": f"{repo_name} tutorial"
                }
            else:
                st.warning(f"Could not parse a valid repository from URL: {url}")
        except Exception as e:
            st.error(f"Error parsing custom URL {url}: {e}")

    if not tools_to_run:
        st.warning("Please select at least one tool or add a repository URL.")
        st.session_state.scores = None
    else:
        with st.spinner("The robots are gathering data from GitHub, Google, and YouTube... This may take a moment."):
            scores, raw_data = run_comparison_analysis(
                gh_token=gh_token or None,
                youtube_key=yt_key or None,
                tools_to_analyze=tools_to_run
            )
        st.session_state.scores = scores
        st.session_state.raw_data = raw_data
        st.progress(1.0, "Analysis Complete!")


if st.session_state.scores:
    st.subheader("📊 Comparison Results")
    st.info("Click on column headers to sort. 'N/A' means a metric isn't applicable (e.g., for closed-source tools).")

    df = pd.DataFrame(st.session_state.scores)
    
    column_order = [
        "Tool", "GPQS Score", "Community Score", "Development Score",
        "Stars", "Forks", "YouTube Mentions", "Google Trends",
        "Code Quality Score", "Documentation Score", "Project Mgmt Score"
    ]
    
    # Reorder DF columns based on what's available
    existing_columns = [col for col in column_order if col in df.columns]
    df = df[existing_columns]
    df = df.sort_values(by="GPQS Score", ascending=False).set_index("Tool")
    
    # Define columns for formatting
    score_cols = [col for col in df.columns if 'Score' in col or 'Trends' in col]
    raw_cols = [col for col in df.columns if col not in score_cols]

    # Robustly convert columns to numeric before formatting to prevent errors
    for col in score_cols + raw_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    st.dataframe(df.style
        .format("{:,.0f}", subset=raw_cols, na_rep="N/A")
        .format("{:.2f}", subset=score_cols, na_rep="N/A")
        .highlight_max(axis=0, color='#d4edda', subset=score_cols)
        .highlight_min(axis=0, color='#f8d7da', subset=score_cols),
        use_container_width=True
    )

if st.session_state.raw_data:
    st.markdown("---")
    st.subheader("🔍 Detailed Raw Data")
    
    for tool_name, data in st.session_state.raw_data.items():
        with st.expander(f"View Raw Data for {tool_name}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**[ Community Engagement ]**")
                st.text(f"  - Stars: {data.get('stars', 'N/A'):,}\n"
                        f"  - Watchers: {data.get('watchers', 'N/A'):,}\n"
                        f"  - Forks: {data.get('forks', 'N/A'):,}\n"
                        f"  - Total Contributors: {data.get('contributors', 'N/A'):,}\n"
                        f"  - YouTube Videos: {data.get('youtube_videos', 'N/A'):,}\n"
                        f"  - Google Trends Interest: {data.get('trends_interest', 'N/A'):.2f}")

                st.markdown("**[ Development Activity ]**")
                st.text(f"  - Commits (Last Year): {data.get('commits_last_year', 'N/A'):,}\n"
                        f"  - Releases (Last Year): {data.get('releases_last_year', 'N/A'):,}\n"
                        f"  - Days Since Last Commit: {data.get('days_since_commit', 'N/A')}")

            with col2:
                st.markdown("**[ Code Quality ]**")
                st.text(f"  - CI/CD Workflow Detected: {data.get('has_ci', 'N/A')}\n"
                        f"  - Test Setup Detected: {data.get('has_tests_in_tree', 'N/A')}")

                st.markdown("**[ Documentation & Usability ]**")
                st.text(f"  - README Size (bytes): {data.get('readme_size', 0):,}\n"
                        f"  - CONTRIBUTING.md Exists: {data.get('has_contrib', 'N/A')}\n"
                        f"  - Code of Conduct Exists: {data.get('has_coc', 'N/A')}\n"
                        f"  - LICENSE File Exists: {data.get('has_license', 'N/A')}")
                
                st.markdown("**[ Project Management ]**")
                st.text(f"  - Avg Days to Close Issue: {data.get('avg_days_close', 'N/A'):.2f}\n"
                        f"  - Avg Days to Merge PR: {data.get('avg_days_merge', 'N/A'):.2f}\n"
                        f"  - Merged PRs (last 100): {data.get('merged_prs', 'N/A')}\n"
                        f"  - Open Issues: {data.get('open_issues', 'N/A'):,}")