import pytest
from unittest.mock import Mock
from llm_code_reviewer import LLMCodeReviewer
from models import LLMReviewResult, CodeReview
from llm_interface import LLMInterface
from vcsp_interface import PR, PRFile
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)


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
    mock_llm.answer.return_value = '''[
        {"file": "main.py", "line": 1, "comments": ["Add logging"]}
    ]'''
    mocker.patch("llm_code_reviewer.get_prompt", return_value="Review prompt")
    mocker.patch("llm_code_reviewer.JsonResponseCleaner.strip",
                 return_value='[{"file": "main.py", "line": 1, "comments": ["Add logging"]}]')
    reviewer = LLMCodeReviewer(llm=mock_llm, vcsp=mock_vcsp, full_context=True, deep=True)

    result = reviewer.review_pr(sample_pr, "user/repo", 1)
    assert isinstance(result, LLMReviewResult)
    assert len(result.reviews) == 1
    assert result.reviews[0].file == "main.py"
    assert result.reviews[0].line == 43  # Updated: + line is at 43
    assert result.reviews[0].comments == ["Add logging"]
    mock_llm.answer.assert_called_once()
    mock_vcsp.get_file_content.assert_called_with("user/repo", "main.py", ref="abc123")


def test_get_file_line_from_diff(mock_vcsp, tmp_path):
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

    reviewer = LLMCodeReviewer(llm=Mock(), vcsp=mock_vcsp)
    line = reviewer._get_file_line_from_diff(diff_file.read_text(encoding='utf-8'))
    assert line == 43  # Updated: + line is at 43


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
    mock_llm.answer.return_value = '''[
        {"file": "old.py", "line": 1, "comments": ["File deleted"]}
    ]'''
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
    mock_llm.answer.return_value = '''[
        {"file": "new.py", "line": 1, "comments": ["New file added"]}
    ]'''
    mocker.patch("llm_code_reviewer.get_prompt", return_value="Review prompt")
    mocker.patch("llm_code_reviewer.JsonResponseCleaner.strip",
                 return_value='[{"file": "new.py", "line": 1, "comments": ["New file added"]}]')
    reviewer = LLMCodeReviewer(llm=mock_llm, vcsp=mock_vcsp)

    result = reviewer.review_pr(sample_pr, "user/repo", 1)
    assert len(result.reviews) == 1
    assert result.reviews[0].file == "new.py"
    assert result.reviews[0].line == 1
    assert result.reviews[0].comments == ["New file added"]


def test_get_file_line_from_diff_empty_lines(mock_vcsp, tmp_path):
    diff_file = tmp_path / "empty_lines_diff.txt"
    diff_content = """--- a/main.py
+++ b/main.py
@@ -40,5 +40,6 @@
    def process_data(data):
        obj = data.get("object")
        result = obj.method()
+
        return result"""
    diff_file.write_text(diff_content, encoding='utf-8')
    logging.debug(f"Created diff file: {diff_file}")
    assert diff_file.exists(), f"Diff file not created: {diff_file}"

    reviewer = LLMCodeReviewer(llm=Mock(), vcsp=mock_vcsp)
    line = reviewer._get_file_line_from_diff(diff_file.read_text(encoding='utf-8'))
    assert line == 43

def test_get_all_added_line_numbers_from_ts_diff(tmp_path):
        diff_content = """--git a/packages/server/src/index.ts b/packages/server/src/index.ts
index fc75afdb0..451c81ed3 100644
--- a/packages/server/src/index.ts
+++ b/packages/server/src/index.ts
@@ -68,7 +68,7 @@ const FOUR_MEGA_BYTES = 4194304;
 
 export async function main() {
   ConfigManager.init();
-  const galaxyClusterUser = GalaxyConfigProperties.getInstance().clusterUser ?? '';
+  const galaxyClusterUser = GalaxyConfigProperties.getInstance().clusterUser;
   const galaxyClusterIdent = GalaxyConfigProperties.getInstance().clusterIdent ?? '';
   const logWrapper = LoggerFactory.getInstance();
   const server = fastify({
@@ -131,12 +131,14 @@ export async function main() {
       playgroundGraphqlEndpoint = prefix + graphqlPath;
       playgroundSubscriptionEndpoint = prefix + subscriptionsPath;
     }
+       (playgroundGraphqlEndpoint as any).toLowerCase = 'hack'; 
     const port = Number(process.env.PORT || 4000);
     const envelopLogger = logWrapper.getLogger('Envelop');
     envelopLogger.info(`Initializing server on port ${port}`);
-    const runtimeContext = await buildRuntimeContext(galaxyClusterUser, galaxyClusterIdent);
+    const runtimeContext = buildRuntimeContext(galaxyClusterUser, galaxyClusterIdent);
     const notifierClient = NotifierClientFactory.createNotifier('*', runtimeContext);
-    await notifierClient.init();
+       envelopLogger.info('Loaded runtimeContext: ' + JSON.stringify(runtimeContext)); 
+    await notifierClient.init().catch(() => {}); 
 
     const mqService = mqAdapterBuilder(AdapterType.RABBIT_MQ);
     await mqService.connect()
"""

        # Write diff to file
        diff_file = tmp_path / "ts_diff.patch"
        diff_file.write_text(diff_content, encoding='utf-8')

        reviewer = LLMCodeReviewer(llm=Mock(), vcsp=mock_vcsp)
        added_lines = reviewer.get_all_added_line_numbers(diff_file.read_text(encoding='utf-8'))

        # Validate expected added lines
        assert added_lines == [71, 134, 138, 140, 141], f"Unexpected added lines: {added_lines}"
            