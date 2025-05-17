import pytest
from unittest.mock import Mock
from llm_code_reviewer import LLMCodeReviewer, remove_hunk_counts
from models import LLMReviewResult, CodeReview
from llm_interface import LLMInterface, ModelResult
from vcsp_interface import PR, PRFile
from pathlib import Path
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
TEST_DATA_PATH = Path(__file__).parent / "data"

# Fixture for mocked VCS and LLM
@pytest.fixture
def mock_vcsp(mocker):
    vcsp = Mock()
    return vcsp


@pytest.fixture
def mock_llm(mocker):
    llm = Mock(spec=LLMInterface)
    return llm


# Fixture for sample PR
@pytest.fixture
def sample_pr():
    return PR(title="Test PR", body="Description", head_sha="abc123", state="open")


def test_review_pr_success(mock_vcsp, mock_llm, sample_pr, tmp_path, mocker):
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

    mock_file = PRFile(filename="main.py", patch=diff_file.read_text(encoding='utf-8'))
    mock_vcsp.get_files_in_pr.return_value = [mock_file]
    mock_vcsp.get_file_content.return_value = content_file.read_text(encoding='utf-8')
    mock_llm.answer.return_value = ModelResult(response='''[
        {"file": "main.py", "line": 43, "comments": ["Add logging"]}
    ]''', total_tokens=0, prompt_tokens=0, completion_tokens=0)
    mocker.patch("llm_code_reviewer.get_prompt", return_value="Review prompt")
    mocker.patch("llm_code_reviewer.JsonResponseCleaner.strip",
                 return_value='[{"file": "main.py", "line": 43, "comments": ["Add logging"]}]')
    reviewer = LLMCodeReviewer(llm=mock_llm, vcsp=mock_vcsp, full_context=True, deep=True)

    result = reviewer.review_pr(sample_pr, "user/repo", 1)
    assert isinstance(result, LLMReviewResult)
    assert len(result.reviews) == 1
    assert result.reviews[0].file == "main.py"
    assert result.reviews[0].line == 43  # Updated: + line is at 43
    assert result.reviews[0].comments == ["Add logging"]
    mock_llm.answer.assert_called_once()
    mock_vcsp.get_file_content.assert_called_with("user/repo", "main.py", ref="abc123")


# def test_get_file_line_from_diff(mock_vcsp, tmp_path):
#     diff_file = tmp_path / "sample_diff.txt"
#     diff_content = """--- a/main.py
# +++ b/main.py
# @@ -40,6 +40,7 @@
#     def process_data(data):
#         obj = data.get("object")
#         result = obj.method()
# +    logger.info("Processed data")
#         return result"""
#     diff_file.write_text(diff_content, encoding='utf-8')
#     logging.debug(f"Created diff file: {diff_file}")
#     assert diff_file.exists(), f"Diff file not created: {diff_file}"

#     reviewer = LLMCodeReviewer(llm=Mock(), vcsp=mock_vcsp)
#     line = reviewer._get_file_line_from_diff(diff_file.read_text(encoding='utf-8'))
#     assert line == 43  # Updated: + line is at 43


def test_review_pr_deleted_file(mock_vcsp, mock_llm, sample_pr, tmp_path, mocker):
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

    mock_file = PRFile(filename="old.py", patch=diff_file.read_text(encoding='utf-8'))
    mock_vcsp.get_files_in_pr.return_value = [mock_file]
    mock_llm.answer.return_value =  ModelResult('''[
        {"file": "old.py", "line": 1, "comments": ["File deleted"]}
    ]''', total_tokens=0, prompt_tokens=0, completion_tokens=0)
    mocker.patch("llm_code_reviewer.get_prompt", return_value="Review prompt")
    mocker.patch("llm_code_reviewer.JsonResponseCleaner.strip",
                 return_value='[{"file": "old.py", "line": 1, "comments": ["File deleted"]}]')
    reviewer = LLMCodeReviewer(llm=mock_llm, vcsp=mock_vcsp)

    result = reviewer.review_pr(sample_pr, "user/repo", 1)
    assert len(result.reviews) == 1
    assert result.reviews[0].file == "old.py"
    assert result.reviews[0].line == 1
    assert result.reviews[0].comments == ["File deleted"]


def test_review_pr_new_file(mock_vcsp, mock_llm, sample_pr, tmp_path, mocker):
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

    mock_file = PRFile(filename="new.py", patch=diff_file.read_text(encoding='utf-8'))
    mock_vcsp.get_files_in_pr.return_value = [mock_file]
    mock_llm.answer.return_value =  ModelResult('''[
        {"file": "new.py", "line": 1, "comments": ["New file added"]}
    ]''', total_tokens=0, prompt_tokens=0, completion_tokens=0)
    mocker.patch("llm_code_reviewer.get_prompt", return_value="Review prompt")
    mocker.patch("llm_code_reviewer.JsonResponseCleaner.strip",
                 return_value='[{"file": "new.py", "line": 1, "comments": ["New file added"]}]')
    reviewer = LLMCodeReviewer(llm=mock_llm, vcsp=mock_vcsp)

    result = reviewer.review_pr(sample_pr, "user/repo", 1)
    assert len(result.reviews) == 1
    assert result.reviews[0].file == "new.py"
    assert result.reviews[0].line == 1
    assert result.reviews[0].comments == ["New file added"]

def test_review_pr_new_file():

    sample = """\
@@ -68,7 +68,7 @@ const FOUR_MEGA_BYTES = 4194304;
@@ -101,7 +101,7 @@ export async function main() {
@@ -132,11 +132,12 @@ export async function main() {
"""
    assert remove_hunk_counts(sample) == """\
@@ -68 +68 @@ const FOUR_MEGA_BYTES = 4194304;
@@ -101 +101 @@ export async function main() {
@@ -132 +132 @@ export async function main() {
"""
    