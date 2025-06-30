import requests
from datetime import datetime, timezone, timedelta
import csv
import os
import time
import math
import logging
import base64
import re
from collections import OrderedDict
import argparse
import json
import shutil
import numpy as np
import zipfile
import io
import yaml

from log_parser import parse_test_results , identify_test_frameworks_and_count_dependencies , identify_build_language , get_github_actions_log
from patterns import framework_regex
from commit_history_analyzer import get_commit_data_local, clone_repo_locally , calculate_sloc_and_test_lines
from repo_info_collector import get_repository_languages , get_workflow_ids , count_lines_in_workflow_yml , get_workflow_all_ids
from metrics_aggregator import save_builds_to_file
from build_run_analyzer import get_jobs_for_run , get_builds_info_from_build_yml , calculate_description_complexity
from request_github import get_request


github_token = 'your_github_token'  
output_csv = 'builds_features.csv'
from_date = None
to_date = None


class LRUCache:
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key not in self.cache:
            return None
        else:
            # Move accessed key to the end to show it was recently used
            self.cache.move_to_end(key)
            return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            # Move the existing key to the end to mark it as recently used
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.capacity:
            # Remove the first item (least recently used)
            self.cache.popitem(last=False)
        self.cache[key] = value

    def delete(self, key):
        # Add this method to allow deletion of specific keys
        if key in self.cache:
            del self.cache[key]

# Setup logging to both file and console
logging.basicConfig(filename='app.log6', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


def load_config(config_file='config.yaml'):
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        logging.error(f"Failed to load config file {config_file}: {e}")
        return {}


# Function to analyze test files for test cases/assertions
def fetch_file_content(repo_full_name, path, commit_sha, token):
    """
    Fetch the content of a file from a GitHub repository at a specific commit.
    If the file does not exist, return None instead of stopping execution.
    """
    if not path or path.strip() == "":
        return None  # Skip if path is empty

    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}?ref={commit_sha}"
    headers = {'Authorization': f'token {token}'}
    
    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            file_data = response.json()
            if 'content' in file_data:
                try:
                    return base64.b64decode(file_data['content']).decode('utf-8')
                except UnicodeDecodeError:
                    return None  # Return None if file is binary
            else:
                return None  # Return None if content is missing
        elif response.status_code == 404:
            return None  # Return None if file not found
        else:
            return None  # Return None for other errors
    except requests.exceptions.RequestException:
        return None  # Return None for network-related issues



def fetch_pull_request_details(repo_full_name, commit_sha, token):
    """Fetch pull request details including PR number, merge commit SHA, and correct comment count."""
    
    # Get PRs that contain this commit
    pr_search_url = f"https://api.github.com/repos/{repo_full_name}/commits/{commit_sha}/pulls"
    pr_response = get_request(pr_search_url, token)

    if pr_response and isinstance(pr_response, list) and len(pr_response) > 0:
        # Take the first PR found
        pr_info = pr_response[0]
        pr_number = pr_info.get('number', 0)

        # Now fetch actual PR details including total comments
        pr_details_url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
        pr_details = get_request(pr_details_url, token)

        if pr_details:
            return {
                'gh_pull_req_number': pr_number,
                'gh_is_pr': True,
                'gh_num_pr_comments': pr_details.get('comments', 0),  # This gets the correct comment count
                'git_merged_with': pr_info.get('merge_commit_sha', None),
                'gh_description_complexity': calculate_description_complexity(pr_info),
            }

    return {
        'gh_pull_req_number': 0,
        'gh_is_pr': False,
        'gh_num_pr_comments': 0,
        'git_merged_with': None,
        'gh_description_complexity': 0,
    }


def fetch_run_details(run_id, repo_full_name, token):
    """
    Fetch details about a specific run, including its jobs and steps.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/jobs"
    response = get_request(url, token)
    if response and 'jobs' in response:
        return response['jobs']  # Return the list of jobs, each containing steps
    return []




# get all files in the root of a repository
def get_github_repo_files(owner, repo, token=None):
    """
    Fetch the list of files in the root of a GitHub repository.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/"
    headers = {"Authorization": f"token {token}"} if token else {}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return [file['name'] for file in response.json() if file['type'] == 'file']



import pandas as pd

import pandas as pd
import os
import numpy as np
from datetime import datetime
import logging

