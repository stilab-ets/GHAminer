import logging
import requests
from datetime import datetime, timezone, timedelta
import time
import math
import base64
from request_github import get_request


def count_lines_in_workflow_yml(repo_full_name, workflow_path, commit_sha, token):
    """
    Fetch the workflow YAML file content at a specific commit SHA and count its lines.
    Uses get_request to handle rate limits and retries properly.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{workflow_path}?ref={commit_sha}"

    try:
        response = get_request(url, token)
        if response and 'content' in response:
            try:
                # Decode Base64 content, split by lines, and count
                content = base64.b64decode(response['content']).decode('utf-8')
                line_count = len(content.splitlines())
                print(f"Length of content of {workflow_path}: {line_count}")
                return line_count
            except base64.binascii.Error as decode_err:
                logging.error(f"Error decoding {workflow_path} at commit {commit_sha}: {decode_err}")
                return 0
        else:
            logging.error(f"No content found in {workflow_path} at commit {commit_sha}")
    except Exception as err:
        logging.error(f"Unexpected error fetching {workflow_path} at commit {commit_sha}: {err}")

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
