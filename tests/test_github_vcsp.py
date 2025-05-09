import pytest
from unittest.mock import Mock
from github.GithubException import GithubException
from github_vcsp import GithubVCSP
from vcsp_interface import PR, PRFile, Commit
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)


# Mock environment variable
@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake_token")


# Fixture for mocked Github client
@pytest.fixture
def mock_github(mocker):
    mock_client = Mock()
    mocker.patch("github_vcsp.Github", return_value=mock_client)
    return mock_client


def test_get_pull_request_success(mock_github):
    mock_repo = Mock()
    mock_pr = Mock()
    mock_pr.title = "Test PR"
    mock_pr.body = "Description"
    mock_pr.head.sha = "abc123"
    mock_pr.state = "open"
    mock_repo.get_pull.return_value = mock_pr
    mock_github.get_repo.return_value = mock_repo
    vcsp = GithubVCSP()
    pr = vcsp.get_pull_request("user/repo", 1)
    assert isinstance(pr, PR)
    assert pr.title == "Test PR"
    assert pr.body == "Description"
    assert pr.head_sha == "abc123"
    assert pr.state == "open"


def test_get_pull_request_failure(mock_github):
    mock_repo = Mock()
    mock_repo.get_pull.side_effect = GithubException(status=404, data={"message": "Not Found"})
    mock_github.get_repo.return_value = mock_repo
    vcsp = GithubVCSP()
    with pytest.raises(Exception, match="Failed to get GitHub PR 1 in user/repo"):
        vcsp.get_pull_request("user/repo", 1)


def test_get_files_in_pr_success(mock_github, tmp_path):
    diff_file = tmp_path / "sample_diff.txt"
    diff_content = """--- a/main.py
+++ b/main.py
@@ -40,6 +40,7 @@
    def process_data(data):
        obj = data.get("object")
        result = obj.method()
+    logger.info("Processed data")
        return result"""
    diff_file.write_text(diff_content, encoding='utf-8')
    logging.debug(f"Created diff file: {diff_file}")
    assert diff_file.exists(), f"Diff file not created: {diff_file}"

    mock_repo = Mock()
    mock_pr = Mock()
    mock_file = Mock()
    mock_file.filename = "main.py"
    mock_file.patch = diff_file.read_text(encoding='utf-8')
    mock_pr.get_files.return_value = [mock_file]
    mock_repo.get_pull.return_value = mock_pr
    mock_github.get_repo.return_value = mock_repo
    vcsp = GithubVCSP()

    files = vcsp.get_files_in_pr("user/repo", 1)
    assert len(files) == 1
    assert isinstance(files[0], PRFile)
    assert files[0].filename == "main.py"
    assert "logger.info" in files[0].patch


def test_get_file_content_success(mock_github, tmp_path):
    content_file = tmp_path / "sample_file.py"
    content = """import logging

logger = logging.getLogger(__name__)

def process_data(data):
    obj = data.get("object")
    result = obj.method()
    return result"""
    content_file.write_text(content, encoding='utf-8')
    logging.debug(f"Created content file: {content_file}")
    assert content_file.exists(), f"Content file not created: {content_file}"

    mock_repo = Mock()
    mock_content = Mock()
    mock_content.decoded_content = content_file.read_bytes()
    mock_repo.get_contents.return_value = mock_content
    mock_github.get_repo.return_value = mock_repo
    vcsp = GithubVCSP()

    content = vcsp.get_file_content("user/repo", "main.py", "abc123")
    assert isinstance(content, str)
    assert "def process_data(data):" in content


def test_get_file_content_binary_failure(mock_github):
    mock_repo = Mock()
    mock_content = Mock()
    mock_content.decoded_content = None
    mock_repo.get_contents.return_value = mock_content
    mock_github.get_repo.return_value = mock_repo
    vcsp = GithubVCSP()
    with pytest.raises(ValueError, match="File content is not decodable"):
        vcsp.get_file_content("user/repo", "image.png", "abc123")


def test_create_review_comment_success(mock_github):
    mock_repo = Mock()
    mock_commit = Mock()
    mock_pr = Mock()
    mock_pr.create_review_comment = Mock()
    mock_prs = Mock(totalCount=1, __getitem__=lambda _, i: mock_pr)
    mock_commit.get_pulls.return_value = mock_prs
    mock_repo.get_commit.return_value = mock_commit
    mock_github.get_repo.return_value = mock_repo
    vcsp = GithubVCSP()
    result = vcsp.create_review_comment("user/repo", "abc123", "main.py", 42, "Test comment", "RIGHT")
    assert result is True
    mock_pr.create_review_comment.assert_called_with("Test comment", mock_commit, "main.py", 42)


def test_get_commit_success(mock_github):
    mock_repo = Mock()
    mock_commit = Mock()
    mock_commit.sha = "abc123"
    mock_commit.commit.message = "Test commit"
    mock_commit.commit.author.name = "Author"
    mock_commit.commit.author.date.isoformat.return_value = "2023-01-01T00:00:00"
    mock_repo.get_commit.return_value = mock_commit
    mock_github.get_repo.return_value = mock_repo
    vcsp = GithubVCSP()
    commit = vcsp.get_commit("user/repo", "abc123")
    assert isinstance(commit, Commit)
    assert commit.sha == "abc123"
    assert commit.message == "Test commit"
    assert commit.author == "Author"
    assert commit.date == "2023-01-01T00:00:00"


def test_get_files_in_pr_deleted_file(mock_github, tmp_path):
    diff_file = tmp_path / "deleted_file_diff.txt"
    diff_content = """--- a/old.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def old_function():
-    print("Old code")
-    return True"""
    diff_file.write_text(diff_content, encoding='utf-8')
    logging.debug(f"Created diff file: {diff_file}")
    assert diff_file.exists(), f"Diff file not created: {diff_file}"

    mock_repo = Mock()
    mock_pr = Mock()
    mock_file = Mock()
    mock_file.filename = "old.py"
    mock_file.patch = diff_file.read_text(encoding='utf-8')
    mock_pr.get_files.return_value = [mock_file]
    mock_repo.get_pull.return_value = mock_pr
    mock_github.get_repo.return_value = mock_repo
    vcsp = GithubVCSP()

    files = vcsp.get_files_in_pr("user/repo", 1)
    assert len(files) == 1
    assert files[0].filename == "old.py"
    assert "-def old_function():" in files[0].patch
    assert "+def" not in files[0].patch


def test_get_files_in_pr_new_file(mock_github, tmp_path):
    diff_file = tmp_path / "new_file_diff.txt"
    diff_content = """--- /dev/null
+++ b/new.py
@@ -0,0 +1,3 @@
+def new_function():
+    print("New code")
+    return True"""
    diff_file.write_text(diff_content, encoding='utf-8')
    logging.debug(f"Created diff file: {diff_file}")
    assert diff_file.exists(), f"Diff file not created: {diff_file}"

    mock_repo = Mock()
    mock_pr = Mock()
    mock_file = Mock()
    mock_file.filename = "new.py"
    mock_file.patch = diff_file.read_text(encoding='utf-8')
    mock_pr.get_files.return_value = [mock_file]
    mock_repo.get_pull.return_value = mock_pr
    mock_github.get_repo.return_value = mock_repo
    vcsp = GithubVCSP()

    files = vcsp.get_files_in_pr("user/repo", 1)
    assert len(files) == 1
    assert files[0].filename == "new.py"
    assert "+def new_function():" in files[0].patch
    assert "-def" not in files[0].patch