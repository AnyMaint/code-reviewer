import os
from github import Github
from vcsp_interface import PR, Commit, PRFile, VCSPInterface
from github import Github, GithubException

class GithubVCSP(VCSPInterface):
    def __init__(self):
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is required")

        self.client = Github(token)

    def get_repository(self, repo_name: str):
        try:
            return self.client.get_repo(repo_name)
        except GithubException as e:
            raise Exception(f"Failed to get GitHub repository {repo_name}: {str(e)}")

    def get_pull_request(self, repo_name: str, pr_number: int):
        try:
            github_pr = self.client.get_repo(repo_name).get_pull(pr_number)
            return PR(
                title=github_pr.title,
                body=github_pr.body,
                head_sha=github_pr.head.sha,
                state=github_pr.state
            )
        except GithubException as e:
            raise Exception(f"Failed to get GitHub PR {pr_number} in {repo_name}: {str(e)}")

    def get_files_in_pr(self, repo_name: str, pr_number: int):
        try:
            pr = self.client.get_repo(repo_name).get_pull(pr_number)
            return [PRFile(file.filename, file.patch) for file in pr.get_files()]
        except GithubException as e:
            raise Exception(f"Failed to get files in GitHub PR {pr_number}: {str(e)}")

    def get_file_content(self, repo_name: str, file_path: str, ref: str = None):
        try:
            content = self.client.get_repo(repo_name).get_contents(file_path, ref=ref)
            return content.decoded_content.decode('utf-8')
        except GithubException as e:
            raise Exception(f"Failed to get file content for {file_path} in {repo_name}: {str(e)}")
        except GithubException as e:
            raise Exception(f"Failed to get file content for {file_path} in {repo_name}: {str(e)}")

    def create_review_comment(self, repo_name: str, pr_number: str, commit: str, file_path: str, line: int, comment: str, side: str):
        try:
            pr = self.client.get_repo(repo_name).get_pull(pr_number)
            pr.create_review_comment(body=comment, commit=commit, path=file_path, position=line, side=side)
            return True
        except GithubException as e:
            raise Exception(f"Failed to create GitHub review comment: {str(e)}")

    def get_commit(self, repo_name: str, commit_sha: str):
        """Retrieve a commit by its SHA from a GitHub repository."""
        try:
            repo = self.client.get_repo(repo_name)
            commit = repo.get_commit(commit_sha)
            return Commit(
                sha=commit.sha,
                message=commit.commit.message,
                author=commit.commit.author.name,
                date=commit.commit.author.date.isoformat()
            )
        except GithubException as e:
            raise Exception(f"Failed to get GitHub commit {commit_sha} in {repo_name}: {str(e)}")
