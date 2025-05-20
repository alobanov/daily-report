import subprocess
from datetime import datetime, timedelta
from collections import defaultdict
import argparse
import sys

def get_git_username():
    try:
        return subprocess.check_output(["git", "config", "user.name"]).decode().strip()
    except subprocess.CalledProcessError:
        print("❌ Git user.name не настроен. Выполните: git config user.name 'Ваше имя'")
        exit(1)

def get_commit_details(commit_hash):
    try:
        output = subprocess.check_output([
            "git", "show", "-s",
            "--pretty=format:• %h %ad %s",
            "--date=short",
            commit_hash
        ]).decode()
        return output
    except subprocess.CalledProcessError:
        return None

def get_commits_by_author(since, until, author):
    try:
        output = subprocess.check_output([
            "git", "log", "--all",
            f"--since={since}",
            f"--until={until}",
            f"--author={author}",
            "--pretty=format:%H"
        ]).decode()
        return list(sorted(set(filter(None, output.strip().split("\n")))))
    except subprocess.CalledProcessError:
        return []

def get_commit_branches(commit_hash):
    try:
        branches = subprocess.check_output([
            "git", "branch", "--contains", commit_hash
        ]).decode().strip().split("\n")
        return [b.strip().lstrip("* ") for b in branches if b.strip()]
    except subprocess.CalledProcessError:
        return []

def main():
    parser = argparse.ArgumentParser(description="Показать git-коммиты за указанную дату (по умолчанию — за вчера).")
    parser.add_argument(
        "--date",
        type=str,
        help="Дата в формате YYYY-MM-DD (например, 2025-05-14). По умолчанию — вчера."
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

    author = get_git_username()
    commit_hashes = get_commits_by_author(since, until, author)

    if not commit_hashes:
        print(f"Нет коммитов пользователя '{author}' за {target_date.date()}.")
        return
    else:
        print(f"""
🔧 Сформируй отчёт о проделанной работе за указанную дату в следующем формате:

Вчера:
- <краткое описание по задаче 1>
- <краткое описание по задаче 2>

📌 Правила:
• Группируй коммиты по веткам. Каждая ветка — это отдельная задача.
• Описывай, что было сделано в каждой ветке абстрактно, без технических деталей.
• Если в ветке develop есть коммиты с префиксом MOB-, это означает, что соответствующая задача была завершена и смержена — упомяни это в отчёте как завершённую работу.

📥 На вход подаётся список веток и коммитов — сформируй на его основе осмысленный, лаконичный и структурированный отчёт.
        """)

    # Получаем develop-коммиты отдельно
    develop_commits = set()
    try:
        output = subprocess.check_output([
            "git", "log", "develop",
            f"--since={since}",
            f"--until={until}",
            f"--author={author}",
            "--pretty=format:%H"
        ]).decode()
        develop_commits = set(filter(None, output.strip().split("\n")))
    except subprocess.CalledProcessError:
        pass

    print(f"\n📦 Коммиты пользователя '{author}' за {target_date.date()}:\n")

    # Сначала показываем develop
    if develop_commits:
        print("🔀 Ветка: develop")
        for commit in develop_commits:
            details = get_commit_details(commit)
            if details:
                print(details)
        print()

    # Остальные коммиты, не входящие в develop
    branch_commits = defaultdict(list)
    for commit in commit_hashes:
        if commit in develop_commits:
            continue
        branches = get_commit_branches(commit)
        for branch in branches:
            if branch != "develop":
                branch_commits[branch].append(commit)
                break

    for branch, commits in branch_commits.items():
        if commits:
            print(f"🔀 Ветка: {branch}")
            for commit in commits:
                details = get_commit_details(commit)
                if details:
                    print(details)
            print()

if __name__ == "__main__":
    main() 