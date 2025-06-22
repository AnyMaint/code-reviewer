# bitbucket_vcsp.py
"""
Bitbucket implementation of the VCSPInterface.
Requires: pip install atlassian-python-api
"""
import os
import re
import logging
import requests
from types import SimpleNamespace
from atlassian import Bitbucket
from vcsp_interface import VCSPInterface, PRFile, PR, Commit
from collections import defaultdict

logger = logging.getLogger(__name__)


def _parse_diff_per_file(diff_text):
    try:
        files = []
        current_file = None
        current_diff = []
        changed_lines = set()
        line_num_new = None

        for line in diff_text.splitlines(keepends=False):
            if line.startswith('diff --git'):
                if current_file:
                    files.append(PRFile(current_file, '\n'.join(current_diff), changed_lines))
                parts = line.split()
                if len(parts) >= 3:
                    current_file = parts[2][2:]  # strip "a/"
                else:
                    logger.warning("Malformed diff header: %s", line)
                    current_file = "unknown"
                current_diff = [line]
                changed_lines = set()
                line_num_new = None
            elif current_file:
                current_diff.append(line)
                if line.startswith('@@'):
                    try:
                        match = re.search(r'\+(\d+)', line)
                        if match:
                            line_num_new = int(match.group(1)) - 1
                    except Exception as e:
                        logger.warning("Failed to parse hunk header: %s", line)
                elif line.startswith('+') and not line.startswith('+++'):
                    if line_num_new is not None:
                        line_num_new += 1
                        changed_lines.add(line_num_new)
                elif not line.startswith('-'):
                    if line_num_new is not None:
                        line_num_new += 1

        if current_file:
            files.append(PRFile(current_file, '\n'.join(current_diff), changed_lines))

        return files

    except Exception as e:
        logger.error("Failed to parse diff text: %s", e)
        return []


