# vcsp_interface.py
from abc import ABC, abstractmethod

class VCSPInterface(ABC):
    """Abstract base class for version control systems."""

    @abstractmethod
    def get_pull_request(self, repo_name: str, pr_number: int):
        """Fetch a pull request by number."""
        pass

    @abstractmethod
    def get_files_in_pr(self, repo_name: str, pr_number: int):
        """Fetch files in a pull request."""
        pass

    @abstractmethod
    def get_file_content(self, repo_name: str, file_path: str, ref: str) -> str:
        """
        Fetch file content by path and ref.

        Args:
            repo_name (str): The name of the repository (e.g., 'username/repo').
            file_path (str): The path to the file in the repository.
            ref (str): The Git reference (e.g., branch, commit SHA).

        Returns:
            str: The decoded file content as a UTF-8 string.

        Raises:
            ValueError: If the file content cannot be decoded (e.g., binary file).
            Exception: If the file cannot be retrieved from the VCS.
        """
        pass

    @abstractmethod
    def create_review_comment(self, repo_name: str, commit: str, file_path: str, line: int, comment: str, side: str):
        """Create a review comment on a pull request."""
        pass

    @abstractmethod
    def get_commit(self, repo_name: str, commit_sha: str):
        """Retrieve a commit by its SHA."""
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