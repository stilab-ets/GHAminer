import logging
import requests
from datetime import datetime, timezone, timedelta
import time
import math
import base64


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

def count_lines_in_build_yml(repo_full_name, commit_sha, token):
    """
    Fetch the build.yml file content at a specific commit SHA and count its lines.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/contents/.github/workflows/build.yml?ref={commit_sha}"
    headers = {'Authorization': f'token {token}'}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        file_data = response.json()
        if 'content' in file_data:
            # Decode content from base64 and split by lines to count them
            content = base64.b64decode(file_data['content']).decode('utf-8')
            print("length of content of workflow is : "  , len(content.splitlines()))
            return len(content.splitlines())
        else:
            logging.error(f"No content found in build.yml at commit {commit_sha}")
    else:
        logging.error(f"Failed to fetch build.yml at commit {commit_sha}: {response.status_code}")
    return 0  # Return 0 if there's an issue with fetching or decoding


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



def get_workflow_all_ids(repo_full_name, token):
    """
    Fetch all workflow IDs for a given repository.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/actions/workflows"
    workflows_response = get_request(url, token)
    workflow_ids = []
    
    if workflows_response and 'workflows' in workflows_response:
        for workflow in workflows_response['workflows']:
            # Collect all workflow IDs, regardless of their names or paths
            workflow_ids.append(workflow['id'])
    
    return workflow_ids
