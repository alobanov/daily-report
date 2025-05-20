import subprocess
from datetime import datetime, timedelta
from collections import defaultdict
import argparse
import sys
import os
import openai
from dotenv import load_dotenv

load_dotenv()

def get_git_username(repo_path=None):
    try:
        cmd = ["git", "config", "user.name"]
        if repo_path:
            cmd = ["git", "-C", repo_path, "config", "user.name"]
        return subprocess.check_output(cmd).decode().strip()
    except subprocess.CalledProcessError:
        print("❌ Git user.name is not configured. Run: git config user.name 'Your Name'")
        exit(1)

def get_commit_details(commit_hash, repo_path=None):
    try:
        cmd = ["git", "show", "-s", "--pretty=format:• %h %ad %s", "--date=short", commit_hash]
        if repo_path:
            cmd = ["git", "-C", repo_path, "show", "-s", "--pretty=format:• %h %ad %s", "--date=short", commit_hash]
        output = subprocess.check_output(cmd).decode()
        return output
    except subprocess.CalledProcessError:
        return None

def get_commits_by_author(since, until, author, repo_path=None, email=None):
    try:
        cmd = ["git", "log", "--all", f"--since={since}", f"--until={until}", f"--author={author}", "--pretty=format:%H"]
        if repo_path:
            cmd = ["git", "-C", repo_path, "log", "--all", f"--since={since}", f"--until={until}", f"--author={author}", "--pretty=format:%H"]
        if email:
            cmd = ["git", "log", "--all", f"--since={since}", f"--until={until}", f"--author={email}", "--pretty=format:%H"]
            if repo_path:
                cmd = ["git", "-C", repo_path, "log", "--all", f"--since={since}", f"--until={until}", f"--author={email}", "--pretty=format:%H"]
        output = subprocess.check_output(cmd).decode()
        return list(sorted(set(filter(None, output.strip().split("\n")))))
    except subprocess.CalledProcessError:
        return []

def get_commit_branches(commit_hash, repo_path=None):
    try:
        cmd = ["git", "branch", "--contains", commit_hash]
        if repo_path:
            cmd = ["git", "-C", repo_path, "branch", "--contains", commit_hash]
        branches = subprocess.check_output(cmd).decode().strip().split("\n")
        return [b.strip().lstrip("* ") for b in branches if b.strip()]
    except subprocess.CalledProcessError:
        return []

def load_prompt_template():
    try:
        with open("prompt_template.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("❌ File prompt_template.txt not found")
        exit(1)

def main():
    parser = argparse.ArgumentParser(description="Show git commits for the specified date (default is yesterday).")
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
    args = parser.parse_args([arg for arg in sys.argv[1:] if not arg.startswith("-f")])  # ignore Jupyter arguments

    # Date determination
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD.")
            return
    else:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        target_date = today - timedelta(days=1)

    since = target_date.isoformat()
    until = (target_date + timedelta(days=1)).isoformat()

    repo_path = args.repo
    author = get_git_username(repo_path)
    commit_hashes = get_commits_by_author(since, until, author, repo_path, args.email)

    if not commit_hashes:
        print(f"No commits by user '{author}' for {target_date.date()}.")
        return

    # Get develop commits separately
    develop_commits = set()
    try:
        cmd = ["git", "log", "develop", f"--since={since}", f"--until={until}", f"--author={author}", "--pretty=format:%H"]
        if repo_path:
            cmd = ["git", "-C", repo_path, "log", "develop", f"--since={since}", f"--until={until}", f"--author={author}", "--pretty=format:%H"]
        if args.email:
            cmd = ["git", "log", "develop", f"--since={since}", f"--until={until}", f"--author={args.email}", "--pretty=format:%H"]
            if repo_path:
                cmd = ["git", "-C", repo_path, "log", "develop", f"--since={since}", f"--until={until}", f"--author={args.email}", "--pretty=format:%H"]
        output = subprocess.check_output(cmd).decode()
        develop_commits = set(filter(None, output.strip().split("\n")))
    except subprocess.CalledProcessError:
        pass

    # Collect commit information
    commits_info = []
    
    # First collect develop commits
    if develop_commits:
        commits_info.append("🔀 Branch: develop")
        for commit in develop_commits:
            details = get_commit_details(commit, repo_path)
            if details:
                commits_info.append(details)
        commits_info.append("")

    # Other commits not in develop
    branch_commits = defaultdict(list)
    for commit in commit_hashes:
        if commit in develop_commits:
            continue
        branches = get_commit_branches(commit, repo_path)
        for branch in branches:
            if branch != "develop":
                branch_commits[branch].append(commit)
                break

    for branch, commits in branch_commits.items():
        if commits:
            commits_info.append(f"🔀 Branch: {branch}")
            for commit in commits:
                details = get_commit_details(commit, repo_path)
                if details:
                    commits_info.append(details)
            commits_info.append("")

    # Form prompt with commit information
    commits_text = "\n".join(commits_info)
    prompt_template = load_prompt_template()
    prompt = prompt_template.format(commits_text=commits_text)

    if args.use_gpt:
        print("\n📤 Sending prompt to ChatGPT API:\n")
        print(prompt)
        print("\n📥 Response from ChatGPT API:\n")
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}]
        )
        print(response.choices[0].message.content)
    else:
        print(prompt)

if __name__ == "__main__":
    main() 