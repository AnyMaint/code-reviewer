import os
import argparse
from github import Github
import openai
import re

# Parse command-line arguments
parser = argparse.ArgumentParser(description="AI Code Review for GitHub PRs")
parser.add_argument("--dry-run", action="store_true", help="Print comments to console instead of posting to GitHub")
args = parser.parse_args()

# Fetch values from environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPO_NAME = os.getenv("REPO_NAME")
PR_NUMBER = os.getenv("PR_NUMBER")

# Validate environment variables
if not all([GITHUB_TOKEN, OPENAI_API_KEY, REPO_NAME, PR_NUMBER]):
    raise ValueError("Missing required environment variables: GITHUB_TOKEN, OPENAI_API_KEY, REPO_NAME, or PR_NUMBER")

# Convert PR_NUMBER to integer
try:
    PR_NUMBER = int(PR_NUMBER)
except ValueError:
    raise ValueError("PR_NUMBER must be an integer")

# GitHub setup
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)
pr = repo.get_pull(PR_NUMBER)

# OpenAI setup
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Function to estimate tokens (rough approximation)
def estimate_tokens(text):
    return len(text) // 4  # 1 token ≈ 4 characters

# Function to get AI review for a code chunk
def get_ai_review(code_chunk, is_diff_only=False):
    prompt = "You are a code reviewer. Provide concise feedback on this code diff with full file context:" if not is_diff_only else "You are a code reviewer. Provide concise feedback on this diff (full file too large):"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": code_chunk}
        ],
        max_tokens=200
    )
    return response.choices[0].message.content.strip()

# Function to parse diff and get file line number
def get_file_line_from_diff(diff):
    lines = diff.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("@@"):
            # Parse @@ -start,end +start,end @@
            match = re.match(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@", line)
            if match:
                new_start = int(match.group(3))  # Start line in the new file
                for j, diff_line in enumerate(lines[i+1:], start=1):
                    if diff_line.startswith("+") and not diff_line.startswith("+++"):
                        return new_start + j - 1  # Adjust for zero-based counting
    return 1  # Fallback if no valid line found

# Token limit threshold (leave room for prompt and output)
MAX_TOKENS = 100000

# Check if PR is open
if pr.state == "open":
    # Get the head commit object
    head_commit = repo.get_commit(pr.head.sha)

    for file in pr.get_files():
        if file.patch:  # Only process files with a diff
            # Get the full file content from the head commit
            file_content = repo.get_contents(file.filename, ref=pr.head.sha).decoded_content.decode("utf-8")
            diff = file.patch
            full_context = f"Full file:\n{file_content}\n\nDiff:\n{diff}"

            # Estimate tokens
            total_tokens = estimate_tokens(full_context)
            if total_tokens < MAX_TOKENS:
                review_text = get_ai_review(full_context)
            else:
                review_text = get_ai_review(diff, is_diff_only=True)

            if review_text and "no feedback" not in review_text.lower():
                # Get the file line number from the diff
                line_num = get_file_line_from_diff(diff)

                comment = f"AI Review: {review_text}"
                if args.dry_run:
                    print(f"Would comment on {file.filename} at line {line_num}: {comment}")
                else:
                    try:
                        # Post the review comment with correct parameters
                        pr.create_review_comment(
                            body=comment,
                            commit=head_commit,  # Commit object
                            path=file.filename,
                            line=line_num,
                            side="RIGHT"  # Comment on the new version
                        )
                        print(f"Posted comment on {file.filename} at line {line_num}: {comment}")
                    except Exception as e:
                        print(f"Error posting comment on {file.filename}: {str(e)}")

else:
    # For closed PRs, combine all files and diffs
    all_content = []
    for file in pr.get_files():
        if file.patch:
            file_content = repo.get_contents(file.filename, ref=pr.head.sha).decoded_content.decode("utf-8")
            all_content.append(f"File: {file.filename}\n{file_content}\n\nDiff:\n{file.patch}")
    full_context = "\n\n".join(all_content)

    total_tokens = estimate_tokens(full_context)
    if total_tokens < MAX_TOKENS:
        review = get_ai_review(full_context)
    else:
        diff_only = "\n".join([file.patch for file in pr.get_files() if file.patch])
        review = get_ai_review(diff_only, is_diff_only=True)

    comment = f"AI Code Review (PR closed):\n\n{review}"
    if args.dry_run:
        print("Would post general comment to closed PR:")
        print(comment)
    else:
        pr.create_issue_comment(comment)
        print("Posted general comment to closed PR:")
        print(comment)
