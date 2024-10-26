from datetime import datetime, timedelta
from github import Github
import yaml
import csv
import pandas as pd
import requests
from github import Auth

repositories = []

# Token d'authentification pour l'API GitHub
token = "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"

# using an access token
auth = Auth.Token(token)

g = Github(auth=auth)

# Dates de début et de fin de la recherche
start_date = datetime(2019, 1, 1)
end_date = datetime(2024, 6, 12)
output_csv = 'projects.csv'

while start_date <= end_date:
    # Crée la requête de recherche pour la plage de dates actuelle
    query = f"created:{start_date.strftime('%Y-%m-%d')}..{start_date.strftime('%Y-%m-%d')}"

    # Exécute la recherche de dépôts avec la requête actuelle
    results = g.search_repositories(query=query)

    # Boucle sur les résultats pour vérifier si le répertoire .github/workflows existe dans le dépôt
    for repo in results:
        try:
            workflows = repo.get_contents(".github/workflows/build.yml")
            with open(output_csv, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=['url'])
                writer.writerow({"url": repo.html_url})
        except Exception as e:
            continue

    # Incrémente la date de début pour passer à la prochaine journée dans la plage de dates
    start_date += timedelta(days=1)

# Créer un dictionnaire pur stocker tous les actions utilisées pour chaque repo
repo_actions = {}


def save_builds_to_file(project, output_csv):
    """Save builds information to a CSV file."""
    fieldnames = [
        'project'
    ]
    with open(output_csv, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        for build in builds_info:
            writer.writerow(build)
    logging.info(f"Build information saved to {output_csv}")


