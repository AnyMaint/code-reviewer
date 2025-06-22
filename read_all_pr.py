import requests
import os
from datetime import datetime, timedelta

# === Config ===
WORKSPACE = os.getenv('BITBUCKET_WORKSPACE')
USERNAME = os.getenv('BITBUCKET_USERNAME')
APP_PASSWORD = os.getenv('BITBUCKET_APP_PASSWORD')
KEYWORDS = ['bugCount', 'smellCount', 'optimizationCount', 'logicalErrors', 'performanceIssues']
repos = ['dbserver-cpp', 'mos-server-agent-dcl', 'wn-index-enrichment-service', 'wn-indexer-service', 'wn-watch-service', 'wn-index-replication-service','unified-mam-service',
        'wn-forwardsearch-service', 'gql-api-server', 'notifier-client-lib-ts', 'grpc-ts-runtime-lib', 'purge-agent', 'wn-event-processor-service', 'rundownpoc' ]
TOKEN_TRIGGER = "Total tokens"

# === Stats ===
issuesHandled = 0
issuesReviewed = 0
WEEK_AGO = datetime.utcnow() - timedelta(days=7)

def fetch_repositories():
    """Fetch all repositories in the workspace."""
    repos = []
    url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}"
    while url:
        resp = requests.get(url, auth=(USERNAME, APP_PASSWORD))
        resp.raise_for_status()
        data = resp.json()
        repos.extend([repo['slug'] for repo in data.get('values', [])])
        url = data.get('next')
    return repos

def fetch_all_prs(repo_slug):
    """Fetch last 50 PRs for a given repository, filtered to only include those from the past week."""
    all_prs = []
    url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{repo_slug}/pullrequests"
    params = {
        'pagelen': 25,
        'state': ['OPEN', 'MERGED']
    }
    resp = requests.get(url, auth=(USERNAME, APP_PASSWORD), params=params)
    if resp.status_code != 200:
        print(f"Failed to fetch PRs for {repo_slug}")
        return []
    data = resp.json()
    for pr in data.get('values', []):
        created_on = pr.get('created_on')
        if created_on:
            created_dt = datetime.strptime(created_on, '%Y-%m-%dT%H:%M:%S.%f%z').replace(tzinfo=None)
            if created_dt >= WEEK_AGO:
                all_prs.append(pr)
    return all_prs

def fetch_comments(repo_slug, pr_id):
    """Fetch all comments for a PR in a specific repo."""
    comments = []
    url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{repo_slug}/pullrequests/{pr_id}/comments"
    while url:
        resp = requests.get(url, auth=(USERNAME, APP_PASSWORD))
        if resp.status_code != 200:
            break
        data = resp.json()
        comments.extend(data.get('values', []))
        url = data.get('next')
    return comments

def process_repository(repo_slug):
    global issuesHandled, issuesReviewed
    issuesHandledRepo = 0
    issuesReviewedRepo = 0
    prs = fetch_all_prs(repo_slug)

    for pr in prs:
        pr_id = pr['id']
        pr_link = pr['links']['html']['href']
        comments = fetch_comments(repo_slug, pr_id)

        found_issue = False
        found_review = False

        for comment in comments:
            text = comment.get('content', {}).get('raw', '')
            if not text:
                continue

            if not found_issue and any(kw in text for kw in KEYWORDS):
                issuesHandled += 1
                issuesHandledRepo += 1
                found_issue = True
                print(f"[Issue] PR #{pr_id} in {repo_slug}: {pr_link}")

            if not found_review and TOKEN_TRIGGER in text:
                issuesReviewed += 1
                issuesReviewedRepo += 1
                found_review = True

    print(f"Repository: {repo_slug} - Issues Handled: {issuesHandledRepo}, Issues Reviewed: {issuesReviewedRepo}")

def main():
    for repo in repos:
        process_repository(repo)

    print("\n--- Summary ---")
    print(f"Issues Handled: {issuesHandled}")
    print(f"Issues Reviewed: {issuesReviewed}")

if __name__ == "__main__":
    main()
