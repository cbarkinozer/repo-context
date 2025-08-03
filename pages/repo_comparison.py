import streamlit as st
import pandas as pd
from src.repo_context.gpqs_calculator import run_gpqs_analysis

# --- Page Configuration ---
st.set_page_config(
    page_title="GPQS Project Comparison",
    page_icon="⭐",
    layout="wide"
)

st.title("⭐ GPQS Project Comparison Tool")
st.markdown("""
Analyze and compare multiple GitHub repositories using the **GitHub Project Quality & Success (GPQS)** metric. This score provides a holistic view of a project's health and viability.
""")

# --- Inputs ---
st.subheader("Enter Repository URLs")
repo_urls_text = st.text_area(
    "Paste one GitHub repository URL per line",
    placeholder="https://github.com/facebook/react\nhttps://github.com/vuejs/vue\nhttps://github.com/angular/angular",
    height=150,
    label_visibility="collapsed"
)

with st.expander("🔑 GitHub Access Token (Highly Recommended)"):
    access_token = st.text_input(
        "GitHub Personal Access Token (PAT)",
        type="password",
        help="A token is crucial to avoid API rate limits when analyzing multiple repos. Create one at https://github.com/settings/tokens with 'public_repo' scope."
    )

if 'results' not in st.session_state:
    st.session_state.results = None
    st.session_state.raw_data = None

# --- Main Logic ---
if st.button("🚀 Analyze and Compare Repositories", use_container_width=True):
    repo_urls = [url.strip() for url in repo_urls_text.split('\n') if url.strip()]

    if not repo_urls:
        st.warning("Please enter at least one repository URL.")
        st.session_state.results = None # Clear previous results
    else:
        all_scores = []
        all_raw_data = {}
        progress_bar = st.progress(0, "Starting Analysis...")
        
        for i, url in enumerate(repo_urls):
            repo_name = '/'.join(url.split('/')[-2:])
            progress_bar.progress((i) / len(repo_urls), f"({i+1}/{len(repo_urls)}) Analyzing {repo_name}...")
            
            scores, raw_data, error = run_gpqs_analysis(url, gh_token=access_token)
            
            if error:
                st.error(f"Could not analyze {repo_name}: {error}")
            else:
                all_scores.append(scores)
                all_raw_data[raw_data['repo_name']] = raw_data
        
        progress_bar.progress(1.0, "Analysis Complete!")

        if all_scores:
            st.session_state.results = all_scores
            st.session_state.raw_data = all_raw_data
        else:
            st.session_state.results = None


# --- Display Results ---
if st.session_state.results:
    st.subheader("📊 Comparison Results")
    st.info("Click on column headers to sort the table.")

    df = pd.DataFrame(st.session_state.results).set_index("Repository")
    
    # Define columns to format
    score_cols = [col for col in df.columns if 'Score' in col]
    raw_cols = [col for col in df.columns if col not in score_cols]

    # Apply styling
    st.dataframe(df.style
        .format("{:,.0f}", subset=raw_cols)
        .format("{:.2f}", subset=score_cols)
        .highlight_max(axis=0, color='#d4edda', subset=score_cols) # Green for max
        .highlight_min(axis=0, color='#f8d7da', subset=score_cols), # Red for min
        use_container_width=True
    )
    
    st.markdown("---")
    st.subheader("🔍 Detailed Raw Data")
    
    for repo_name, data in st.session_state.raw_data.items():
        with st.expander(f"View Raw Data for {repo_name}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**[ Community Engagement ]**")
                st.text(f"  - Stars: {data['stars']:,}\n"
                        f"  - Watchers: {data['watchers']:,}\n"
                        f"  - Forks: {data['forks']:,}\n"
                        f"  - Total Contributors: {data['contributors']:,}")

                st.markdown("**[ Development Activity ]**")
                st.text(f"  - Commits (Last Year): {data['commits_last_year']:,}\n"
                        f"  - Releases (Last Year): {data['releases_last_year']:,}\n"
                        f"  - Days Since Last Commit: {data['days_since_commit']}")

                st.markdown("**[ Project Management ]**")
                st.text(f"  - Avg Days to Close Issue: {data['avg_days_close']:.2f}\n"
                        f"  - Avg Days to Merge PR: {data['avg_days_merge']:.2f}\n"
                        f"  - Merged PRs (last 100): {data['merged_prs']}\n"
                        f"  - Open Issues: {data['open_issues']:,}")

            with col2:
                st.markdown("**[ Code Quality ]**")
                st.text(f"  - CI/CD Workflow Detected: {data['has_ci']}\n"
                        f"  - Test Setup Detected: {data['has_tests_in_tree']}")

                st.markdown("**[ Documentation & Usability ]**")
                st.text(f"  - README Exists: {data.get('readme_size', 0) > 0}\n"
                        f"  - CONTRIBUTING.md Exists: {data['has_contrib']}\n"
                        f"  - Code of Conduct Exists: {data['has_coc']}\n"
                        f"  - LICENSE File Exists: {data['has_license']}")