#!/usr/bin/env python3
# Requires: pip install PyGithub atlassian-python-api

__version__ = "1.2.0"

import os
import argparse
import re
import logging, requests
from github import Github
from atlassian import Bitbucket
from chatgpt_llm import ChatGPTLLM
from gemini_llm import GeminiLLM
from grok_llm import GrokLLM


def parse_args():
    parser = argparse.ArgumentParser(description="AI Code Review for GitHub and Bitbucket PRs")
    parser.add_argument("repository", help="For GitHub: 'owner/repo'. For Bitbucket: 'repo_slug'.")
    parser.add_argument("pr_number", type=int, help="Pull Request number or ID")
    parser.add_argument("--provider", choices=["github", "bitbucket"], default="github",
                        help="Code hosting provider (default: github)")
    parser.add_argument("--mode", choices=["general", "issues", "comments"], default="general",
                        help="Mode: 'general', 'issues', 'comments'")
    parser.add_argument("--full-context", action="store_true",
                        help="Send full files with diffs to the LLM (default: diffs only)")
    parser.add_argument("--llm", choices=["chatgpt", "gemini", "grok"], default="chatgpt",
                        help="LLM to use")
    parser.add_argument("--deep", action="store_true", help="Verbose feedback")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--version", action="version", version=f"AI Code Reviewer {__version__}")
    return parser.parse_args()


def parse_diff_per_file(diff_text):
    files, current, buff = [], None, []
    for line in diff_text.splitlines(keepends=True):
        if line.startswith('diff --git'):
            if current:
                files.append((current, ''.join(buff)))
            parts = line.split()
            current = parts[2][2:]
            buff = [line]
        elif current:
            buff.append(line)
    if current:
        files.append((current, ''.join(buff)))
    return files


def get_file_line_from_diff(diff_text):
    for header, *body in diff_text.split('@@')[1:]:
        new_info = header.split('@@')[0]
        m = re.match(r" \+(\d+),(\d+)", new_info)
        if m:
            start = int(m.group(1))
            for i, l in enumerate(body[0].splitlines(), start=1):
                if l.startswith('+') and not l.startswith('+++'):
                    return start + i - 1
    return 1


def main():
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    logger = logging.getLogger(__name__)

    # Initialize client, repo and pr uniformly
    client = None
    repo = None
    pr = None
    raw_diff = None

    if args.provider == 'github':
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is required for GitHub operations")
        client = Github(token)
        repo = client.get_repo(args.repository)
        pr = repo.get_pull(args.pr_number)
    else:
        bb_user = os.getenv('BITBUCKET_USERNAME')
        bb_pass = os.getenv('BITBUCKET_APP_PASSWORD')
        if not bb_user or not bb_pass:
            raise ValueError("BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD are required for Bitbucket operations")
        client = Bitbucket(url='https://api.bitbucket.org', username=bb_user, password=bb_pass)
        repo = args.repository  # slug only
        workspace = "ooyalaflex"
        try:
            pr = client.get_pull_request(workspace, repo, args.pr_number)
                # Fetch the raw diff manually using the Bitbucket REST API
            diff_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/pullrequests/{args.pr_number}/diff"
            response = requests.get(diff_url, auth=(bb_user, bb_pass))
            if response.status_code != 200:
                logger.error("Failed to fetch pull request diff: %s", response.text)
                response.raise_for_status()
            raw_diff = response.text
        except Exception as e:
            logger.error("Bitbucket API error: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                logger.error("Response status code: %s", e.response.status_code)
                logger.error("Response content: %s", e.response.text)
            raise

    # Gather title, description, and files
    title = pr.title if args.provider == 'github' else pr.get('title', '')
    desc = pr.body if args.provider == 'github' else pr.get('description', '')
    if args.provider == 'github':
        files = [
            (f.filename, f.patch,
             repo.get_contents(f.filename, ref=pr.head.sha).decoded_content.decode()
             if args.full_context else None)
            for f in pr.get_files() if f.patch
        ]
    else:
        files = [(fname, patch, None) for fname, patch in parse_diff_per_file(raw_diff)]

    # Build review payload
    header = f"PR Title: {title}\nPR Description:\n{desc}\n\n"
    diffs = []
    for fname, patch, content in files:
        if args.full_context and content:
            diffs.append(f"File: {fname}\n{content}\n\nDiff:\n{patch}\n{'-'*16}")
        else:
            diffs.append(f"Diff:\n{patch}\n{'-'*16}")
    payload = header + "Diffs:\n" + "\n".join(diffs)

    # Generate review
    llm = {"chatgpt": ChatGPTLLM, "gemini": GeminiLLM, "grok": GrokLLM}[args.llm](debug=args.debug, deep=args.deep)
    review = llm.generate_review(payload, args.mode)

    # Output or comment
    if args.mode == 'general':
        print(f"General PR Review:\n{review}")
    elif args.mode == 'issues':
        print(f"Code Issues:\n{review}")
    elif args.mode == 'comments':
        print(f"Code Issues:\n{review}")
        state = (pr.state if args.provider=='github' else pr.get('state')).upper()
        if state == 'OPEN':
            gh_head = None
            if args.provider == 'github':
                gh_head = repo.get_commit(pr.head.sha)
            for fname, patch, content in files:
                chunk = header + (f"File: {fname}\n{content}\n\nDiff:\n{patch}" if content else f"Diff:\n{patch}")
                fr = llm.generate_review(chunk, args.mode)
                if fr and 'no feedback' not in fr.lower():
                    ln = get_file_line_from_diff(patch)
                    comment = f"AI Issue: {fr}"
                    if args.provider == 'github':
                        pr.create_review_comment(body=comment, commit=gh_head, path=fname, line=ln, side='RIGHT')
                        logger.info("Posted GitHub comment on %s:%d", fname, ln)
                    else:
                        client.create_pull_request_comment(workspace, repo,
                                                          args.pr_number, fname, ln, comment)
                        logger.info("Posted Bitbucket comment on %s:%d", fname, ln)
        else:
            print("PR is closed; skipping comments.")
    else:
        raise ValueError(f"Unknown mode: {args.mode}")


if __name__ == '__main__':
    main()
