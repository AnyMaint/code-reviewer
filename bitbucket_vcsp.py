# bitbucket_vcsp.py
"""
Bitbucket implementation of the VCSPInterface.
"""
import os
import logging
import requests
from types import SimpleNamespace
from atlassian import Bitbucket
from vcsp_interface import VCSPInterface, PRFile, PR, Commit

logger = logging.getLogger(__name__)


def _parse_diff_per_file(diff_text):
    files = []
    current = None
    buff = []
    for line in diff_text.splitlines(keepends=True):
        if line.startswith('diff --git'):
            if current:
                files.append(PRFile(current, ''.join(buff)))
            parts = line.split()
            current = parts[2][2:]
            buff = [line]
        elif current:
            buff.append(line)
    if current:
        files.append(PRFile(current, ''.join(buff)))
    return files


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

    def get_repository(self, repo_name: str):
        # Not needed for PR operations; could return repo metadata if desired
        return None

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
        except Exception as e:
            logger.error("Error parsing pull request data: %s", e)
            raise
        return PR(title, body, head_sha, state)

    def get_files_in_pr(self, repo_name: str, pr_number: int):
        diff_url = f"https://api.bitbucket.org/2.0/repositories/{self.workspace}/{repo_name}/pullrequests/{pr_number}/diff"
        try:
            response = requests.get(diff_url, auth=(self.bb_user, self.bb_pass))
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error("Failed to fetch pull request diff for %s #%s: %s", repo_name, pr_number, e)
            raise
        try:
            return _parse_diff_per_file(response.text)
        except Exception as e:
            logger.error("Error parsing diff text: %s", e)
            raise

    def get_file_content(self, repo_name: str, file_path: str, ref: str):
        try:
            text = self.client.get_file_from_repo(self.workspace, repo_name, file_path, ref)
        except Exception as e:
            logger.error("Error fetching file content %s@%s:%s: %s", repo_name, ref, file_path, e)
            raise
        return SimpleNamespace(decoded_content=text.encode('utf-8'))

    def create_review_comment(self, repo_name: str, commit: str, file_path: str, line: int, comment: str, side: str):
        try:
            return self.client.create_pull_request_comment(
                self.workspace,
                repo_name,
                self.pr_number,
                file_path,
                line,
                comment
            )
        except Exception as e:
            logger.error("Error posting review comment on %s line %s: %s", file_path, line, e)
            raise

    def get_commit(self, repo_name: str, commit_sha: str) -> Commit:
        try:
            data = self.client.get_commit(self.workspace, repo_name, commit_sha)
        except Exception as e:
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
