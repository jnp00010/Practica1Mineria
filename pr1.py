import csv
import time
from itertools import combinations
from collections import defaultdict

from github import Github, Auth

GITHUB_TOKEN = "Tu token de GitHub"

SEED_REPOSITORIES = [
    "tensorflow/tensorflow",
    "pytorch/pytorch"
]

MAX_CONTRIBUTORS_PER_REPO = 25
MAX_REPOS_PER_USER = 3
MAX_USERS_TO_EXPAND = 20
MAX_TOTAL_REPOS = 150

auth = Auth.Token(GITHUB_TOKEN)
g = Github(auth=auth)


def check_rate_limit():

    remaining, limit = g.rate_limiting

    reset_ts = getattr(g, "rate_limiting_resettime", None)

    if remaining < 10 and reset_ts:
        now_ts = int(time.time())
        sleep_time = max(reset_ts - now_ts, 0) + 5
        print(f"Rate limit casi agotado ({remaining}/{limit}). Esperando {sleep_time}s...")
        time.sleep(sleep_time)

nodes = {}
edges = defaultdict(int)
processed_repos = set()


def process_repository(repo_full_name):
    if repo_full_name in processed_repos:
        return
    if len(processed_repos) >= MAX_TOTAL_REPOS:
        return

    processed_repos.add(repo_full_name)
    print(f"Procesando repo: {repo_full_name}  (total repos: {len(processed_repos)}/{MAX_TOTAL_REPOS})")

    check_rate_limit()
    repo = g.get_repo(repo_full_name)

    check_rate_limit()
    contributors = repo.get_contributors()

    contributor_logins = []

    for i, contributor in enumerate(contributors):
        if i >= MAX_CONTRIBUTORS_PER_REPO:
            break

        contributor_logins.append(contributor.login)

        if contributor.login not in nodes:
            check_rate_limit()
            nodes[contributor.login] = {
                "Id": contributor.login,
                "Label": contributor.login,
                "Followers": contributor.followers
            }

    for user1, user2 in combinations(contributor_logins, 2):
        edge = tuple(sorted([user1, user2]))
        edges[edge] += 1


def expand_from_user(user_login):
    if len(processed_repos) >= MAX_TOTAL_REPOS:
        return

    print(f"Expandiendo desde usuario: {user_login}")

    check_rate_limit()
    user = g.get_user(user_login)

    check_rate_limit()
    repos = user.get_repos(sort="stars")

    for i, repo in enumerate(repos):
        if i >= MAX_REPOS_PER_USER:
            break
        if len(processed_repos) >= MAX_TOTAL_REPOS:
            break

        try:
            process_repository(repo.full_name)
        except Exception as e:
            print(f"Error en repo {repo.full_name}: {e}")
            continue

def main():

    for repo in SEED_REPOSITORIES:
        process_repository(repo)

    usuarios_iniciales = list(nodes.keys())[:MAX_USERS_TO_EXPAND]

    for user in usuarios_iniciales:
        if len(processed_repos) >= MAX_TOTAL_REPOS:
            break
        try:
            expand_from_user(user)
        except Exception as e:
            print(f"Error expandiendo usuario {user}: {e}")
            continue

    with open("nodes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Id", "Label", "Followers"])
        writer.writeheader()
        for node in nodes.values():
            writer.writerow(node)

    with open("edges.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Source", "Target", "Weight"])
        writer.writeheader()
        for (source, target), weight in edges.items():
            writer.writerow({
                "Source": source,
                "Target": target,
                "Weight": weight
            })

    print("Proceso terminado.")
    print(f"Repos procesados: {len(processed_repos)}")
    print(f"Nodos: {len(nodes)}")
    print(f"Aristas: {len(edges)}")


if __name__ == "__main__":
    main()