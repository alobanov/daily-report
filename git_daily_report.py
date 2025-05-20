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
        print("❌ Git user.name не настроен. Выполните: git config user.name 'Ваше имя'")
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
        print("❌ Файл prompt_template.txt не найден")
        exit(1)

def main():
    parser = argparse.ArgumentParser(description="Показать git-коммиты за указанную дату (по умолчанию — за вчера).")
    parser.add_argument(
        "--date",
        type=str,
        help="Дата в формате YYYY-MM-DD (например, 2025-05-14). По умолчанию — вчера."
    )
    parser.add_argument(
        "--repo",
        type=str,
        help="Путь к git-репозиторию. По умолчанию — текущая директория."
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Email автора коммитов. По умолчанию — коммиты текущего пользователя."
    )
    parser.add_argument(
        "--use-gpt",
        action="store_true",
        help="Отправить промпт в ChatGPT API и вывести результат."
    )
    args = parser.parse_args([arg for arg in sys.argv[1:] if not arg.startswith("-f")])  # игнорим Jupyter-аргументы

    # Определение даты
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("❌ Неверный формат даты. Используйте YYYY-MM-DD.")
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
        print(f"Нет коммитов пользователя '{author}' за {target_date.date()}.")
        return

    # Получаем develop-коммиты отдельно
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

    # Собираем информацию о коммитах
    commits_info = []
    
    # Сначала собираем develop-коммиты
    if develop_commits:
        commits_info.append("🔀 Ветка: develop")
        for commit in develop_commits:
            details = get_commit_details(commit, repo_path)
            if details:
                commits_info.append(details)
        commits_info.append("")

    # Остальные коммиты, не входящие в develop
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
            commits_info.append(f"🔀 Ветка: {branch}")
            for commit in commits:
                details = get_commit_details(commit, repo_path)
                if details:
                    commits_info.append(details)
            commits_info.append("")

    # Формируем промпт с информацией о коммитах
    commits_text = "\n".join(commits_info)
    prompt_template = load_prompt_template()
    prompt = prompt_template.format(commits_text=commits_text)

    if args.use_gpt:
        print("\n📤 Отправляю промпт в ChatGPT API:\n")
        print(prompt)
        print("\n📥 Ответ от ChatGPT API:\n")
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