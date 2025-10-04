#!/usr/bin/env python3

import subprocess
from collections import defaultdict

AUTHOR = "dependabot[bot]"

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def get_dependabot_commits():
    print("🔍 Getting dependabot commits...")
    commits = run(f'git log --author="{AUTHOR}" --pretty=format:"%H|%s"')
    return [line.split("|") for line in commits.splitlines()]

def get_files_changed(commit_hash):
    files = run(f'git show --name-only --pretty="" {commit_hash}')
    return files.splitlines()

def get_diff_for_commit(commit_hash):
    return run(f'git show {commit_hash}')

def main():
    commits = get_dependabot_commits()
    all_files = defaultdict(list)

    print(f"🧾 Found {len(commits)} dependabot commits\n")

    for commit_hash, message in commits:
        files = get_files_changed(commit_hash)
        print(f"\n📌 Commit: {commit_hash}\n🔖 Message: {message}")
        print("🗂️ Files changed:")
        for file in files:
            all_files[file].append(commit_hash)
            print(f"  - {file}")

    print("\n📊 Summary of suspicious targets (SDKs, scripts):")
    for file in all_files:
        if any(kw in file.lower() for kw in ['withdraw', 'sdk', 'handler', 'send', 'fund', 'claim']):
            print(f"⚠️ {file} — changed in commits: {', '.join(all_files[file])}")

if __name__ == "__main__":
    main()
