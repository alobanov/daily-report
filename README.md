# Git Daily Report

A script for generating a daily report of user's git commits for a selected date.

## Quick Start

1. Create and activate a virtual environment:
   ```bash
   deactivate && rm -rf venv && python3.12 -m venv venv && source venv/bin/activate && python --version
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file and add your OpenAI API key:
   ```env
   OPENAI_API_KEY=sk-...your_key...
   ```
4. Run the script:
   ```bash
   python git_daily_report.py --date YYYY-MM-DD
   ```
   If no date is specified, yesterday's date will be used.

## Usage Example
```bash
python git_daily_report.py --date 2024-06-01
```

## Additional Arguments
- `--repo` - path to git repository (default is current directory)
- `--email` - author's email for commits (default is current user's commits)
- `--use-gpt` - send prompt to ChatGPT API and display result (requires OPENAI_API_KEY environment variable or .env file)

## Requirements
- Python 3.7+
- git (must be installed and configured with user.name)
- openai, python-dotenv (for sending requests to ChatGPT API and loading environment variables)

## Description
- The script groups commits by branches and generates a structured report.
- For proper operation, git must be configured and you must be in a git repository.