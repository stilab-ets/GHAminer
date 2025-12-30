import logging
import requests
from datetime import datetime, timezone, timedelta
import time
import math
import base64
from request_github import get_request

import base64
import logging

import numpy as np  # Import numpy for NaN

def count_lines_in_workflow_yml(repo_full_name, workflow_path, commit_sha, token):
    """
    Fetch the workflow YAML file content at a specific commit SHA and count its lines.
    If the file is missing, returns np.nan instead of stopping execution.
    """
    if not workflow_path or workflow_path.strip() == "":
        return None  # Return NaN if path is empty

    url = f"https://api.github.com/repos/{repo_full_name}/contents/{workflow_path}?ref={commit_sha}"

    try:
        response = get_request(url, token)

        if response and 'content' in response:
            try:
                content = base64.b64decode(response['content']).decode('utf-8')
                return len(content.splitlines())  # Return line count
            except (base64.binascii.Error, UnicodeDecodeError):
                return np.nan  # Return NaN if file is binary or unreadable
        elif response and response.get('message') == 'Not Found':
            return None  # Return NaN if file is not found
        else:
            return None # Return NaN for other errors
    except Exception:
        return None  # Return NaN if there's an unexpected error






def get_repository_languages(repo_full_name, token):
    url = f"https://api.github.com/repos/{repo_full_name}/languages"
    languages_data = get_request(url, token)
    if languages_data:
        total_bytes = sum(languages_data.values())
        language = max(languages_data, key=lambda lang: languages_data[lang] / total_bytes)
        return language
    return "No language found"



def get_workflow_ids(repo_full_name, token, specific_workflow_ids=None):
    """
    Fetch workflow IDs for a given repository.
    
    Args:
        repo_full_name (str): The full repository name (owner/repo).
        token (str): GitHub API token.
        specific_workflow_ids (list, optional): List of specific workflow IDs to filter.
            - If None or empty list: returns ALL workflow IDs in the repository.
            - If non-empty list: returns only the specified workflow IDs (validated against existing workflows).
    
    Returns:
        list: List of workflow IDs to process.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/actions/workflows"
    workflows_response = get_request(url, token)
    
    if not workflows_response or 'workflows' not in workflows_response:
        return []
    
    # Get all available workflow IDs from the repository
    all_workflow_ids = [workflow['id'] for workflow in workflows_response['workflows']]
    
    # If specific_workflow_ids is None or empty, return all workflows
    if not specific_workflow_ids:
        logging.info(f"No specific workflows configured. Processing all {len(all_workflow_ids)} workflows.")
        return all_workflow_ids
    
    # Filter to only include specified workflow IDs that exist in the repository
    valid_workflow_ids = [wid for wid in specific_workflow_ids if wid in all_workflow_ids]
    
    # Log warnings for any specified IDs that don't exist
    invalid_ids = [wid for wid in specific_workflow_ids if wid not in all_workflow_ids]
    if invalid_ids:
        logging.warning(f"The following workflow IDs were not found in {repo_full_name}: {invalid_ids}")
    
    logging.info(f"Processing {len(valid_workflow_ids)} specified workflows out of {len(all_workflow_ids)} available.")
    return valid_workflow_ids


def get_workflow_ids_by_name(repo_full_name, token, workflow_names=None):
    """
    Fetch workflow IDs by workflow file names or paths.
    
    Args:
        repo_full_name (str): The full repository name (owner/repo).
        token (str): GitHub API token.
        workflow_names (list, optional): List of workflow file names to filter (e.g., ['build.yml', 'test.yml']).
            - If None or empty list: returns ALL workflow IDs in the repository.
            - If non-empty list: returns only workflows matching the specified names.
    
    Returns:
        list: List of workflow IDs to process.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/actions/workflows"
    workflows_response = get_request(url, token)
    
    if not workflows_response or 'workflows' not in workflows_response:
        return []
    
    # If workflow_names is None or empty, return all workflows
    if not workflow_names:
        return [workflow['id'] for workflow in workflows_response['workflows']]
    
    # Filter workflows by name/path
    matched_workflow_ids = []
    for workflow in workflows_response['workflows']:
        workflow_path = workflow.get('path', '').lower()
        workflow_file = workflow_path.split('/')[-1] if workflow_path else ''
        
        for name in workflow_names:
            name_lower = name.lower()
            # Match by exact file name or partial path match
            if name_lower == workflow_file or name_lower in workflow_path:
                matched_workflow_ids.append(workflow['id'])
                break
    
    return matched_workflow_ids


def get_workflow_all_ids(repo_full_name, token):
    """
    Fetch all workflow IDs for a given repository.
    This is a convenience wrapper around get_workflow_ids with no filtering.
    """
    return get_workflow_ids(repo_full_name, token, specific_workflow_ids=None)
