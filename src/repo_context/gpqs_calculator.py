import requests
import math
import os
from datetime import datetime, timedelta

# --- CONFIGURATION ---
GH_TOKEN = os.getenv('GH_TOKEN')
HEADERS = {'Authorization': f'token {GH_TOKEN}'} if GH_TOKEN else {}
API_URL = 'https://api.github.com'

# --- MANUAL OVERRIDES SECTION ---
# For metrics that are hard to automate, provide values here.
# Set a value to None to let the script calculate it automatically.
MANUAL_OVERRIDES = {
    "readme_contrib_score": None, # Score (0-100) for README/CONTRIBUTING quality
    "linter_score": None,         # Score (0-100) for linter setup
    "testing_ci_score": None,     # Score (0-100) for testing/CI setup
    "dependency_critical_alerts": None, # Number of critical alerts
    "dependency_high_alerts": None,   # Number of high alerts
}


# --- GITHUB API HELPER FUNCTIONS (No changes from previous version) ---

def get_repo_data(owner, repo):
    url = f"{API_URL}/repos/{owner}/{repo}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_contributors_count(owner, repo):
    url = f"{API_URL}/repos/{owner}/{repo}/contributors?per_page=1&anon=true"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    if 'Link' in response.headers:
        link_header = response.headers['Link']
        try:
            return int(link_header.split('>; rel="last"')[0].split('page=')[-1])
        except (ValueError, IndexError):
            return 1
    else:
        return len(response.json()) if response.json() else 0

def get_commit_activity(owner, repo):
    one_year_ago = datetime.now() - timedelta(days=365)
    url_commits = f"{API_URL}/repos/{owner}/{repo}/commits?since={one_year_ago.isoformat()}&per_page=1"
    response_commits = requests.get(url_commits, headers=HEADERS)
    response_commits.raise_for_status()
    commits_last_year = 0
    if 'Link' in response_commits.headers:
        try:
            commits_last_year = int(response_commits.headers['Link'].split('>; rel="last"')[0].split('page=')[-1])
        except (ValueError, IndexError):
             commits_last_year = 0
    url_releases = f"{API_URL}/repos/{owner}/{repo}/releases?per_page=100"
    releases_json = requests.get(url_releases, headers=HEADERS).json()
    releases_last_year = sum(1 for r in releases_json if isinstance(r, dict) and datetime.strptime(r['published_at'], '%Y-%m-%dT%H:%M:%SZ') > one_year_ago)
    return commits_last_year, releases_last_year

def check_file_existence(owner, repo, paths):
    """Checks if any of the given file paths exist in the repo."""
    if isinstance(paths, str):
        paths = [paths]
    for path in paths:
        url = f"{API_URL}/repos/{owner}/{repo}/contents/{path}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return True
    return False

def get_project_management_stats(owner, repo):
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

# --- UPDATED: FUNCTION TO PRINT RAW DATA ---

def print_raw_data(data):
    """Prints the collected raw data points before the scores."""
    print("--- RAW DATA COLLECTED ---")
    print("[ Community Engagement ]")
    print(f"  > Stars: {data['stars']:,}")
    print(f"  > Watchers: {data['watchers']:,}")
    print(f"  > Forks: {data['forks']:,}")
    print(f"  > Total Contributors: {data['contributors']:,}")
    
    print("\n[ Development Activity ]")
    print(f"  > Commits (Last Year): {data['commits_last_year']:,}")
    print(f"  > Releases (Last Year): {data['releases_last_year']:,}")
    print(f"  > Days Since Last Commit: {data['days_since_commit']}")

    print("\n[ Code Quality ]")
    print(f"  > CI/CD Workflow Detected (.github/workflows): {data['has_ci']}")
    print(f"  > Test Folder Detected (tests/, test/, src/test/, spec/): {data['has_tests']}")
    print(f"  > Linter Config Detected (e.g., .eslintrc, checkstyle.xml): {data['has_linter']}")
    crit_alert_str = f"{data['crit_alerts']} {'(Manual)' if MANUAL_OVERRIDES['dependency_critical_alerts'] is not None else '(Assumed)'}"
    high_alert_str = f"{data['high_alerts']} {'(Manual)' if MANUAL_OVERRIDES['dependency_high_alerts'] is not None else '(Assumed)'}"
    print(f"  > Critical Dependency Alerts: {crit_alert_str}")
    print(f"  > High Dependency Alerts: {high_alert_str}")
    
    print("\n[ Documentation & Usability ]")
    print(f"  > README Exists (Size > 10KB): {data['has_readme']}")
    print(f"  > CONTRIBUTING.md Exists: {data['has_contrib']}")
    print(f"  > Documentation Website (Homepage URL): {data['has_doc_website']}")
    print(f"  > Code of Conduct Exists: {data['has_coc']}")
    print(f"  > LICENSE File Exists: {data['has_license']}")
    print(f"  > Issue/PR Templates Exist: {data['has_template']}")
    
    print("\n[ Project Management ]")
    print(f"  > Avg Days to Close Issue (last 100): {data['avg_days_close']:.2f}")
    print(f"  > Avg Days to Merge PR (last 100): {data['avg_days_merge']:.2f}")
    print(f"  > Merged PRs (in last 100 closed): {data['merged_prs']}")
    print(f"  > Closed/Unmerged PRs (in last 100): {data['closed_unmerged_prs']}")
    print(f"  > Current Open Issues: {data['open_issues']:,}")
    print("----------------------------\n")


