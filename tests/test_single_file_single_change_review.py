import pytest
import os
import logging
from unittest.mock import Mock
from pathlib import Path
from llm_code_reviewer import LLMCodeReviewer
from vcsp_interface import PR, PRFile
from models import LLMReviewResult
from chatgpt_llm import ChatGPTLLM
from gemini_llm import GeminiLLM
from grok_llm import GrokLLM

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Base path for test data
TEST_DATA_PATH = Path(__file__).parent / "data"

# Fixture for mocked VCS
@pytest.fixture
def mock_vcsp(mocker):
    vcsp = Mock()
    return vcsp

# PR configurations
PR_CONFIGS = [
    {
        "pr_filename": "src/main/java/com/example/UserService.java",
        "diff_file_name": "test_pr_diff.txt",
        "expected_keywords": ["string", "==", "equals"],
        "pr_title": "Add admin role check",
        "pr_body": "Check if user is admin and set role",
        "pr_line": 3
    },
    {
        "pr_filename": "src/main/java/com/example/FileProcessor.java",
        "diff_file_name": "test_pr_diff_exception.txt",
        "expected_keywords": ["exception", "catch", "swallow", "rethrow", "handle"],
        "pr_title": "Add error handling for file processing",
        "pr_body": "Handle file input errors gracefully",
        "pr_line": 3
    },
    {
        "pr_filename": "src/main/java/com/example/Counter.java",
        "diff_file_name": "test_pr_diff_concurrency.txt",
        "expected_keywords": ["synchronized", "non-final", "final", "concurrency", "thread", "lock"],
        "pr_title": "Add thread-safe increment",
        "pr_body": "Ensure increment operation is thread-safe",
        "pr_line": 7
    }
]
@pytest.mark.parametrize(
    "llm_class, llm_name, env_var",
    [
        (ChatGPTLLM, "ChatGPT","OPENAI_API_KEY"),
        (GeminiLLM, "Gemini","GOOGLE_API_KEY"),
        (GrokLLM, "Grok","XAI_API_KEY")
    ],
    ids=["chatgpt", "gemini", "grok"]
)
@pytest.mark.parametrize(
    "pr_config",
    PR_CONFIGS,
    ids=[f"pr-{config['diff_file_name'].replace('.txt', '')}" for config in PR_CONFIGS]
)
def test_review_pr_with_real_llm(mock_vcsp, llm_class, llm_name, env_var, pr_config):
    """Test LLMCodeReviewer with real LLMs on Java PRs with logical bugs."""
    # Skip if API key is not set
    if not os.getenv(env_var):
        pytest.skip(env_var+" not set")

    # Extract PR configuration
    pr_filename = pr_config["pr_filename"]
    diff_file_name = pr_config["diff_file_name"]
    expected_keywords = pr_config["expected_keywords"]
    pr_title = pr_config["pr_title"]
    pr_body = pr_config["pr_body"]
    pr_line = pr_config["pr_line"]

    # Create PR object
    pr = PR(title=pr_title, body=pr_body, head_sha="abc123", state="open")

    # Load test PR diff
    diff_file = TEST_DATA_PATH / diff_file_name
    assert diff_file.exists(), f"Diff file not found: {diff_file}"
    logging.debug(f"Using diff file: {diff_file}")
    diff_content = diff_file.read_text(encoding='utf-8')

    # Setup mock VCS to return PR file
    mock_file = PRFile(filename=pr_filename, patch=diff_content)
    mock_vcsp.get_files_in_pr.return_value = [mock_file]


    # Initialize LLM and reviewer
    llm = llm_class()
    reviewer = LLMCodeReviewer(llm=llm, vcsp=mock_vcsp, full_context=True, deep=True)

    # Run review
    result = reviewer.review_pr(pr, "user/repo", 1)

    # Assert results
    assert isinstance(result, LLMReviewResult), f"{llm_name} did not return an LLMReviewResult"
    assert len(result.reviews) > 0, f"{llm_name} did not return any reviews"
    found_bug = False
    for review in result.reviews:
        if review.file == pr_filename and review.line == pr_line:
            for comment in review.comments:
                comment_lower = comment.lower()
                if any(keyword in comment_lower for keyword in expected_keywords):
                    found_bug = True
                    logging.info(f"{llm_name} detected bug in {pr_filename}: {comment}")
                    break
    assert found_bug, f"{llm_name} failed to detect bug in {pr_filename} (expected keywords: {expected_keywords})"