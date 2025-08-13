# src/repo_context/gpqs_calculator.py
import os
import requests
import math
import time
import pandas as pd
from datetime import datetime, timedelta
from urllib.parse import urlparse
from dotenv import load_dotenv
from pytrends.request import TrendReq
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- SETUP AND CONFIGURATION ---
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
API_URL = 'https://api.github.com'

TOOL_MAPPING = {
    "Cursor AI": {"repo": None, "trends_term": "Cursor AI editor", "youtube_term": "Cursor AI review"},
    "Cline": {"repo": "cline/cline", "trends_term": "Cline AI", "youtube_term": "Cline AI coding"},
    "GitHub Copilot": {"repo": None, "trends_term": "GitHub Copilot", "youtube_term": "GitHub Copilot tutorial"},
    "Gemini CLI": {"repo": "google-gemini/gemini-cli", "trends_term": "Google Gemini CLI", "youtube_term": "Gemini CLI tutorial"},
    "Sourcegraph Cody": {"repo": None, "trends_term": "Sourcegraph Cody", "youtube_term": "Sourcegraph Cody"},
    "Windsurf (Codeium)": {"repo": None, "trends_term": "Codeium", "youtube_term": "Codeium review"},
    "Sourcery AI": {"repo": "sourcery-ai/sourcery", "trends_term": "Sourcery AI", "youtube_term": "Sourcery AI refactoring"},
    "Tabby": {"repo": "TabbyML/tabby", "trends_term": "TabbyML", "youtube_term": "TabbyML self-hosted"},
    "Qodo": {"repo": None, "trends_term": "Qodo AI", "youtube_term": "Qodo AI"},
    "Replit": {"repo": None, "trends_term": "Replit", "youtube_term": "Replit tutorial"},
    "Codex (OpenAI)": {"repo": "openai/codex", "trends_term": "OpenAI Codex", "youtube_term": "OpenAI Codex demo"},
    "CodeRabbit": {"repo": None, "trends_term": "CodeRabbit AI", "youtube_term": "CodeRabbit AI review"},
    "Ellipsis.dev": {"repo": None, "trends_term": "Ellipsis.dev", "youtube_term": "Ellipsis dev AI"},
    "Aider": {"repo": "Aider-AI/aider", "trends_term": "Aider git", "youtube_term": "Aider git tutorial"},
}

# --- API FETCHERS ---

def fetch_youtube_video_count(query, api_key):
    if not api_key: return None
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.search().list(q=query, type='video', part='id', maxResults=1)
        response = request.execute()
        return response.get('pageInfo', {}).get('totalResults')
    except HttpError as e:
        print(f"Error fetching YouTube data for query '{query}': {e}")
        return None

def fetch_google_trends_interest(keywords):
    if not keywords: return pd.Series(dtype=float)
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        pytrends.build_payload(keywords, cat=0, timeframe='today 12-m', geo='', gprop='')
        df = pytrends.interest_over_time()
        return df.mean() if not df.empty else pd.Series(index=keywords, dtype=float)
    except Exception as e:
        print(f"Error fetching Google Trends data: {e}")
        return pd.Series(index=keywords, dtype=float)

def get_repo_data(owner, repo, session):
    url = f"{API_URL}/repos/{owner}/{repo}"
    response = session.get(url)
    response.raise_for_status()
    return response.json()

def get_contributors_count(owner, repo, session):
    url = f"{API_URL}/repos/{owner}/{repo}/contributors?per_page=1&anon=true"
    response = session.get(url)
    response.raise_for_status()
    if 'Link' in response.headers:
        try:
            return int(response.headers['Link'].split('>; rel="last"')[0].split('page=')[-1])
        except (ValueError, IndexError): return 1
    else:
        return len(response.json() or [])