# --- SCORING FUNCTIONS (No changes) ---

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
    score_testing_ci = MANUAL_OVERRIDES['testing_ci_score'] if MANUAL_OVERRIDES['testing_ci_score'] is not None else (50 if data['has_ci'] else 0) + (50 if data['has_tests'] else 0)
    score_linter = MANUAL_OVERRIDES['linter_score'] if MANUAL_OVERRIDES['linter_score'] is not None else (100 if data['has_linter'] else 0)
    score_dependency_health = max(0, 100 - (data['crit_alerts'] * 10) - (data['high_alerts'] * 5))
    return (0.4 * score_testing_ci) + (0.3 * score_linter) + (0.3 * score_dependency_health)

def calculate_documentation_score(data):
    score_readme_contrib = MANUAL_OVERRIDES['readme_contrib_score'] if MANUAL_OVERRIDES['readme_contrib_score'] is not None else (70 if data['has_readme'] else 20) + (30 if data['has_contrib'] else 0)
    score_doc_website = 100 if data['has_doc_website'] else 0
    community_files_score = (33.33 if data['has_coc'] else 0) + (33.33 if data['has_license'] else 0) + (33.33 if data['has_template'] else 0)
    return (0.5 * score_readme_contrib) + (0.3 * score_doc_website) + (0.2 * community_files_score)

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


def main():
    """Main function to orchestrate the analysis."""
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
        commits_last_year, releases_last_year = get_commit_activity(owner, repo)
        avg_days_close, avg_days_merge, merged_prs, closed_unmerged_prs = get_project_management_stats(owner, repo)

        # --- UPDATED: POPULATE RAW DATA DICTIONARY ---
        raw_data = {
            'stars': repo_data.get('stargazers_count', 0),
            'watchers': repo_data.get('subscribers_count', 0),
            'forks': repo_data.get('forks_count', 0),
            'contributors': get_contributors_count(owner, repo),
            'commits_last_year': commits_last_year,
            'releases_last_year': releases_last_year,
            'days_since_commit': (datetime.now() - datetime.strptime(repo_data.get('pushed_at'), '%Y-%m-%dT%H:%M:%SZ')).days,
            'has_ci': check_file_existence(owner, repo, '.github/workflows'),
            'has_tests': check_file_existence(owner, repo, ['tests', 'test', 'src/test', 'spec']),
            'has_linter': check_file_existence(owner, repo, ['.eslintrc', 'pyproject.toml', 'tox.ini', '.rubocop.yml', 'checkstyle.xml', '.styleci.yml']),
            'crit_alerts': MANUAL_OVERRIDES['dependency_critical_alerts'] if MANUAL_OVERRIDES['dependency_critical_alerts'] is not None else 0,
            'high_alerts': MANUAL_OVERRIDES['dependency_high_alerts'] if MANUAL_OVERRIDES['dependency_high_alerts'] is not None else 0,
            'has_readme': repo_data.get('size', 0) > 10,
            'has_contrib': check_file_existence(owner, repo, 'CONTRIBUTING.md'),
            'has_doc_website': bool(repo_data.get('homepage')),
            'has_coc': check_file_existence(owner, repo, 'CODE_OF_CONDUCT.md'),
            'has_license': bool(repo_data.get('license')),
            'has_template': check_file_existence(owner, repo, ['.github/ISSUE_TEMPLATE', '.github/pull_request_template.md']),
            'avg_days_close': avg_days_close,
            'avg_days_merge': avg_days_merge,
            'merged_prs': merged_prs,
            'closed_unmerged_prs': closed_unmerged_prs,
            'open_issues': repo_data.get('open_issues_count', 0),
        }

        # --- DISPLAY RAW AND CALCULATED SCORES ---
        print_raw_data(raw_data)

        community_score = calculate_community_score(raw_data)
        development_score = calculate_development_score(raw_data)
        code_quality_score = calculate_code_quality_score(raw_data)
        documentation_score = calculate_documentation_score(raw_data)
        project_management_score = calculate_project_management_score(raw_data)

        gpqs_score = (
            (0.25 * community_score) + (0.25 * development_score) +
            (0.20 * code_quality_score) + (0.15 * documentation_score) +
            (0.15 * project_management_score)
        )

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