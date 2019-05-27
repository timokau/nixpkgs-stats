#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p "python3.withPackages(ps: with ps; [ PyGithub ])"

import os
import sys
import datetime
import operator
from github import Github

TEMPLATE="""
# Community spotlight

The holy trinity for contribution to nixpkgs are direct code contribution, reviews of those contributions and merges of finished pull requests. In the past week

- {num_prs} pull request were *opened* by {num_pr_users} contributors. [@{most_pr_user}](https://github.com/{most_pr_user}) alone opened {most_pr_number} of those
- {num_reviews} pull request were *reviewed* by {num_reviews_users} contributors. [@{most_reviews_user}](https://github.com/{most_reviews_user}) alone reviewed {most_reviews_number} of those
- {num_merges} pull request were *merged* by {num_merges_users} contributors. [@{most_merges_user}](https://github.com/{most_merges_user}) alone merged {most_merges_number} of those

The most reacted to comment was [this one]({most_reacted_url}).

You can help! You do not need any special permissions to propose or review changes. Check out [this discourse thread](https://discourse.nixos.org/t/prs-already-reviewed/2617) if you want to get started with reviews.
"""
# num_prs, num_pr_users, most_pr_user, most_pr_numbers

def in_timeframe(date, now):
    return now - date < datetime.timedelta(days=7)

def dict_to_sorted_list(stats):
    inverted = dict()
    for (login, number) in stats.items():
        inverted[number] = inverted.get(number, []) + [login]
    return sorted(inverted.items(), key=operator.itemgetter(0), reverse=True)

def print_leaderboard(stats):
    sorted_stats = dict_to_sorted_list(stats)

    for (rank, (number, logins)) in enumerate(sorted_stats, start=1):
        login_list = ', '.join(logins)
        print(f'{rank}. {login_list} ({number})')

def main():
    # https://github.com/settings/tokens
    GITHUB_API_TOKEN = os.environ.get('GITHUB_API_TOKEN', None)
    if GITHUB_API_TOKEN is None:
        print('You need to export GITHUB_API_TOKEN')
        sys.exit(1)

    now = datetime.datetime.now()
    github = Github(GITHUB_API_TOKEN)
    repo = github.get_repo("NixOS/nixpkgs")
    pulls = repo.get_pulls(
        state='all',
        sort='updated',
        direction="desc",
    )
    reviews = dict()
    merges = dict()
    opens = dict()

    most_reacted = None
    most_reactions = 0

    for pull in pulls:
        approved_by = []
        if not in_timeframe(pull.updated_at, now):
            break
        print(pull)
        if in_timeframe(pull.created_at, now):
            user = pull.user
            print(f"{user.login} opens")
            opens[user.login] = opens.get(user.login, 0) + 1
        for review in list(pull.get_reviews()):
            if not in_timeframe(review.submitted_at, now):
                continue
            user = review.user
            state = review.state
            if state == "CHANGES_REQUESTED":
                print(f"{user.login} requests")
                reviews[user.login] = reviews.get(user.login, 0) + 1
            elif state == "APPROVED":
                reviews[user.login] = reviews.get(user.login, 0) + 1
                print(f"{user.login} approves")
                approved_by += [user.login]
            elif state == "COMMENTED":
                pass
        for comment in list(pull.get_comments()):
            if not in_timeframe(comment.created_at, now):
                continue
            reactions = len(list(comment.get_reactions()))
            if reactions > most_reactions:
                most_reactions = reactions
                most_reacted = comment

        if pull.is_merged():
            if in_timeframe(pull.merged_at, now):
                user = pull.merged_by
                if len(approved_by) == 0:
                    print(f"{user.login} implicitly approves by merge")
                    reviews[user.login] = reviews.get(user.login, 0) + 1
                elif user.login not in approved_by:
                    print(f"{user.login} merges with existing review")
                    merges[user.login] = merges.get(user.login, 0) + 1

    # Ignore bot PRs
    opens.pop('r-ryantm', None)

    opens_sorted = dict_to_sorted_list(opens)
    reviews_sorted = dict_to_sorted_list(reviews)
    merges_sorted = dict_to_sorted_list(merges)

    def total(stats):
        return sum([num for (num, _) in stats])
    def count_users(stats):
        return sum([len(logins) for (_, logins) in stats])

    print(TEMPLATE.format(
        num_prs=total(opens_sorted),
        num_pr_users=count_users(opens_sorted),
        most_pr_user=opens_sorted[0][1][0],
        most_pr_number=opens_sorted[0][0],

        num_reviews=total(reviews_sorted),
        num_reviews_users=count_users(reviews_sorted),
        most_reviews_user=reviews_sorted[0][1][0],
        most_reviews_number=reviews_sorted[0][0],

        num_merges=total(merges_sorted),
        num_merges_users=count_users(merges_sorted),
        most_merges_user=merges_sorted[0][1][0],
        most_merges_number=merges_sorted[0][0],

        most_reacted_url=most_reacted.html_url,
    ))

if __name__ == "__main__":
    main()
