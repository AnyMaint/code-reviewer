import os
import argparse
from github import Github
import openai

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

# Function to get AI review for a code chunk
def get_ai_review(code_chunk):
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Updated to gpt-4o-mini
        messages=[
            {"role": "system", "content": "You are a code reviewer. Provide concise feedback on this code diff:"},
            {"role": "user", "content": code_chunk}
        ],
        max_tokens=200  # Smaller limit for individual comments
    )
    return response.choices[0].message.content.strip()

# Check if PR is open
if pr.state == "open":
    # Process each file and its changes
    for file in pr.get_files():
        if file.patch:  # Only process files with a diff
            # Get the diff for this file
            diff = file.patch
            review = get_ai_review(diff)

            if review and "no feedback" not in review.lower():  # Skip empty or irrelevant reviews
                # Find a line to comment on (simplified: first added/changed line)
                lines = diff.splitlines()
                for i, line in enumerate(lines, 1):
                    if line.startswith("+") and not line.startswith("+++"):  # Added line
                        position = i
                        break
                else:
                    position = 1  # Fallback to first line if no specific addition found

                comment = f"AI Review: {review}"
                if args.dry_run:
                    print(f"Would comment on {file.filename} at line {position}: {comment}")
                else:
                    # Post a review comment on the specific line
                    pr.create_review_comment(
                        body=comment,
                        commit_id=pr.head.sha,
                        path=file.filename,
                        position=position
                    )
                    print(f"Posted comment on {file.filename} at line {position}: {comment}")

else:
    # For closed PRs, post a single general comment
    diff = "\n".join([file.patch for file in pr.get_files() if file.patch])
    review = get_ai_review(diff)
    comment = f"AI Code Review (PR closed):\n\n{review}"
    if args.dry_run:
        print("Would post general comment to closed PR:")
        print(comment)
    else:
        pr.create_issue_comment(comment)
        print("Posted general comment to closed PR:")
        print(comment)