def get_existing_build_ids(repo_full_name, output_csv):
    """
    Read the CSV file and return a set of existing build IDs for the given repo.
    This ensures we only fetch new builds.
    """
    if not os.path.exists(output_csv):
        return set()  # If file doesn't exist, process from scratch

    try:
        df = pd.read_csv(output_csv, usecols=['repo', 'id_build'])
        df = df[df['repo'] == repo_full_name]
        return set(df['id_build'].astype(str))  # Store existing IDs as strings for consistency
    except Exception as e:
        logging.error(f"Error reading existing build IDs from {output_csv}: {e}")
        return set()

def get_builds_info(repo_full_name, token, output_csv, framework_regex , config):
    base_path = os.path.dirname(os.path.abspath(__file__))  # Get project folder path
    repo_url = f"https://github.com/{repo_full_name}.git"
    local_repo_path = clone_repo_locally(repo_url, base_path)


    # Get already recorded build IDs
    existing_build_ids = get_existing_build_ids(repo_full_name, output_csv)

    # Fetch all workflows
    build_workflow_ids = get_workflow_all_ids(repo_full_name, token)

    languages = get_repository_languages(repo_full_name, token)
    #commit_cache = LRUCache(capacity=10000)
    repo_files = get_github_repo_files(repo_full_name.split('/')[0], repo_full_name.split('/')[1], token)
    build_language = identify_build_language(repo_files)
    test_frameworks, dependency_count = identify_test_frameworks_and_count_dependencies(
        repo_files, repo_full_name.split('/')[0], repo_full_name.split('/')[1], token
    )


    for workflow_id in build_workflow_ids:
        total_builds = 0
        page = 1
        sloc_initial = test_lines_initial = test_lines_per_1000_sloc = 0
        last_end_date = None

        while True:
            api_url = f"https://api.github.com/repos/{repo_full_name}/actions/workflows/{workflow_id}/runs?page={page}&per_page=100"
            response = requests.get(api_url, headers={'Authorization': f'token {token}'})  # Make request

            if response.status_code != 200:
                logging.error(f"Failed to fetch builds for {repo_full_name} (workflow: {workflow_id}, page: {page}), status: {response.status_code}")
                break  # Stop if request fails

            response_data = response.json()
            time.sleep(1)

            if 'workflow_runs' in response_data and response_data['workflow_runs']:
                builds_info = []
                workflow_runs = response_data['workflow_runs'] 
                #workflow_runs = sorted(workflow_runs, key=lambda run: run['created_at'])

                for idx, run in enumerate(workflow_runs):
                    run_id = str(run['id'])  # Convert ID to string for consistency
        
                    if run_id in existing_build_ids:
                        logging.info(f"Skipping existing build {run_id}")
                        continue  # Skip already processed builds

                    # If it's a new build, process it
                    existing_build_ids.add(run_id)
                    total_builds += 1

                    start_time = time.time()

                    # Extract necessary data
                    commit_sha = run['head_sha']
                    run_date = datetime.strptime(run['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    workflow_name = run.get('name', 'Unknown Workflow')
                    workflow_filename = run.get('path', 'unknown_workflow.yml')
                    event_trigger = run.get('event', 'unknown')
                    issuer = run.get('actor', {}).get('login', 'unknown')
                    workflow_id = run.get('workflow_id', 'unknown')

                    # Determine the next run's date (run+1)
                    run_plus_1_date = None
                    if idx + 1 < len(workflow_runs):
                        run_plus_1_date = datetime.strptime(workflow_runs[idx + 1]['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    

                    if config.get("fetch_sloc", False):
                        print(f"Calculating repo SLOC & test lines for first run of workflow {workflow_id}")
                        timestamp_str = run_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                        sloc_initial, test_lines_initial = calculate_sloc_and_test_lines(local_repo_path, commit_sha=commit_sha, timestamp=timestamp_str)
                        test_lines_per_1000_sloc = (test_lines_initial / sloc_initial) * 1000

                    # get commits data within the range of this run and previous run
                    commit_data = {}
                    if config.get("fetch_commit_details", False):
                        commit_data = get_commit_data_local(commit_sha, local_repo_path, run_date, run_plus_1_date)

                    # Fetch line count of the workflow YAML file
                    workflow_size = count_lines_in_workflow_yml(repo_full_name, workflow_filename, commit_sha, token)
                    if workflow_size is None:
                        workflow_size = None  # Ensure NaN is recorded


                    # time to fetch 1 row of data
                    duration_to_fetch = time.time() - start_time

                    # Compile the build info
                    build_info = compile_build_info(
                        run, repo_full_name, commit_data, sloc_initial , test_lines_per_1000_sloc,  commit_sha, languages, total_builds,
                        build_language, test_frameworks, dependency_count, workflow_size, framework_regex ,workflow_name, event_trigger, issuer, workflow_id, duration_to_fetch,
                        config
                    )
                    builds_info.append(build_info)

                    save_builds_to_file(builds_info, output_csv)

                logging.info(f"Processed page {page} of builds for workflow {workflow_id}")

            else:
                logging.info(f"No workflow runs found on page {page} for workflow {workflow_id}.")
                break  # Stop if no more data

            # **Fix Pagination Handling**
            if 'next' in response.headers.get('Link', ''):
                page += 1
            else:
                break  # No more pages left

    logging.info(f"Finished processing {repo_full_name}. Cleaning up...")

    # Delete cloned repository
    if os.path.exists(local_repo_path):
        shutil.rmtree(local_repo_path, ignore_errors=True)
        logging.info(f"Deleted temporary repository: {local_repo_path}")

    time.sleep(15)  # Prevent token exhaustion
    #unique_contributors.clear()









def compile_build_info(run, repo_full_name, commit_data, sloc_initial, test_lines_per_1000_sloc, commit_sha, languages, total_builds,
                       build_language, test_frameworks , dependency_count , workflow_size , framework_regex , workflow_name, event_trigger, issuer, workflow_id, duration_to_fetch , config):
    # Parsing build start and end times
    start_time = datetime.strptime(run['created_at'], '%Y-%m-%dT%H:%M:%SZ')
    end_time = datetime.strptime(run['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
    duration = (end_time - start_time).total_seconds()

    if config.get("fetch_job_details", False):
        jobs_ids, job_details, job_count = get_jobs_for_run(repo_full_name, run['id'], github_token)
        
        # Filter out skipped jobs and steps
        non_skipped_jobs = [
            {
                "job_name": job["job_name"],
                "steps": [step for step in job["steps"] if step["step_conclusion"] != "skipped"]
            }
            for job in job_details if job["job_result"] != "skipped"
        ]

        # Check for the keyword 'test' in job and step names of non-skipped entries
        tests_ran = any(
            "test" in job['job_name'].lower() or 
            any("test" in step['step_name'].lower() for step in job['steps'])
            for job in non_skipped_jobs
        )



    # You may get multiple frameworks; decide how to handle this case
    determined_framework = test_frameworks[0] if test_frameworks else "unknown"  # Default or handle appropriately
    cumulative_test_results = {'passed': 0, 'failed': 0, 'skipped': 0, 'total': 0}
    
    # set to true to fetch logs and parse test results
    if config.get("fetch_test_parsing_results", False):
        # Proceed with existing logic, including log fetching and parsing
        build_log = get_github_actions_log(repo_full_name, run['id'], github_token)
        
        try:
            with zipfile.ZipFile(io.BytesIO(build_log), 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith('.txt'):
                        with zip_ref.open(file_info) as log_file:
                            for line in log_file:
                                log_content = line.decode('utf-8').strip()  # Process line-by-line
                                if log_content:
                                    test_results = parse_test_results(determined_framework, log_content, build_language, framework_regex)
                                    cumulative_test_results['passed'] += test_results['passed']
                                    cumulative_test_results['failed'] += test_results['failed']
                                    cumulative_test_results['skipped'] += test_results['skipped']
                                    cumulative_test_results['total'] += test_results['total']
                                    print(f"Parsed test results from {file_info.filename}: {test_results}")
        except zipfile.BadZipFile:
            print(f"Failed to unzip log file for build {run['id']}")
        
    # Check if this build is PR-related
    if config.get("fetch_pull_request_details", False):
        pr_details = fetch_pull_request_details(repo_full_name, commit_sha, github_token)


    head_commit_data = run.get('head_commit') or {}
    first_commit_created_at = head_commit_data.get('timestamp', "N/A")


    # Compile the build information dictionary
    build_info = {
        'repo': repo_full_name,
        'id_build': run['id'],
        'workflow_id': workflow_id,
        'issuer_name': issuer,
        'branch': run['head_branch'],
        'commit_sha': commit_sha,
        'languages': languages,
        'status': run['status'],
        'workflow_event_trigger': event_trigger,
        'conclusion': run['conclusion'],
        'created_at': run['created_at'],
        'updated_at': run['updated_at'],
        'build_duration': duration,
        'total_builds': total_builds,


        #'gh_sloc': sloc_initial,

        'gh_first_commit_created_at': first_commit_created_at,  # Safely handled
        'build_language': build_language,
        'dependencies_count': dependency_count,  
        'workflow_size': workflow_size, 
        'test_framework': test_frameworks,
        'workflow_name' : workflow_name,
        'fetch_duration' : duration_to_fetch
    }

    if config.get("fetch_sloc", False):
        build_info.update({
            'gh_sloc': sloc_initial,
            'gh_test_lines_per_kloc': test_lines_per_1000_sloc
        })

    if config.get("fetch_test_parsing_results", False):
        build_info.update({
            'tests_passed': cumulative_test_results['passed'],
            'tests_failed': cumulative_test_results['failed'],
            'tests_skipped': cumulative_test_results['skipped'],
            'tests_total': cumulative_test_results['total']
        })

    if config.get("fetch_job_details", False):
        build_info.update({
            'gh_job_id': jobs_ids,
            'total_jobs': job_count,
            'job_details': json.dumps(job_details),  # Store job details as a JSON string
            'tests_ran': tests_ran
        })

    if config.get("fetch_commit_details", False):
        build_info.update({
            'gh_files_added': commit_data.get('gh_files_added', 0),
            'gh_files_deleted': commit_data.get('gh_files_deleted', 0),
            'gh_files_modified': commit_data.get('gh_files_modified', 0),
            'file_types': commit_data.get('file_types', []),
            'gh_lines_added': commit_data.get('gh_lines_added', 0),
            'gh_lines_deleted': commit_data.get('gh_lines_deleted', 0),
            'gh_src_churn': commit_data.get('gh_src_churn', 0),
            'gh_tests_added': commit_data.get('gh_tests_added', 0),
            'gh_tests_deleted': commit_data.get('gh_tests_deleted', 0),
            'gh_test_churn': commit_data.get('gh_test_churn', 0),
            'gh_src_files': commit_data.get('gh_src_files', 0),
            'gh_doc_files': commit_data.get('gh_doc_files', 0),
            'gh_other_files': commit_data.get('gh_other_files', 0),
            'gh_commits_on_files_touched': commit_data.get('gh_commits_on_files_touched', 0),
            'dockerfile_changed': commit_data.get('dockerfile_changed', 0),
            'docker_compose_changed': commit_data.get('docker_compose_changed', 0),
            'git_num_committers': commit_data.get('unique_committers', 0),
            'git_commits' : commit_data.get('git_commits' , 0),
            'gh_team_size_last_3_month': commit_data.get('committers_3_months' , 0)
        })

    if config.get("fetch_pull_request_details", False):
        build_info.update({
            'gh_pull_req_number': pr_details['gh_pull_req_number'],
            'gh_is_pr': pr_details['gh_is_pr'],
            'gh_num_pr_comments': pr_details['gh_num_pr_comments'],
            'git_merged_with': pr_details['git_merged_with'],
            'gh_description_complexity': pr_details['gh_description_complexity']
        })


    # Add additional data from commit_data
    #build_info.update(commit_data)

    return build_info




def main():
    global github_token
    global to_date
    global from_date
    projects_file = 'github_projects.csv'
    single_project = None
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--token", help="github token")
    parser.add_argument("-p", "--projects", help="csv of projects list")
    parser.add_argument("-s", "--single-project", help="GitHub repository URL for single project analysis")
    parser.add_argument("-fd", "--from_date", help="since date")
    parser.add_argument("-td", "--to_date", help="to date")
    args = parser.parse_args()

    if args.token: 
        github_token = args.token
    if args.projects:
        projects_file = args.projects
    if args.single_project:
        single_project = args.single_project
    if args.to_date:
        to_date = args.to_date
    if args.from_date:
        from_date = args.from_date

    projects = []

    config = load_config()
    
    # Handle single project or projects file
    if single_project:
        # If a single project is specified, process only that
        repo_full_name = single_project.split('/')[-2] + '/' + single_project.split('/')[-1]
        get_builds_info(repo_full_name, github_token, output_csv, framework_regex, config)
    else:
        # If a CSV file is provided, process all projects in the file
        with open(projects_file, 'r') as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                projects.append(row[0])
        
        # Process each project URL
        for project in projects:
            name = project.split('/')

            # Check if the URL is valid before proceeding
            if len(name) >= 2:
                repo_full_name = f"{name[-2]}/{name[-1]}"
                get_builds_info(repo_full_name, github_token, output_csv, framework_regex, config)
            else:
                print(name)
                logging.error(f"Invalid URL format for project: {project}")
    
    logging.info("Build information processed and saved to output CSV.")


if __name__ == "__main__":
    main()