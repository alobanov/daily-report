#!/usr/bin/env python3
"""
Git Daily Report Generator

This script generates a daily report of git commits and optionally uses ChatGPT
to create a human-readable summary of the work done.
"""

import subprocess
from datetime import datetime, timedelta
from collections import defaultdict
import argparse
import sys
import os
import logging
from dataclasses import dataclass
from typing import List, Set, Dict, Optional, Any
import openai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

@dataclass
class GitConfig:
    """Configuration for Git operations."""
    repo_path: Optional[str]
    author_email: Optional[str]
    target_date: datetime

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> 'GitConfig':
        """Create GitConfig from command line arguments."""
        if args.date:
            try:
                target_date = datetime.strptime(args.date, "%Y-%m-%d")
            except ValueError:
                logger.error("Invalid date format. Use YYYY-MM-DD.")
                sys.exit(1)
        else:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            target_date = today - timedelta(days=1)

        return cls(
            repo_path=args.repo,
            author_email=args.email,
            target_date=target_date
        )

class GitClient:
    """Client for Git operations."""
    
    def __init__(self, config: GitConfig):
        self.config = config
        self._base_cmd = ["git"]
        if config.repo_path:
            self._base_cmd.extend(["-C", config.repo_path])

    def _run_command(self, cmd: List[str]) -> str:
        """Run a git command and return its output."""
        try:
            full_cmd = self._base_cmd + cmd
            logger.debug(f"Running command: {' '.join(full_cmd)}")
            return subprocess.check_output(full_cmd).decode().strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            raise

    def get_username(self) -> str:
        """Get the configured Git username."""
        try:
            return self._run_command(["config", "user.name"])
        except subprocess.CalledProcessError:
            logger.error("Git user.name is not configured. Run: git config user.name 'Your Name'")
            sys.exit(1)

    def get_commit_details(self, commit_hash: str) -> Optional[str]:
        """Get detailed information about a commit."""
        try:
            return self._run_command([
                "show", "-s",
                "--pretty=format:• %h %ad %s",
                "--date=short",
                commit_hash
            ])
        except subprocess.CalledProcessError:
            return None

    def get_commits_by_author(self, since: str, until: str, author: str) -> List[str]:
        """Get all commits by the specified author within the date range."""
        try:
            author_filter = self.config.author_email or author
            cmd = [
                "log", "--all",
                f"--since={since}",
                f"--until={until}",
                f"--author={author_filter}",
                "--pretty=format:%H"
            ]
            output = self._run_command(cmd)
            return list(sorted(set(filter(None, output.split("\n")))))
        except subprocess.CalledProcessError:
            return []

    def get_commit_branches(self, commit_hash: str) -> List[str]:
        """Get all branches containing the specified commit."""
        try:
            branches = self._run_command(["branch", "--contains", commit_hash])
            return [b.strip().lstrip("* ") for b in branches.split("\n") if b.strip()]
        except subprocess.CalledProcessError:
            return []

    def get_develop_commits(self, since: str, until: str, author: str) -> Set[str]:
        """Get all commits in the develop branch by the specified author."""
        try:
            author_filter = self.config.author_email or author
            cmd = [
                "log", "develop",
                f"--since={since}",
                f"--until={until}",
                f"--author={author_filter}",
                "--pretty=format:%H"
            ]
            output = self._run_command(cmd)
            return set(filter(None, output.split("\n")))
        except subprocess.CalledProcessError:
            return set()

class ChatGPTClient:
    """Client for ChatGPT API operations."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable is not set")
            sys.exit(1)
        self.client = openai.OpenAI(api_key=api_key)

    def generate_report(self, prompt: str) -> str:
        """Generate a report using ChatGPT API."""
        try:
            logger.info("Sending prompt to ChatGPT API")
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            raise

class ReportGenerator:
    """Main class for generating git commit reports."""

    def __init__(self, config: GitConfig):
        self.config = config
        self.git_client = GitClient(config)
        self.chatgpt_client = ChatGPTClient()

    def load_prompt_template(self) -> str:
        """Load the prompt template from file."""
        try:
            with open("prompt_template.txt", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error("File prompt_template.txt not found")
            sys.exit(1)

    def collect_commits_info(self, author: str) -> List[str]:
        """Collect information about all commits."""
        since = self.config.target_date.isoformat()
        until = (self.config.target_date + timedelta(days=1)).isoformat()
        
        commit_hashes = self.git_client.get_commits_by_author(since, until, author)
        if not commit_hashes:
            logger.info(f"No commits by user '{author}' for {self.config.target_date.date()}.")
            return []

        develop_commits = self.git_client.get_develop_commits(since, until, author)
        commits_info = []

        # Collect develop commits
        if develop_commits:
            commits_info.append("🔀 Branch: develop")
            for commit in develop_commits:
                details = self.git_client.get_commit_details(commit)
                if details:
                    commits_info.append(details)
            commits_info.append("")

        # Collect other commits
        branch_commits: Dict[str, List[str]] = defaultdict(list)
        for commit in commit_hashes:
            if commit in develop_commits:
                continue
            branches = self.git_client.get_commit_branches(commit)
            for branch in branches:
                if branch != "develop":
                    branch_commits[branch].append(commit)
                    break

        for branch, commits in branch_commits.items():
            if commits:
                commits_info.append(f"🔀 Branch: {branch}")
                for commit in commits:
                    details = self.git_client.get_commit_details(commit)
                    if details:
                        commits_info.append(details)
                commits_info.append("")

        return commits_info

    def generate_report(self, use_gpt: bool = False) -> None:
        """Generate and display the report."""
        author = self.git_client.get_username()
        commits_info = self.collect_commits_info(author)
        
        if not commits_info:
            return

        commits_text = "\n".join(commits_info)
        prompt_template = self.load_prompt_template()
        prompt = prompt_template.format(commits_text=commits_text)

        if use_gpt:
            logger.info("Sending prompt to ChatGPT API")
            print("\n📤 Sending prompt to ChatGPT API:\n")
            print(prompt)
            print("\n📥 Response from ChatGPT API:\n")
            try:
                response = self.chatgpt_client.generate_report(prompt)
                print(response)
            except Exception as e:
                logger.error(f"Failed to generate report: {e}")
        else:
            print(prompt)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Show git commits for the specified date (default is yesterday)."
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date in YYYY-MM-DD format (e.g., 2025-05-14). Default is yesterday."
    )
    parser.add_argument(
        "--repo",
        type=str,
        help="Path to git repository. Default is current directory."
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Author email for commits. Default is current user's commits."
    )
    parser.add_argument(
        "--use-gpt",
        action="store_true",
        help="Send prompt to ChatGPT API and display the result."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging."
    )
    return parser.parse_args([arg for arg in sys.argv[1:] if not arg.startswith("-f")])

def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)

    config = GitConfig.from_args(args)
    generator = ReportGenerator(config)
    generator.generate_report(args.use_gpt)

if __name__ == "__main__":
    main() 