import streamlit as st
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import available_timezones

from src.repo_context.core import generate_context_from_repo, COMMON_EXTENSIONS, parse_github_url

st.set_page_config(
    page_title="GitHub Repo to LLM Context",
    page_icon="🤖",
    layout="wide"
)

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

# Use the imported COMMON_EXTENSIONS constant for the options
selected_extensions = st.multiselect(
    "Select file extensions to include:",
    options=COMMON_EXTENSIONS,
    default=COMMON_EXTENSIONS
)

if st.button("🚀 Generate Intelligent Context", use_container_width=True):
    if repo_url:
        # The spinner now calls the clean, imported function
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

            # Use the imported parse_github_url function to help name the file
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