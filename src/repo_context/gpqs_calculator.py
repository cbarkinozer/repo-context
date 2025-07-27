# Filename: gpq_analyzer_manual.py

import requests
import math
import os
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# It's highly recommended to use a GitHub Personal Access Token.
# Create one at https://github.com/settings/tokens (select 'public_repo' scope)
GH_TOKEN = os.getenv('GH_TOKEN')
HEADERS = {'Authorization': f'token {GH_TOKEN}'} if GH_TOKEN else {}
API_URL = 'https://api.github.com'

# --- MANUAL OVERRIDES SECTION ---
# For metrics that are difficult to assess automatically, you can provide values here.
# Set a value to None to let the script attempt to calculate it automatically.
MANUAL_OVERRIDES = {
    # Score (0-100) for the quality/completeness of the README and CONTRIBUTING files.
    "readme_contrib_score": None,

    # Score (0-100) based on the presence of a linter config file.
    "linter_score": None,
    
    # Score (0-100) reflecting test suite existence and CI integration.
    # (e.g., 50 for CI file, 50 for tests folder = 100)
    "testing_ci_score": None,

    # Manually enter the number of alerts from the repo's "Security" > "Dependabot" tab.
    "dependency_critical_alerts": None,
    "dependency_high_alerts": None,
}


# --- GITHUB API HELPER FUNCTIONS ---

def get_repo_data(owner, repo):
    """Fetches the main repository data."""
    url = f"{API_URL}/repos/{owner}/{repo}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_contributors_count(owner, repo):
    """Fetches the total number of contributors."""
    url = f"{API_URL}/repos/{owner}/{repo}/contributors?per_page=1&anon=true"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    if 'Link' in response.headers:
        link_header = response.headers['Link']
        try:
            return int(link_header.split('>; rel="last"')[0].split('page=')[-1])
        except (ValueError, IndexError):
            return 1 # If parsing fails, there's likely only one page of contributors.
    else: # If no 'Link' header, the number of contributors is on the first page
        return len(response.json()) if response.json() else 0


def get_commit_activity(owner, repo):
    """Fetches commit and release activity for the last year."""
    one_year_ago = datetime.now() - timedelta(days=365)
    
    # Commits (approximated from the link header, as fetching all is too slow)
    url_commits = f"{API_URL}/repos/{owner}/{repo}/commits?since={one_year_ago.isoformat()}&per_page=1"
    response_commits = requests.get(url_commits, headers=HEADERS)
    response_commits.raise_for_status()
    commits_last_year = 0
    if 'Link' in response_commits.headers:
        try:
            commits_last_year = int(response_commits.headers['Link'].split('>; rel="last"')[0].split('page=')[-1])
        except (ValueError, IndexError):
             commits_last_year = 0
    
    # Releases
    url_releases = f"{API_URL}/repos/{owner}/{repo}/releases?per_page=100"
    releases_json = requests.get(url_releases, headers=HEADERS).json()
    releases_last_year = sum(1 for r in releases_json if isinstance(r, dict) and datetime.strptime(r['published_at'], '%Y-%m-%dT%H:%M:%SZ') > one_year_ago)
    
    return commits_last_year, releases_last_year

def check_file_existence(owner, repo, path):
    """Checks if a file or directory exists in the repo."""
    url = f"{API_URL}/repos/{owner}/{repo}/contents/{path}"
    response = requests.get(url, headers=HEADERS)
    return response.status_code == 200

