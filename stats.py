#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p "python3.withPackages(ps: with ps; [ PyGithub ])"

import os
import datetime
import operator
from github import Github

def in_timeframe(date, now):
    return now - date < datetime.timedelta(days=7)

def print_leaderboard(stats):
    s_stats = sorted(stats.items(), key=operator.itemgetter(1), reverse=True)
    for (rank, (login, number)) in enumerate(s_stats, start=1):
        print(f'{rank}. {login} ({number})')

def main():
    # https://github.com/settings/tokens
    GITHUB_API_TOKEN = os.environ.get('GITHUB_API_TOKEN', None)

    now = datetime.datetime.now()
    github = Github(GITHUB_API_TOKEN)
    repo = github.get_repo("NixOS/nixpkgs")
    pulls = repo.get_pulls(
        state='all',
        sort='updated',
        direction="desc",
    )
    approvals = dict()
    changes = dict()
    merges = dict()
    opens = dict()
    for pull in pulls:
        approval_by = None
        if not in_timeframe(pull.updated_at, now):
            break
        print(pull)
        if in_timeframe(pull.created_at, now):
            user = pull.user
            print(f"{user.login} opens")
            opens[user.login] = opens.get(user.login, 0) + 1
        reviews = list(pull.get_reviews())
        for review in reviews:
            if not in_timeframe(review.submitted_at, now):
                continue
            user = review.user
            state = review.state
            if state == "CHANGES_REQUESTED":
                print(f"{user.login} requests")
                changes[user.login] = changes.get(user.login, 0) + 1
            elif state == "APPROVED":
                approvals[user.login] = approvals.get(user.login, 0) + 1
                print(f"{user.login} approves")
                approval_by = user
            elif state == "COMMENTED":
                pass
        if pull.is_merged():
            if in_timeframe(pull.merged_at, now):
                user = pull.merged_by
                if approval_by is None:
                    print(f"{user.login} approves")
                    approvals[user.login] = approvals.get(user.login, 0) + 1
                print(f"{user.login} merges")
                merges[user.login] = merges.get(user.login, 0) + 1

    print("\n### Approvals\n")
    print_leaderboard(approvals)
    print("\n### Requests for changes\n")
    print_leaderboard(changes)
    print("\n### Merges\n")
    print_leaderboard(merges)
    print("\n### New PRs\n")
    print_leaderboard(opens)

if __name__ == "__main__":
    main()