class BitbucketVCSP(VCSPInterface):
    def __init__(self):
        self.bb_user = os.getenv('BITBUCKET_USERNAME')
        self.bb_pass = os.getenv('BITBUCKET_APP_PASSWORD')
        if not self.bb_user or not self.bb_pass:
            logger.error("Environment variables BITBUCKET_USERNAME or BITBUCKET_APP_PASSWORD not set.")
            raise ValueError("BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD are required for Bitbucket operations")
        # Workspace can be overridden via BITBUCKET_WORKSPACE, defaults to username
        self.workspace = os.getenv('BITBUCKET_WORKSPACE', self.bb_user)
        try:
            self.client = Bitbucket(url='https://api.bitbucket.org', username=self.bb_user, password=self.bb_pass)
        except Exception as e:
            logger.error("Failed to initialize Bitbucket client: %s", e)
            raise
        self.repo_slug = None
        self.pr_number = None
    
    def _get_json(self, url):
        try:
            response = requests.get(url, auth=(self.bb_user, self.bb_pass))
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("API request failed for URL %s: %s", url, e)
            return {}

    def get_repository(self, repo_name: str):
        # Not needed for PR operations; could return repo metadata if desired
        return None



    def get_last_ai_review_time(self, repo_name, pr_number):
        url = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{repo_name}/pullrequests/{pr_number}/comments"
        last_time = None
        while url:
            data = self._get_json(url)
            for comment in data.get("values", []):
                if "AI Comment:" in comment.get("content", {}).get("raw", ""):
                    comment_time = comment["created_on"]
                    if not last_time or comment_time > last_time:
                        last_time = comment_time
            url = data.get("next")
        return last_time

    def get_commits_after_time(self, repo_name, pr_number, since_time):
        url = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{repo_name}/pullrequests/{pr_number}/commits"
        commits = []
        while url:
            data = self._get_json(url)
            for commit in data.get("values", []):
                if commit["date"] > since_time:
                    commits.append(commit)
            url = data.get("next")
        return commits

    def get_commit_diff(self, repo_name, commit_hash):
        try:
            url = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{repo_name}/diff/{commit_hash}"
            response = requests.get(url, auth=(self.bb_user, self.bb_pass))
            response.raise_for_status()
            return _parse_diff_per_file(response.text)
        except Exception as e:
            logger.error("Failed to fetch or parse diff for commit %s: %s", commit_hash, e)
            return []

    def get_pr_diff(self, repo_name, pr_number):
        try:
            url = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{repo_name}/pullrequests/{pr_number}/diff"
            response = requests.get(url, auth=(self.bb_user, self.bb_pass))
            response.raise_for_status()
            return _parse_diff_per_file(response.text)
        except Exception as e:
            logger.error("Failed to fetch or parse PR diff: %s", e)
            return []

    def get_files_in_pr(self, repo_name: str, pr_number: int):
        last_review_time = self.get_last_ai_review_time(repo_name, pr_number)

        if last_review_time:
            commits = self.get_commits_after_time(repo_name, pr_number, last_review_time)
            if not commits:
                logger.info("No new commits after last AI review.")
                return []

            per_commit_diffs = []
            for commit in commits:
                commit_diff = self.get_commit_diff(repo_name, commit["hash"])
                per_commit_diffs.append(commit_diff)

            # Conflict detection
            merged = defaultdict(lambda: {"diff": [], "lines": set()})
            conflict_files = set()

            for commit_diff in per_commit_diffs:
                for pr_file in commit_diff:
                    if pr_file.filename in merged:
                        if merged[pr_file.filename]["lines"] & pr_file.lines:
                            conflict_files.add(pr_file.filename)
                    merged[pr_file.filename]["diff"].append(pr_file)
                    merged[pr_file.filename]["lines"].update(pr_file.lines)

            # Final output
            final_files = []
            full_pr_diff = None  # lazy load
            for filename, group in merged.items():
                if filename in conflict_files:
                    if full_pr_diff is None:
                        full_pr_diff = {f.filename: f for f in self.get_pr_diff(repo_name, pr_number)}
                    if filename in full_pr_diff:
                        final_files.append(full_pr_diff[filename])
                    else:
                        logger.warning("Conflict file %s not found in PR diff", filename)
                else:
                    for pr_file in group["diff"]:
                        final_files.append(pr_file)

            return final_files

        else:
            # No AI review, return full PR diff
            logger.info("No previous AI comment found, taking full PR diff.")
            return self.get_pr_diff(repo_name, pr_number)

    def get_pull_request(self, repo_name: str, pr_number: int) -> PR:
        try:
            pr_data = self.client.get_pull_request(self.workspace, repo_name, pr_number)
        except Exception as e:
            logger.error("Error fetching pull request %s #%s: %s", repo_name, pr_number, e)
            raise
        self.repo_slug = repo_name
        self.pr_number = pr_number
        try:
            title = pr_data.get('title')
            body = pr_data.get('description')
            source = pr_data.get('source', {})
            head_sha = source.get('commit', {}).get('hash')
            state = pr_data.get('state')
            logger.debug("Pull Request Data - Title: %s, Body: %s, Head SHA: %s, State: %s", title, body, head_sha, state)
        except Exception as e:
            logger.error("Error parsing pull request data: %s", e)
            raise
        return PR(title, body, head_sha, state)


        

    def get_file_content(self, repo_name: str, file_path: str, ref: str):
        # Fetch raw file content via REST API
        content_url = (
            f"https://api.bitbucket.org/2.0/repositories/"
            f"{self.workspace}/{repo_name}/src/{ref}/{file_path}"
        )
        try:
            response = requests.get(content_url, auth=(self.bb_user, self.bb_pass))
            response.raise_for_status()
            text = response.text
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching file content %s@%s:%s: %s", repo_name, ref, file_path, e)
            return None
        return SimpleNamespace(decoded_content=text.encode('utf-8'))

    def create_review_comment(self, repo_name: str, commit: str, file_path: str, line: int, comment: str, side: str):
        """
        Post a review comment on a Bitbucket pull request via REST API.
        """
        url = (
            f"https://api.bitbucket.org/2.0/repositories/"
            f"{self.workspace}/{repo_name}/pullrequests/{self.pr_number}/comments"
        )
        payload = None
        if file_path != "":
            payload = {
                "content": {"raw": comment},
                "inline": {"path": file_path, "to": line}
            }
        else:
            payload = {
                "content": {"raw": comment}             
            }
        try:
            response = requests.post(url, json=payload, auth=(self.bb_user, self.bb_pass))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            status = e.response.status_code if e.response else 'N/A'
            text = e.response.text if e.response else str(e)
            logger.error(
                "Failed to post review comment to %s #%s: status %s, response: %s",
                repo_name, self.pr_number, status, text
            )
            raise

    def get_commit(self, repo_name: str, commit_sha: str) -> Commit:
        # Fetch a single commit via REST API
        commit_url = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{repo_name}/commit/{commit_sha}"
        try:
            response = requests.get(commit_url, auth=(self.bb_user, self.bb_pass))
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching commit %s #%s: %s", repo_name, commit_sha, e)
            raise
        try:
            message = data.get('message')
            author = data.get('author', {}).get('user', {}).get('display_name')
            date = data.get('date')
        except Exception as e:
            logger.error("Error parsing commit data: %s", e)
            raise
        return Commit(commit_sha, message, author, date)
