import logging
import requests
from datetime import datetime, timezone, timedelta
import time
import math


def get_request(url, token):
    headers = {'Authorization': f'token {token}'}
    attempt = 0
    while attempt < 5:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403 and 'X-RateLimit-Reset' in response.headers:
            reset_time = datetime.fromtimestamp(int(response.headers['X-RateLimit-Reset']), timezone.utc)
            sleep_time = (reset_time - datetime.now(timezone.utc)).total_seconds() + 10
            logging.error(f"Rate limit exceeded, sleeping for {sleep_time} seconds. URL: {url}")
            time.sleep(sleep_time)
        else:
            logging.error(
                f"Failed to fetch data, status code: {response.status_code}, URL: {url}, Response: {response.text}")
            time.sleep(math.pow(2, attempt) * 10)  # Exponential backoff
        attempt += 1
    return None



def get_repository_languages(repo_full_name, token):
    url = f"https://api.github.com/repos/{repo_full_name}/languages"
    languages_data = get_request(url, token)
    if languages_data:
        total_bytes = sum(languages_data.values())
        language = max(languages_data, key=lambda lang: languages_data[lang] / total_bytes)
        return language
    return "No language found"



def get_workflow_ids(repo_full_name, token):
    url = f"https://api.github.com/repos/{repo_full_name}/actions/workflows"
    workflows_response = get_request(url, token)
    build_workflow_ids = []
    if workflows_response and 'workflows' in workflows_response:
        for workflow in workflows_response['workflows']:
            # Assuming workflows defined in build.yml have 'build' in their name or in the path as build.yml
            if '/build.yml' in workflow['path'].lower():
                build_workflow_ids.append(workflow['id'])
    return build_workflow_ids