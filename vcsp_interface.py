from abc import ABC, abstractmethod

class VCSPInterface(ABC):
    """Abstract base class for version control systems."""

    @abstractmethod
    def get_repository(self, repo_name: str):
        """Fetch a repository by name."""
        pass

    @abstractmethod
    def get_pull_request(self, repo_name: str, pr_number: int):
        """Fetch a pull request by number."""
        pass

    @abstractmethod
    def get_files_in_pr(self, repo_name: str, pr_number: int):
        """Fetch files in a pull request."""
        pass

    @abstractmethod
    def get_file_content(self, repo_name: str, file_path: str, ref: str):
        """Fetch file content by path and ref."""
        pass

    @abstractmethod
    def create_review_comment(self, repo_name: str, commit: str, file_path: str, line: int, comment: str, side: str):
        """Create a review comment on a pull request."""
        pass

    @abstractmethod
    def get_commit(self, repo_name: str, commit_sha: str):
        """Create a review comment on a pull request."""
        pass

class PRFile:
    def __init__(self, filename, patch):
        self.filename = filename
        self.patch = patch

class PR:
    def __init__(self, title, body, head_sha, state):
        self.title = title
        self.body = body
        self.head_sha = head_sha
        self.state = state

class Commit:
    def __init__(self, sha, message, author, date):
        self.sha = sha
        self.message = message
        self.author = author
        self.date = date
