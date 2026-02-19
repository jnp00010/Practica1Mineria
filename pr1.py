import datetime

from github import Github
import csv
import time
from itertools import combinations
from collections import defaultdict

# ==============================
# CONFIGURACIÓN
# ==============================

GITHUB_TOKEN = "Pon aqui tu token"

SEED_REPOSITORIES = [
    "tensorflow/tensorflow",
    "pytorch/pytorch"
]

MAX_CONTRIBUTORS_PER_REPO = 30
MAX_REPOS_PER_USER = 5

# ==============================
# INICIALIZAR API
# ==============================

from github import Github, Auth

# Autenticación moderna
auth = Auth.Token(GITHUB_TOKEN)
g = Github(auth=auth)



def check_rate_limit():
    rate_limit = g.get_rate_limit()
    remaining = rate_limit.core.remaining
    reset_time = rate_limit.core.reset

    if remaining < 10:
        sleep_time = (reset_time - datetime.utcnow()).total_seconds()
        print(f"Esperando {sleep_time} segundos por rate limit...")
        time.sleep(max(sleep_time, 0))


# ==============================
# ESTRUCTURAS
# ==============================

nodes = {}
edges = defaultdict(int)


# ==============================
# FUNCIONES
# ==============================

def process_repository(repo_full_name):
    print(f"Procesando repo: {repo_full_name}")

    repo = g.get_repo(repo_full_name)
    contributors = repo.get_contributors()

    contributor_logins = []

    for i, contributor in enumerate(contributors):
        if i >= MAX_CONTRIBUTORS_PER_REPO:
            break

        contributor_logins.append(contributor.login)

        # Guardamos nodo
        if contributor.login not in nodes:
            nodes[contributor.login] = {
                "Id": contributor.login,
                "Label": contributor.login,
                "Followers": contributor.followers
            }

    # Generar aristas entre todos los contribuidores del repo
    for user1, user2 in combinations(contributor_logins, 2):
        edge = tuple(sorted([user1, user2]))
        edges[edge] += 1


def expand_from_user(user_login):
    print(f"Expandiendo desde usuario: {user_login}")

    user = g.get_user(user_login)
    repos = user.get_repos(sort="stars")

    for i, repo in enumerate(repos):
        if i >= MAX_REPOS_PER_USER:
            break

        try:
            process_repository(repo.full_name)
        except Exception as e:
            print(f"Error en repo {repo.full_name}: {e}")
            continue


# ==============================
# EJECUCIÓN PRINCIPAL
# ==============================

def main():
    # Paso 1: procesar repos semilla
    for repo in SEED_REPOSITORIES:
        process_repository(repo)

    # Paso 2: expansión
    usuarios_iniciales = list(nodes.keys())

    for user in usuarios_iniciales:
        try:
            expand_from_user(user)
        except Exception as e:
            print(f"Error expandiendo usuario {user}: {e}")
            continue

    # ==============================
    # GUARDAR CSV NODOS
    # ==============================

    with open("nodes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Id", "Label", "Followers"])
        writer.writeheader()
        for node in nodes.values():
            writer.writerow(node)

    # ==============================
    # GUARDAR CSV ARISTAS
    # ==============================

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
    print(f"Nodos: {len(nodes)}")
    print(f"Aristas: {len(edges)}")


if __name__ == "__main__":
    main()

