# gitlab_vcsp.py
import os
import gitlab
from gitlab.exceptions import GitlabGetError, GitlabCreateError
from vcsp_interface import PR, Commit, PRFile, VCSPInterface


class GitlabVCSP(VCSPInterface):
    def __init__(self):
        token = os.getenv("GITLAB_TOKEN")
        if not token:
            raise ValueError("GITLAB_TOKEN environment variable is required")

        self.client = gitlab.Gitlab("https://gitlab.com", private_token=token)

    def get_repository(self, repo_name: str):
        try:
            return self.client.projects.get(repo_name)
        except GitlabGetError as e:
            raise Exception(f"Failed to get GitLab repository {repo_name}: {str(e)}")

    def get_pull_request(self, repo_name: str, pr_number: int):
        try:
            project = self.client.projects.get(repo_name)
            mr = project.mergerequests.get(pr_number)
            return PR(
                title=mr.title,
                body=mr.description,
                head_sha=mr.sha,
                state='open'  # there is no MR state in Gitlab api lib
            )
        except GitlabGetError as e:
            raise Exception(f"Failed to get GitLab MR {pr_number} in {repo_name}: {str(e)}")

    def get_files_in_pr(self, repo_name: str, pr_number: int):
        try:
            project = self.client.projects.get(repo_name)
            mr = project.mergerequests.get(pr_number)
            changes = mr.changes()['changes']
            return [PRFile(change['new_path'], change.get('diff', '')) for change in changes]
        except GitlabGetError as e:
            raise Exception(f"Failed to get files in GitLab MR {pr_number}: {str(e)}")

    def get_file_content(self, repo_name: str, file_path: str, ref: str = None) -> str:
        try:
            project = self.client.projects.get(repo_name)
            ref = ref or 'main'
            file = project.files.get(file_path=file_path, ref=ref)
            content_bytes = file.decode()
            if not content_bytes:
                raise ValueError(f"File content is empty or not decodable for {file_path}")
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode file content for {file_path} (possibly binary): {str(e)}")
        except GitlabGetError as e:
            raise Exception(f"Failed to get file content for {file_path} in {repo_name}: {str(e)}")

    def create_review_comment(self, repo_name: str, commit: str, file_path: str, line: int, comment: str, side: str):
        try:
            project = self.client.projects.get(repo_name)
            # Find the merge request associated with the commit
            mrs = project.commits.get(commit).merge_requests()
            if not mrs:
                raise Exception(f"No merge request found for commit {commit}")
            mr_id = mrs[0]['iid']  # Get the ID of the first merge request
            mr = project.mergerequests.get(mr_id)  # Fetch the merge request object

            # Create a discussion with a position-based comment
            mr.discussions.create({
                'body': comment,
                'position': {
                    'base_sha': mr.diff_refs['base_sha'],
                    'start_sha': mr.diff_refs['start_sha'],
                    'head_sha': mr.diff_refs['head_sha'],
                    'position_type': 'text',
                    'new_path': file_path,
                    'new_line': line
                }
            })
            return True
        except GitlabCreateError as e:
            raise Exception(f"Failed to create GitLab review comment: {str(e)}")

    def get_commit(self, repo_name: str, commit_sha: str):
        """Retrieve a commit by its SHA from a GitLab repository."""
        try:
            project = self.client.projects.get(repo_name)
            commit = project.commits.get(commit_sha)
            return Commit(
                sha=commit.id,
                message=commit.message,
                author=commit.author_name,
                date=commit.authored_date
            )
        except GitlabGetError as e:
            raise Exception(f"Failed to get GitLab commit {commit_sha} in {repo_name}: {str(e)}")