def get_commit_activity(owner, repo, session):
    one_year_ago = datetime.now() - timedelta(days=365)
    url_commits = f"{API_URL}/repos/{owner}/{repo}/commits?since={one_year_ago.isoformat()}&per_page=1"
    response_commits = session.get(url_commits)
    response_commits.raise_for_status()
    commits_last_year = 0
    if 'Link' in response_commits.headers:
        try:
            commits_last_year = int(response_commits.headers['Link'].split('>; rel="last"')[0].split('page=')[-1])
        except (ValueError, IndexError):
             commits_last_year = 0
    url_releases = f"{API_URL}/repos/{owner}/{repo}/releases?per_page=100"
    releases_json = session.get(url_releases).json()
    releases_last_year = sum(1 for r in releases_json if isinstance(r, dict) and r.get('published_at') and datetime.strptime(r['published_at'], '%Y-%m-%dT%H:%M:%SZ') > one_year_ago)
    return commits_last_year, releases_last_year

def get_git_tree(owner, repo, branch, session):
    url = f"{API_URL}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    response = session.get(url)
    if response.status_code == 409: return []
    response.raise_for_status()
    return [item['path'] for item in response.json().get("tree", [])]

def has_tests_in_tree(tree):
    test_dirs = {'test', 'tests', 'spec', 'e2e', 'integration-tests'}
    test_file_suffixes = {'_test.py', '.test.js', '.spec.js', '.test.ts', '.spec.ts'}
    for path in tree:
        parts = path.split('/')
        if any(part in test_dirs for part in parts) or any(path.endswith(suffix) for suffix in test_file_suffixes):
            return True
    return False

def get_readme_size(owner, repo, session):
    url = f"{API_URL}/repos/{owner}/{repo}/readme"
    response = session.get(url)
    return response.json().get("size", 0) if response.status_code == 200 else 0

def check_file_existence(owner, repo, path, session):
    url = f"{API_URL}/repos/{owner}/{repo}/contents/{path}"
    return session.get(url).status_code == 200

