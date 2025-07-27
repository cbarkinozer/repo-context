# src/repo_context/gpqs_calculator.py
import requests
import math
from datetime import datetime, timedelta
from urllib.parse import urlparse

API_URL = 'https://api.github.com'

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
        link_header = response.headers['Link']
        try:
            return int(link_header.split('>; rel="last"')[0].split('page=')[-1])
        except (ValueError, IndexError):
            return 1
    else:
        content = response.json()
        return len(content) if content else 0

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
    releases_last_year = sum(1 for r in releases_json if isinstance(r, dict) and 'published_at' in r and r['published_at'] and datetime.strptime(r['published_at'], '%Y-%m-%dT%H:%M:%SZ') > one_year_ago)
    return commits_last_year, releases_last_year

def get_git_tree(owner, repo, branch, session):
    url = f"{API_URL}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    response = session.get(url)
    if response.status_code == 409: # Handles empty repository case
        return []
    response.raise_for_status()
    tree = response.json().get("tree", [])
    return [item['path'] for item in tree]

def has_tests_in_tree(tree):
    test_dirs = {'test', 'tests', 'spec', 'e2e', 'integration-tests'}
    test_file_suffixes = {'_test.py', '.test.js', '.spec.js', '.test.ts', '.spec.ts'}
    for path in tree:
        parts = path.split('/')
        if any(part in test_dirs for part in parts):
            return True
        if any(path.endswith(suffix) for suffix in test_file_suffixes):
            return True
    return False

def get_readme_size(owner, repo, session):
    url = f"{API_URL}/repos/{owner}/{repo}/readme"
    response = session.get(url)
    if response.status_code == 200:
        return response.json().get("size", 0)
    return 0

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

def calculate_community_score(data):
    score_stars = min(100, math.log10(data['stars'] + data['watchers'] + 1) * 20)
    score_forks = min(100, math.log10(data['forks'] + 1) * 25)
    score_contributors = min(100, math.log10(data['contributors'] + 1) * 30)
    return (0.4 * score_stars) + (0.3 * score_forks) + (0.3 * score_contributors)

def calculate_development_score(data):
    score_frequency = min(100, (data['commits_last_year'] / 50) + (data['releases_last_year'] * 10))
    score_recency = max(0, 100 - (data['days_since_commit'] * 2))
    return (0.5 * score_frequency) + (0.5 * score_recency)

def calculate_code_quality_score(data):
    ci_score = 100 if data['has_ci'] else 0
    test_score = 100 if data['has_tests_in_tree'] else 0
    return (0.5 * ci_score) + (0.5 * test_score)

def calculate_documentation_score(data):
    readme_size = data.get('readme_size', 0)
    if readme_size > 10000:
        readme_score = 100
    elif readme_size > 5000:
        readme_score = 70
    elif readme_size > 1000:
        readme_score = 40
    else:
        readme_score = 0
    
    community_files_score = (50 if data['has_license'] else 0) + (30 if data['has_contrib'] else 0) + (20 if data['has_coc'] else 0)
    
    return (0.7 * readme_score) + (0.3 * community_files_score)

def calculate_project_management_score(data):
    total_issues = data['open_issues'] + data['closed_unmerged_prs']
    issue_closure_rate = (data['closed_unmerged_prs'] / total_issues) * 100 if total_issues > 0 else 0
    time_to_close_score = 100 / (data['avg_days_close'] + 1)
    issue_mgmt_score = (0.6 * issue_closure_rate) + (0.4 * time_to_close_score)
    total_prs = data['merged_prs'] + data['closed_unmerged_prs']
    pr_acceptance_rate = (data['merged_prs'] / total_prs) * 100 if total_prs > 0 else 0
    time_to_merge_score = 100 / (data['avg_days_merge'] + 1)
    pr_mgmt_score = (0.5 * pr_acceptance_rate) + (0.5 * time_to_merge_score)
    return (0.6 * issue_mgmt_score) + (0.4 * pr_mgmt_score)

def run_gpqs_analysis(repo_url, gh_token=None):
    session = requests.Session()
    if gh_token:
        session.headers.update({'Authorization': f'token {gh_token}'})

    try:
        parsed_url = urlparse(repo_url)
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) < 2:
            return None, None, f"Error: Invalid GitHub URL format: {repo_url}"
        owner, repo = path_parts[0], path_parts[1]

        repo_data = get_repo_data(owner, repo, session)
        default_branch = repo_data.get('default_branch', 'main')
        git_tree = get_git_tree(owner, repo, default_branch, session)
        
        commits_last_year, releases_last_year = get_commit_activity(owner, repo, session)
        avg_days_close, avg_days_merge, merged_prs, closed_unmerged_prs = get_project_management_stats(owner, repo, session)

        raw_data = {
            'repo_name': f"{owner}/{repo}",
            'stars': repo_data.get('stargazers_count', 0),
            'watchers': repo_data.get('subscribers_count', 0),
            'forks': repo_data.get('forks_count', 0),
            'contributors': get_contributors_count(owner, repo, session),
            'commits_last_year': commits_last_year,
            'releases_last_year': releases_last_year,
            'days_since_commit': (datetime.now() - datetime.strptime(repo_data.get('pushed_at'), '%Y-%m-%dT%H:%M:%SZ')).days,
            'has_ci': '.github/workflows' in [path.split('/')[0] + '/' + path.split('/')[1] for path in git_tree if path.startswith('.github/workflows')],
            'has_tests_in_tree': has_tests_in_tree(git_tree),
            'readme_size': get_readme_size(owner, repo, session),
            'has_contrib': check_file_existence(owner, repo, 'CONTRIBUTING.md', session),
            'has_coc': check_file_existence(owner, repo, 'CODE_OF_CONDUCT.md', session),
            'has_license': bool(repo_data.get('license')) or check_file_existence(owner, repo, 'LICENSE', session),
            'avg_days_close': avg_days_close,
            'avg_days_merge': avg_days_merge,
            'merged_prs': merged_prs,
            'closed_unmerged_prs': closed_unmerged_prs,
            'open_issues': repo_data.get('open_issues_count', 0),
        }

        community_score = calculate_community_score(raw_data)
        development_score = calculate_development_score(raw_data)
        code_quality_score = calculate_code_quality_score(raw_data)
        documentation_score = calculate_documentation_score(raw_data)
        project_management_score = calculate_project_management_score(raw_data)

        gpqs_score = (
            (0.35 * community_score) +
            (0.35 * development_score) +
            (0.15 * code_quality_score) +
            (0.10 * documentation_score) +
            (0.05 * project_management_score)
        )

        scores = {
            "Repository": f"{owner}/{repo}",
            "GPQS Score": round(gpqs_score, 2),
            "Community Score": round(community_score, 2),
            "Development Score": round(development_score, 2),
            "Code Quality Score": round(code_quality_score, 2),
            "Documentation Score": round(documentation_score, 2),
            "Project Management Score": round(project_management_score, 2),
            "Stars": raw_data['stars'],
            "Forks": raw_data['forks']
        }
        return scores, raw_data, None

    except requests.exceptions.HTTPError as e:
        error_msg = f"Error analyzing {repo_url}: {e}"
        if e.response.status_code == 403:
            error_msg += "\n(Hint: Rate limit exceeded. Please provide a GitHub PAT.)"
        elif e.response.status_code == 404:
            error_msg += "\n(Hint: Repository not found. Please check the URL.)"
        return None, None, error_msg
    except Exception as e:
        return None, None, f"An unexpected error occurred for {repo_url}: {e}"