def get_project_management_stats(owner, repo):
    """Fetches stats for the 100 most recent closed issues and pull requests."""
    # Issues
    url_issues = f"{API_URL}/repos/{owner}/{repo}/issues?state=closed&per_page=100"
    issues = requests.get(url_issues, headers=HEADERS).json()
    total_days_to_close, closed_issue_count = 0, 0
    for issue in issues:
        if isinstance(issue, dict) and 'pull_request' not in issue:
            created = datetime.strptime(issue['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            closed = datetime.strptime(issue['closed_at'], '%Y-%m-%dT%H:%M:%SZ')
            total_days_to_close += (closed - created).days
            closed_issue_count += 1
    avg_days_to_close = (total_days_to_close / closed_issue_count) if closed_issue_count > 0 else 0

    # Pull Requests
    url_prs = f"{API_URL}/repos/{owner}/{repo}/pulls?state=closed&per_page=100"
    prs = requests.get(url_prs, headers=HEADERS).json()
    total_days_to_merge, merged_prs, closed_unmerged_prs = 0, 0, 0
    for pr in prs:
        if isinstance(pr, dict) and pr['merged_at']:
            created = datetime.strptime(pr['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            merged = datetime.strptime(pr['merged_at'], '%Y-%m-%dT%H:%M:%SZ')
            total_days_to_merge += (merged - created).days
            merged_prs += 1
        elif isinstance(pr, dict):
            closed_unmerged_prs += 1
    avg_days_to_merge = (total_days_to_merge / merged_prs) if merged_prs > 0 else 0
    
    return avg_days_to_close, avg_days_to_merge, merged_prs, closed_unmerged_prs

# --- SCORING FUNCTIONS ---

def calculate_community_score(stars, watchers, forks, contributors):
    score_stars = min(100, math.log10(stars + watchers + 1) * 20)
    score_forks = min(100, math.log10(forks + 1) * 25)
    score_contributors = min(100, math.log10(contributors + 1) * 30)
    return (0.4 * score_stars) + (0.3 * score_forks) + (0.3 * score_contributors)

def calculate_development_score(commits_last_year, releases_last_year, last_commit_date):
    score_frequency = min(100, (commits_last_year / 50) + (releases_last_year * 10))
    days_since_commit = (datetime.now() - datetime.strptime(last_commit_date, '%Y-%m-%dT%H:%M:%SZ')).days
    score_recency = max(0, 100 - (days_since_commit * 2))
    return (0.5 * score_frequency) + (0.5 * score_recency)

def calculate_code_quality_score(repo_checks):
    # Testing & CI Score
    score_testing_ci = MANUAL_OVERRIDES['testing_ci_score']
    if score_testing_ci is None:
        score_testing_ci = (50 if repo_checks['has_ci'] else 0) + (50 if repo_checks['has_tests'] else 0)

    # Linter Score
    score_linter = MANUAL_OVERRIDES['linter_score']
    if score_linter is None:
        score_linter = 100 if repo_checks['has_linter'] else 0

    # Dependency Health Score
    crit_alerts = MANUAL_OVERRIDES['dependency_critical_alerts']
    high_alerts = MANUAL_OVERRIDES['dependency_high_alerts']
    if crit_alerts is not None and high_alerts is not None:
        score_dependency_health = max(0, 100 - (crit_alerts * 10) - (high_alerts * 5))
    else:
        score_dependency_health = 75 # Assume "good" if not provided, as API can't get this
    
    return (0.4 * score_testing_ci) + (0.3 * score_linter) + (0.3 * score_dependency_health)

def calculate_documentation_score(repo_data, repo_checks):
    # README & Contributing Guide Score
    score_readme_contrib = MANUAL_OVERRIDES['readme_contrib_score']
    if score_readme_contrib is None:
        # Automatic: 70 for a decent README, 30 for a CONTRIBUTING file
        score_readme_contrib = (70 if repo_data.get('size', 0) > 10 else 20) + (30 if repo_checks['has_contrib'] else 0)

    # Documentation Website Score
    score_doc_website = 100 if repo_data.get('homepage') else 0
    
    # Community Health Files Score
    community_files_score = 0
    if repo_checks['has_coc']: community_files_score += 33.33
    if repo_checks['has_license']: community_files_score += 33.33
    if repo_checks['has_template']: community_files_score += 33.33

    return (0.5 * score_readme_contrib) + (0.3 * score_doc_website) + (0.2 * community_files_score)

def calculate_project_management_score(repo_data, pm_stats):
    avg_days_close, avg_days_merge, merged_prs, closed_unmerged_prs = pm_stats
    
    # Issue Management
    open_issues = repo_data.get('open_issues_count', 0)
    total_issues = open_issues + closed_unmerged_prs # Approximation based on recent data
    issue_closure_rate = (closed_unmerged_prs / total_issues) * 100 if total_issues > 0 else 0
    time_to_close_score = 100 / (avg_days_close + 1)
    issue_mgmt_score = (0.6 * issue_closure_rate) + (0.4 * time_to_close_score)

    # PR Management
    total_prs = merged_prs + closed_unmerged_prs
    pr_acceptance_rate = (merged_prs / total_prs) * 100 if total_prs > 0 else 0
    time_to_merge_score = 100 / (avg_days_merge + 1)
    pr_mgmt_score = (0.5 * pr_acceptance_rate) + (0.5 * time_to_merge_score)
    
    return (0.6 * issue_mgmt_score) + (0.4 * pr_mgmt_score)

def main():
    """Main function to calculate and display the GPQS score."""
    if not GH_TOKEN:
        print("Warning: GH_TOKEN environment variable not set. Running unauthenticated with a low rate limit.\n")

    repo_url_input = input("Enter the full GitHub repository URL (e.g., https://github.com/owner/repo): ")
    
    try:
        if not repo_url_input.startswith("https://github.com/"):
            raise ValueError("Invalid GitHub repository URL.")
        
        parts = repo_url_input.strip('/').split('/')
        owner, repo = parts[-2], parts[-1]
        
        print(f"\nAnalyzing repository: {owner}/{repo}\n")

        # --- DATA GATHERING ---
        repo_data = get_repo_data(owner, repo)
        contributors_count = get_contributors_count(owner, repo)
        commits_last_year, releases_last_year = get_commit_activity(owner, repo)
        pm_stats = get_project_management_stats(owner, repo)
        
        repo_checks = {
            'has_ci': check_file_existence(owner, repo, '.github/workflows'),
            'has_tests': check_file_existence(owner, repo, 'tests') or check_file_existence(owner, repo, 'test'),
            'has_linter': check_file_existence(owner, repo, '.eslintrc') or check_file_existence(owner, repo, 'pyproject.toml') or check_file_existence(owner, repo, '.rubocop.yml'),
            'has_contrib': check_file_existence(owner, repo, 'CONTRIBUTING.md'),
            'has_coc': check_file_existence(owner, repo, 'CODE_OF_CONDUCT.md'),
            'has_license': bool(repo_data.get('license')),
            'has_template': check_file_existence(owner, repo, '.github/ISSUE_TEMPLATE') or check_file_existence(owner, repo, '.github/pull_request_template.md')
        }

        # --- CALCULATE SCORES ---
        community_score = calculate_community_score(
            repo_data.get('stargazers_count', 0), repo_data.get('subscribers_count', 0),
            repo_data.get('forks_count', 0), contributors_count
        )
        development_score = calculate_development_score(
            commits_last_year, releases_last_year, repo_data.get('pushed_at')
        )
        code_quality_score = calculate_code_quality_score(repo_checks)
        documentation_score = calculate_documentation_score(repo_data, repo_checks)
        project_management_score = calculate_project_management_score(repo_data, pm_stats)

        # --- FINAL GPQS SCORE ---
        gpqs_score = (
            (0.25 * community_score) + (0.25 * development_score) +
            (0.20 * code_quality_score) + (0.15 * documentation_score) +
            (0.15 * project_management_score)
        )

        # --- DISPLAY RESULTS ---
        print("--- DETAILED SCORES (out of 100) ---")
        print(f"Community Engagement:    {community_score:.2f}")
        print(f"Development Activity:    {development_score:.2f}")
        print(f"Code Quality:            {code_quality_score:.2f}")
        print(f"Documentation & Usability: {documentation_score:.2f}")
        print(f"Project Management:      {project_management_score:.2f}")
        print("--------------------------------------")
        print(f"FINAL GPQS SCORE: {gpqs_score:.2f} / 100")
        print("--------------------------------------")

    except requests.exceptions.HTTPError as e:
        print(f"Error fetching data from GitHub: {e}")
        if e.response.status_code == 403:
            print("You may have hit the GitHub API rate limit. Please set a GH_TOKEN environment variable.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()