def get_project_management_stats(owner, repo, session):
    url_issues = f"{API_URL}/repos/{owner}/{repo}/issues?state=closed&per_page=100"
    issues = session.get(url_issues).json()
    total_days_to_close, closed_issue_count = 0, 0
    for issue in issues:
        if isinstance(issue, dict) and 'pull_request' not in issue and issue.get('closed_at'):
            created = datetime.strptime(issue['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            closed = datetime.strptime(issue['closed_at'], '%Y-%m-%dT%H:%M:%SZ')
            total_days_to_close += (closed - created).days
            closed_issue_count += 1
    avg_days_to_close = (total_days_to_close / closed_issue_count) if closed_issue_count > 0 else 0
    url_prs = f"{API_URL}/repos/{owner}/{repo}/pulls?state=closed&per_page=100"
    prs = session.get(url_prs).json()
    total_days_to_merge, merged_prs, closed_unmerged_prs = 0, 0, 0
    for pr in prs:
        if isinstance(pr, dict) and pr.get('merged_at'):
            created = datetime.strptime(pr['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            merged = datetime.strptime(pr['merged_at'], '%Y-%m-%dT%H:%M:%SZ')
            total_days_to_merge += (merged - created).days
            merged_prs += 1
        elif isinstance(pr, dict):
            closed_unmerged_prs += 1
    avg_days_to_merge = (total_days_to_merge / merged_prs) if merged_prs > 0 else 0
    return avg_days_to_close, avg_days_to_merge, merged_prs, closed_unmerged_prs

# --- SCORING FUNCTIONS ---

def calculate_community_score(data):
    # On-platform (GitHub) signals. Use .get(key, 0) for robustness.
    score_stars = min(100, math.log10(data.get('stars', 0) + 1) * 20)
    score_forks = min(100, math.log10(data.get('forks', 0) + 1) * 25)
    score_contributors = min(100, math.log10(data.get('contributors', 0) + 1) * 30)
    on_platform_score = (0.5 * score_stars) + (0.2 * score_forks) + (0.3 * score_contributors)

    # Off-platform (broader web) signals.
    # Use 'or 0' to safely handle None values from failed API calls.
    youtube_vids = data.get('youtube_videos') or 0
    trends_val = data.get('trends_interest') or 0
    
    score_youtube = min(100, math.log10(youtube_vids + 1) * 20)
    score_trends = trends_val if pd.notna(trends_val) else 0 # Ensure NaN from trends is handled
    off_platform_score = (0.5 * score_youtube) + (0.5 * score_trends)
    
    # Final weighted score
    return (0.6 * on_platform_score) + (0.4 * off_platform_score)

def calculate_development_score(data):
    score_frequency = min(100, (data.get('commits_last_year', 0) / 50) + (data.get('releases_last_year', 0) * 10))
    score_recency = max(0, 100 - (data.get('days_since_commit', 0) * 2))
    return (0.5 * score_frequency) + (0.5 * score_recency)

def calculate_code_quality_score(data):
    ci_score = 100 if data.get('has_ci') else 0
    test_score = 100 if data.get('has_tests_in_tree') else 0
    return (0.5 * ci_score) + (0.5 * test_score)

def calculate_documentation_score(data):
    readme_score = 100 if data.get('readme_size', 0) > 10000 else 70 if data.get('readme_size', 0) > 5000 else 40 if data.get('readme_size', 0) > 1000 else 0
    community_files_score = (50 if data.get('has_license') else 0) + (30 if data.get('has_contrib') else 0) + (20 if data.get('has_coc') else 0)
    return (0.7 * readme_score) + (0.3 * community_files_score)

def calculate_project_management_score(data):
    total_issues = data.get('open_issues', 0) + data.get('closed_unmerged_prs', 0)
    issue_closure_rate = (data.get('closed_unmerged_prs', 0) / total_issues) * 100 if total_issues > 0 else 0
    time_to_close_score = 100 / ((data.get('avg_days_close') or 0) + 1)
    issue_mgmt_score = (0.6 * issue_closure_rate) + (0.4 * time_to_close_score)
    total_prs = data.get('merged_prs', 0) + data.get('closed_unmerged_prs', 0)
    pr_acceptance_rate = (data.get('merged_prs', 0) / total_prs) * 100 if total_prs > 0 else 0
    time_to_merge_score = 100 / ((data.get('avg_days_merge') or 0) + 1)
    pr_mgmt_score = (0.5 * pr_acceptance_rate) + (0.5 * time_to_merge_score)
    return (0.6 * issue_mgmt_score) + (0.4 * pr_mgmt_score)

# --- MAIN ANALYSIS FUNCTIONS ---

def run_gpqs_analysis(session, repo_path, trends_interest, youtube_videos):
    try:
        repo_url = f"https://github.com/{repo_path}"
        owner, repo = repo_path.split('/')
        repo_data = get_repo_data(owner, repo, session)
        default_branch = repo_data.get('default_branch', 'main')
        git_tree = get_git_tree(owner, repo, default_branch, session)
        commits_last_year, releases_last_year = get_commit_activity(owner, repo, session)
        avg_days_close, avg_days_merge, merged_prs, closed_unmerged_prs = get_project_management_stats(owner, repo, session)
        
        raw_data = {
            'repo_name': repo_path,
            'stars': repo_data.get('stargazers_count', 0), 'watchers': repo_data.get('subscribers_count', 0),
            'forks': repo_data.get('forks_count', 0), 'contributors': get_contributors_count(owner, repo, session),
            'commits_last_year': commits_last_year, 'releases_last_year': releases_last_year,
            'days_since_commit': (datetime.now() - datetime.strptime(repo_data.get('pushed_at'), '%Y-%m-%dT%H:%M:%SZ')).days,
            'has_ci': any(p.startswith('.github/workflows') for p in git_tree),
            'has_tests_in_tree': has_tests_in_tree(git_tree), 'readme_size': get_readme_size(owner, repo, session),
            'has_contrib': check_file_existence(owner, repo, 'CONTRIBUTING.md', session),
            'has_coc': check_file_existence(owner, repo, 'CODE_OF_CONDUCT.md', session),
            'has_license': bool(repo_data.get('license')) or check_file_existence(owner, repo, 'LICENSE', session),
            'avg_days_close': avg_days_close, 'avg_days_merge': avg_days_merge,
            'merged_prs': merged_prs, 'closed_unmerged_prs': closed_unmerged_prs,
            'open_issues': repo_data.get('open_issues_count', 0),
            'youtube_videos': youtube_videos, 'trends_interest': trends_interest
        }

        community_score = calculate_community_score(raw_data)
        development_score = calculate_development_score(raw_data)
        code_quality_score = calculate_code_quality_score(raw_data)
        documentation_score = calculate_documentation_score(raw_data)
        project_management_score = calculate_project_management_score(raw_data)
        gpqs_score = ((0.35 * community_score) + (0.35 * development_score) + (0.15 * code_quality_score) +
                      (0.10 * documentation_score) + (0.05 * project_management_score))

        scores = {
            "GPQS Score": round(gpqs_score, 2), "Community Score": round(community_score, 2),
            "Development Score": round(development_score, 2), "Code Quality Score": round(code_quality_score, 2),
            "Documentation Score": round(documentation_score, 2), "Project Mgmt Score": round(project_management_score, 2),
            "Stars": raw_data['stars'], "Forks": raw_data['forks'],
            "YouTube Mentions": raw_data['youtube_videos'], "Google Trends": raw_data['trends_interest']
        }
        return scores, raw_data, None
    except requests.exceptions.HTTPError as e:
        error_msg = f"API error for {repo_url}: {e}"
        if e.response.status_code == 403: error_msg += "\n(Hint: Rate limit exceeded or invalid PAT.)"
        elif e.response.status_code == 404: error_msg += "\n(Hint: Repository not found.)"
        return None, None, error_msg
    except Exception as e:
        return None, None, f"Unexpected error for {repo_url}: {e}"

def run_comparison_analysis(gh_token, youtube_key, tools_to_analyze):
    all_scores, all_raw_data = [], {}
    session = requests.Session()
    if gh_token:
        session.headers.update({'Authorization': f'token {gh_token}'})

    trends_keywords = [config['trends_term'] for config in tools_to_analyze.values()]
    trends_data = {}
    if trends_keywords:
        print(f"Fetching Google Trends data for: {trends_keywords}...")
        for i in range(0, len(trends_keywords), 5):
            chunk = trends_keywords[i:i+5]
            chunk_data = fetch_google_trends_interest(chunk)
            if chunk_data is not None:
                trends_data.update(chunk_data.to_dict())
            time.sleep(1)

    for tool_name, config in tools_to_analyze.items():
        print(f"\n--- Analyzing: {tool_name} ---")
        youtube_videos = fetch_youtube_video_count(config['youtube_term'], youtube_key)
        trends_interest = trends_data.get(config['trends_term'])

        if config['repo']:
            scores, raw_data, error = run_gpqs_analysis(session, config['repo'], trends_interest, youtube_videos)
            if error:
                print(error)
                scores = {"Tool": tool_name, "GPQS Score": "Error"}
            else:
                scores["Tool"] = tool_name
                all_raw_data[tool_name] = raw_data
            all_scores.append(scores)
        else:
            raw_data_closed = {'youtube_videos': youtube_videos, 'trends_interest': trends_interest}
            community_score = calculate_community_score(raw_data_closed)
            all_scores.append({
                "Tool": tool_name,
                "Community Score": round(community_score, 2),
                "YouTube Mentions": youtube_videos,
                "Google Trends": trends_interest,
                "GPQS Score": "N/A"
            })
        time.sleep(15)
            
    return all_scores, all_raw_data