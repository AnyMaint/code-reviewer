# Changelog
All notable changes to **AI Code Reviewer** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to semantic versioning.

## [2.0.1] - 2025-05-02
### Added
- Unit tests
- Tests for specific bugs and issues
- Separate script for PR summary (`describe-pr.py`)
### Changed
- LLM interface - prompt only
- Introduced reviewer class, which creates prompts
- LLM output in JSON
- Issues lines detection based on LLM output only
- Support multiple LLM models: Added the ability to specify one or more LLMs via the --llm option (e.g., --llm chatgpt grok).
- Enhanced metrics reporting: Introduced token usage, bug count, and a summary of general review information as additional metrics using ( --add_statistic_info).
- possible to use a container to execute the command (with defaults): 
  docker run --name code-review-runner --env-file .env lemaxw/code-reviewer:2.0.1 purge-agent 27
  or overwrite the defaults:
  docker run --name code-reviewer-temp --env-file .env   --entrypoint python3 lemaxw/code-reviewer:2.0.1   review.py mos-server-agent-dcl 160 --vcsp bitbucket --deep --full-context --llm chatgpt --mode issues --add_statistic_info

## [1.2] - 2025-04-25
### Added
- Gitlab support
- Bitbucket support
- Generic VCS interface

## [1.1.1] - 2025-04-22
### Changed
- PR description and title are now part of prompt
- LLM prompt changed to decrease false positives

## [1.1.0] - 2025-04-22
### Added
- Support for Grok LLM via the xAI API.
- Default bug-focused review mode, limiting output to critical bugs (syntax errors, null-pointer exceptions, logical errors).
- `--deep` flag to enable verbose reviews including non-bug feedback (e.g., data migration, documentation).
- Centralized prompt preparation in `prompts.py` with `get_prompt` function for easier maintenance.
- Version number (`__version__`) and `--version` flag in `review.py`.

## [1.0.0] - 2025-03-31
### Added
- Initial release with support for ChatGPT and Gemini LLMs.
- Modes: `general` (PR summary), `issues` (list issues), `comments` (post to GitHub).
- `--full-context` flag to include full file contents in reviews.
- `--debug` flag to print LLM API request details.

