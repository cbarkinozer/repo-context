import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse

# --- Constants & Headers ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
# Delay between requests to be respectful to the server
RATE_LIMIT_DELAY = 1 # seconds

# --- Core Scraping Logic ---

def get_nav_links(base_url, session):
    """Fetches the main page and extracts navigation links from the sidebar."""
    try:
        response = session.get(base_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')

        # Use the semantic <nav> tag for robustness
        nav_menu = soup.find('ul', class_=lambda c: c and 'overflow-y-auto' in c)
        if not nav_menu:
            return [], "Error: Could not find the navigation menu. Searched for a scrollable list (<ul> with class 'overflow-y-auto') but it was not found. The site's HTML structure may have changed."

        links = []
        for a_tag in nav_menu.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)
            # Avoid duplicates and external links
            if full_url not in [link['url'] for link in links] and urlparse(full_url).netloc == urlparse(base_url).netloc:
                link_text = a_tag.get_text(strip=True)
                links.append({'url': full_url, 'title': link_text})

        if not links:
            return [], "Error: Found a potential navigation menu container, but it contained no links. The content might be loaded dynamically after the page loads."

        return links, None
    except requests.exceptions.RequestException as e:
        return [], f"Error fetching the base URL: {e}"
    except Exception as e:
        return [], f"An unexpected error occurred while parsing navigation links: {e}"

def scrape_page_content(url, session):
    """Scrapes the main content from a single page."""
    try:
        time.sleep(RATE_LIMIT_DELAY)
        response = session.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')

        # Use the semantic <main> tag for the primary content
        main_content = soup.find('div', class_=lambda c: c and 'prose-custom' in c)
        if not main_content:
            return None, "Could not find the main content area. Searched for a <div> with class 'prose-custom' but it was not found."

        content_text = main_content.get_text(separator='\n', strip=True)
        return content_text, None
    except requests.exceptions.RequestException as e:
        return None, f"Failed to fetch content from {url}: {e}"
    except Exception as e:
        return None, f"An unexpected error occurred while scraping {url}: {e}"

# --- Streamlit UI ---

st.set_page_config(
    page_title="Deep Wiki Context Generator",
    page_icon="📜",
    layout="wide"
)

st.title("📜 Deep Wiki LLM Context Generator")
st.markdown("""
This tool scrapes a documentation site on [deepwiki.com](https://deepwiki.com/), extracts content from all pages in the sidebar navigation, and compiles it into a single text file.
This is useful for creating a comprehensive context file to feed into LLMs like Google's NotebookLM for tasks like generating a podcast.
""")

deep_wiki_url = st.text_input(
    "Enter a Deep Wiki URL to start scraping",
    placeholder="https://deepwiki.com/google-gemini/gemini-cli"
)

if st.button("🚀 Generate Deep Wiki Context", use_container_width=True):
    if not deep_wiki_url or 'deepwiki.com' not in urlparse(deep_wiki_url).netloc:
        st.warning("Please enter a valid Deep Wiki URL (e.g., https://deepwiki.com/some-topic).")
    else:
        with st.spinner("Initializing scraper and finding navigation links..."):
            session = requests.Session()
            links, error = get_nav_links(deep_wiki_url, session)
            if error:
                st.error(error)
                st.stop()
            
            st.info(f"Found {len(links)} pages to scrape. Starting process...")

        progress_bar = st.progress(0, text="Scraping pages...")
        full_context = []
        errors = []
        
        for i, link_info in enumerate(links):
            url = link_info['url']
            title = link_info['title']
            
            progress_text = f"({i+1}/{len(links)}) Scraping: {title}"
            progress_bar.progress((i + 1) / len(links), text=progress_text)
            
            content, error = scrape_page_content(url, session)
            
            if error:
                errors.append(f"- **{title}** ({url}): {error}")
            elif content:
                # Format the output with a clear header for each page
                full_context.append(f"# {title}\n\n")
                full_context.append(f"Source URL: {url}\n\n")
                full_context.append("---\n\n")
                full_context.append(content)
                full_context.append("\n\n---\n\n")

        progress_bar.progress(1.0, text="Scraping complete! Compiling final context...")

        if not full_context:
            st.error("Could not scrape any content. Please check the URL and the website structure.")
            if errors:
                st.subheader("Scraping Errors:")
                st.markdown("\n".join(errors), unsafe_allow_html=True)
        else:
            final_text = "".join(full_context)
            st.success("Context successfully generated!")
            
            parsed_url = urlparse(deep_wiki_url)
            file_name_slug = parsed_url.path.strip('/').replace('/', '_')
            file_name = f"deep_wiki_{file_name_slug}_context.txt"

            st.download_button(
                label="📥 Download Context as Text File",
                data=final_text,
                file_name=file_name,
                mime="text/plain",
                use_container_width=True
            )
            
            if errors:
                st.warning("Some pages could not be scraped. The generated context might be incomplete.")
                with st.expander("View Scraping Errors"):
                    st.markdown("\n".join(errors), unsafe_allow_html=True)

            st.markdown("### Generated Context Preview:")
            st.text_area("Context", final_text, height=500, label_visibility="collapsed")