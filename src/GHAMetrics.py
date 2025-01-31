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

from log_parser import parse_test_results , identify_test_frameworks_and_count_dependencies , identify_build_language , get_github_actions_log
from patterns import framework_regex
from commit_history_analyzer import get_commit_data, get_commit_data_local, clone_repo_locally
from repo_info_collector import get_repository_languages , get_workflow_ids , count_lines_in_workflow_yml , get_workflow_all_ids
from metrics_aggregator import save_builds_to_file , save_head
from build_run_analyzer import get_jobs_for_run , get_builds_info_from_build_yml , calculate_description_complexity
from request_github import get_request


import zipfile
import io

github_token = 'your_token_here'  
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


# Function to analyze test files for test cases/assertions

def fetch_file_content(repo_full_name, path, commit_sha, token):
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}?ref={commit_sha}"
    headers = {'Authorization': f'token {token}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_data = response.json()
        # Files are base64 encoded by GitHub, so decode them
        if 'content' in file_data:
            try:
                return base64.b64decode(file_data['content']).decode('utf-8')
            except UnicodeDecodeError:
                logging.error(f"Binary file detected and skipped: {path} at commit {commit_sha}")
                return ""  # Return empty string if binary file detected
        else:
            logging.error(f"No content found in {path} at commit {commit_sha}")
    else:
        logging.error(f"Failed to fetch file content: {response.status_code}, URL: {url}")
    return ""  # Return empty string if there is an error fetching the file



import time
import logging
from datetime import datetime, timedelta, timezone
import requests

def get_team_size_last_three_months(repo_full_name, token, commit_cache):
    """
    Efficiently fetches the number of unique contributors in the last three months.
    Uses cached commit data if available, otherwise fetches from GitHub with rate limits in mind.
    """
    last_commit_url = f"https://api.github.com/repos/{repo_full_name}/commits"
    committers = set()

    # Check cached commits before making API requests
    cached_commits = [commit for commit in commit_cache.cache.keys() if commit.startswith(repo_full_name)]
    
    if cached_commits:
        logging.info(f"Using cached commits for {repo_full_name}")
        for commit_sha in cached_commits:
            commit_data = commit_cache.get(commit_sha)
            if commit_data:
                committers.add(commit_data.get('author', ''))  # Ensure author login is stored

        if len(committers) > 0:
            return len(committers)  # Return cached team size if data is available

    logging.info(f"Fetching commits for {repo_full_name} from GitHub as cache is incomplete.")

    # Get the latest commit date
    response = get_request(last_commit_url, token)
    if not response or not isinstance(response, list) or 'commit' not in response[0]:
        logging.error(f"Failed to fetch commits for {repo_full_name}")
        return None

    last_commit_date = datetime.strptime(response[0]['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ')
    start_date = last_commit_date - timedelta(days=90)  # Three months prior

    # API request to fetch commits within the last 3 months
    commits_url = f"{last_commit_url}?since={start_date.isoformat()}Z&until={last_commit_date.isoformat()}Z"

    attempt = 0  # Retry counter

    while commits_url:
        try:
            raw_response = requests.get(commits_url, headers={'Authorization': f'token {token}'})

            if raw_response.status_code == 200:
                response = raw_response.json()  # Convert to JSON list of commits

                for commit in response:
                    if commit.get('committer') and commit['committer'].get('login'):
                        committers.add(commit['committer']['login'])
                        commit_sha = commit.get('sha')
                        if commit_sha:
                            commit_cache.put(f"{repo_full_name}-{commit_sha}", {"author": commit['committer']['login']})

                # Extract the next page URL from headers
                link_header = raw_response.headers.get('Link', '')
                commits_url = None  # Default to None, if no pagination exists
                if link_header:
                    links = {rel.split(";")[1].strip(): rel.split(";")[0].strip("<>") for rel in link_header.split(",")}
                    if 'rel="next"' in links:
                        commits_url = links['rel="next"']

                attempt = 0  # Reset attempt counter after a successful request

            elif raw_response.status_code == 403 and 'X-RateLimit-Reset' in raw_response.headers:
                # Handle GitHub rate limits
                reset_time = datetime.fromtimestamp(int(raw_response.headers['X-RateLimit-Reset']), timezone.utc)
                sleep_time = (reset_time - datetime.now(timezone.utc)).total_seconds() + 10
                logging.warning(f"Rate limit exceeded, sleeping for {sleep_time:.2f} seconds before retrying.")
                time.sleep(sleep_time)

            else:
                logging.error(f"Failed to fetch commits, status code: {raw_response.status_code}")
                attempt += 1
                time.sleep(min(2 ** attempt, 60))  # Exponential backoff (max 60s)

                if attempt > 5:  # Maximum retries
                    logging.error("Max retries reached, aborting commit fetch.")
                    break

        except requests.RequestException as e:
            logging.error(f"Error fetching commits: {e}")
            attempt += 1
            time.sleep(min(2 ** attempt, 60))  # Exponential backoff (max 60s)

            if attempt > 5:
                logging.error("Max retries reached due to request errors, aborting commit fetch.")
                break

    return len(committers)







def fetch_pull_request_details(repo_full_name, pr_number, token):
    """Fetch pull request details including the merge commit SHA if merged."""
    pr_url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
    pr_response = get_request(pr_url, token)
    if pr_response:
        # Fetches merge commit SHA from the pull request details if it exists
        pr_details = {
            'title': pr_response.get('title', ''),
            'body': pr_response.get('body', ''),
            'comments_count': pr_response.get('comments', 0),  # Number of comments
            'merge_commit_sha': pr_response.get('merge_commit_sha', None)  # SHA of the merge commit if PR is merged
        }
        return pr_details
    return {}


def fetch_run_details(run_id, repo_full_name, token):
    """
    Fetch details about a specific run, including its jobs and steps.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/jobs"
    response = get_request(url, token)
    if response and 'jobs' in response:
        return response['jobs']  # Return the list of jobs, each containing steps
    return []




def count_commits_on_files(repo_full_name, files, token, last_commit_date):
    unique_commits = set()
    headers = {'Authorization': f'token {token}'}
    end_date = last_commit_date
    start_date = end_date - timedelta(days=90)

    for file in files:
        commits_url = f"https://api.github.com/repos/{repo_full_name}/commits?path={file['filename']}&since={start_date.isoformat()}Z&until={end_date.isoformat()}Z"
        while True:
            response = requests.get(commits_url, headers=headers)
            if response.status_code == 200:
                commits_data = response.json()
                for commit in commits_data:
                    unique_commits.add(commit['sha'])

                if 'next' in response.links:
                    commits_url = response.links['next']['url']
                else:
                    break
            else:
                logging.error(
                    f"Failed to fetch commits for file {file['filename']}, status code: {response.status_code}, response: {response.text}")
                break

    return len(unique_commits)





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



# end new functions

def get_builds_info(repo_full_name, token, output_csv, framework_regex):
    base_path = os.path.dirname(os.path.abspath(__file__))  # Get project folder path
    
    repo_url = f"https://github.com/{repo_full_name}.git"
    local_repo_path = clone_repo_locally(repo_url, base_path)

    # Read the configuration from config.json
    try:
        with open("config.json", "r") as config_file:
            config = json.load(config_file)
        fetch_all_workflows = config.get("fetch_all_workflows", True)  # Default to True
    except FileNotFoundError:
        logging.warning("config.json not found. Defaulting to fetching all workflows.")
        fetch_all_workflows = True

    # Call the appropriate function based on the configuration
    if fetch_all_workflows:
        build_workflow_ids = get_workflow_all_ids(repo_full_name, token)
    else:
        build_workflow_ids = get_workflow_ids(repo_full_name, token)

    languages = get_repository_languages(repo_full_name, token)
    commit_cache = LRUCache(capacity=10000)
    gh_team_size = get_team_size_last_three_months(repo_full_name, token, commit_cache)
    repo_files = get_github_repo_files(repo_full_name.split('/')[0], repo_full_name.split('/')[1], token)
    build_language = identify_build_language(repo_files)
    test_frameworks, dependency_count = identify_test_frameworks_and_count_dependencies(
        repo_files, repo_full_name.split('/')[0], repo_full_name.split('/')[1], token
    )
    unique_builds = set()
    last_end_date = None  # Initialize to track end date of each build

    # Initialize a set to track unique contributors up to each commit
    unique_contributors = set()

    if not build_workflow_ids:
        logging.error("No workflows found.")
        return

    workflow_files = {}  # Stores {workflow_id: (workflow_name, file_path)}

    for workflow_id in build_workflow_ids:
        workflow_info_url = f"https://api.github.com/repos/{repo_full_name}/actions/workflows/{workflow_id}"
        workflow_info = get_request(workflow_info_url, token)

        if workflow_info and 'name' in workflow_info and 'path' in workflow_info:
            workflow_files[workflow_id] = (workflow_info['name'], workflow_info['path'])  # Store tuple (name, path)
        else:
            workflow_files[workflow_id] = ("Unknown Workflow", "unknown_workflow.yml")  # Fallback


    for workflow_id in build_workflow_ids:
        total_builds = 0
        page = 1
        sloc, test = 0, 0
        while True:
            api_url = f"https://api.github.com/repos/{repo_full_name}/actions/workflows/{workflow_id}/runs?page={page}&per_page=100"
            response_data = get_request(api_url, token)
            if response_data and 'workflow_runs' in response_data:
                builds_info = []
                for run in response_data['workflow_runs'][::-1]:
                    run_id = run['id']
                    if run_id in unique_builds:
                        logging.info(f"Skipping duplicate build {run_id}")
                        continue
                    unique_builds.add(run_id)
                    total_builds += 1

                    start_time = time.time()

                    commit_sha = run['head_sha']
                    until_date = datetime.strptime(run['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    
                    # Fetch correct workflow file name from mapped workflow IDs
                    workflow_name, workflow_filename = workflow_files.get(workflow_id, ("Unknown Workflow", "unknown_workflow.yml"))

                    # Pass the unique_contributors set to be updated within get_commit_data_local
                    commit_data = get_commit_data_local(
                        commit_sha, local_repo_path, until_date, last_end_date, commit_cache, unique_contributors
                    )

                    # Fetch line count of the correct workflow YAML file at the specific commit
                    workflow_size = count_lines_in_workflow_yml(repo_full_name, workflow_filename, commit_sha, token)

                    # Compile the build info, using the length of unique_contributors here
                    build_info = compile_build_info(
                        run, repo_full_name, commit_data, commit_sha, languages,
                        len(unique_contributors), total_builds,
                        gh_team_size, build_language, test_frameworks, dependency_count, workflow_size, framework_regex
                    )

                    # Add workflow name to build info
                    build_info['workflow_name'] = workflow_name  # Use actual workflow name

                    duration_to_fetch = time.time() - start_time
                    build_info['fetch_duration'] = duration_to_fetch  # Add the duration as a new field
                    builds_info.clear()
                    builds_info.append(build_info)
                    save_builds_to_file(builds_info, output_csv)

                    # Update last_end_date to the end time of this build
                    last_end_date = datetime.strptime(run['updated_at'], '%Y-%m-%dT%H:%M:%SZ')

                logging.info(f"Processed page {page} of builds for workflow {workflow_id}")
                if 'next' not in response_data.get('links', {}):
                    break
                page += 1
            else:
                break

    # Process repository...
    logging.info(f"Finished processing {repo_full_name}. Cleaning up...")

    # Delete cloned repository
    if os.path.exists(local_repo_path):
        shutil.rmtree(local_repo_path, ignore_errors=True)
        logging.info(f"Deleted temporary repository: {local_repo_path}")

    # Sleep to avoid hitting API limits
    time.sleep(15)  # Prevent token exhaustion


    # Reset unique contributors after processing each repository
    unique_contributors.clear()







def compile_build_info(run, repo_full_name, commit_data, commit_sha, languages, number_of_committers, total_builds, gh_team_size,
                       build_language, test_frameworks , dependency_count , workflow_size , framework_regex):
    # Parsing build start and end times
    start_time = datetime.strptime(run['created_at'], '%Y-%m-%dT%H:%M:%SZ')
    end_time = datetime.strptime(run['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
    duration = (end_time - start_time).total_seconds()
    jobs_ids, job_count = get_jobs_for_run(repo_full_name, run['id'], github_token)  # Get job IDs and count

    ### NEWLY ADDED CODE ##############################################################
    # You may get multiple frameworks; decide how to handle this case
    determined_framework = test_frameworks[0] if test_frameworks else "unknown"  # Default or handle appropriately

    # Proceed with existing logic, including log fetching and parsing
    build_log = get_github_actions_log(repo_full_name, run['id'], github_token)
    cumulative_test_results = {'passed': 0, 'failed': 0, 'skipped': 0, 'total': 0}

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
    ### END OF NEWLY ADDED CODE #######################################################

    # Initialize default values
    pr_number = 0
    description_complexity = 0
    pr_comments_count = 0
    merge_commit_sha = None  # Initialize merge commit SHA

    # Check if the build was triggered by a pull request
    gh_is_pr = run['event'] == 'pull_request' and len(run['pull_requests']) > 0
    if gh_is_pr:
        if 'pull_requests' in run and run['pull_requests']:
            pr_number = run['pull_requests'][0]['number']
            if pr_number:
                pr_details = fetch_pull_request_details(repo_full_name, pr_number, github_token)
                if pr_details:
                    description_complexity = calculate_description_complexity(pr_details)
                    pr_comments_count = pr_details.get('comments_count', 0)
                    merge_commit_sha = pr_details.get('merge_commit_sha', None)

    # Determine if tests ran by checking 'steps' in each job
    run_details = fetch_run_details(run['id'], repo_full_name, github_token)
    tests_ran = any("test" in step['name'].lower() for job in run_details for step in job.get('steps', []))

    # Compile the build information dictionary
    build_info = {
        'repo': repo_full_name,
        'id_build': run['id'],
        'branch': run['head_branch'],
        'commit_sha': commit_sha,
        'workflow_name': "Unknown",
        'languages': languages,
        'status': run['status'],
        'conclusion': run['conclusion'],
        'created_at': run['created_at'],
        'updated_at': run['updated_at'],
        'build_duration': duration,
        'total_builds': total_builds,
        'tests_ran': tests_ran,
        'gh_src_churn': commit_data.get('gh_src_churn', 0),
        'gh_pull_req_number': pr_number,
        'gh_is_pr': gh_is_pr,
        'gh_num_pr_comments': pr_comments_count,
        'git_merged_with': merge_commit_sha,
        'gh_description_complexity': description_complexity,
        'git_num_committers': number_of_committers,
        'gh_job_id': jobs_ids,
        'total_jobs': job_count,
        'gh_first_commit_created_at': run['head_commit']['timestamp'],
        'gh_team_size_last_3_month': gh_team_size,
        'build_language': build_language,
        'dependencies_count': dependency_count,  
        'workflow_size': workflow_size, 
        'test_framework': test_frameworks,
        'tests_passed': cumulative_test_results['passed'],
        'tests_failed': cumulative_test_results['failed'],
        'tests_skipped': cumulative_test_results['skipped'],
        'tests_total': cumulative_test_results['total']
    }

    # Add additional data from commit_data
    build_info.update(commit_data)

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
    
    # Handle single project or projects file
    if single_project:
        # If a single project is specified, process only that
        repo_full_name = single_project.split('/')[-2] + '/' + single_project.split('/')[-1]
        save_head(output_csv)
        get_builds_info(repo_full_name, github_token, output_csv, framework_regex)
    else:
        # If a CSV file is provided, process all projects in the file
        with open(projects_file, 'r') as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                projects.append(row[0])

        save_head(output_csv)
        
        # Process each project URL
        for project in projects:
            name = project.split('/')
            
            # Check if the URL is valid before proceeding
            if len(name) >= 2:
                repo_full_name = f"{name[-2]}/{name[-1]}"
                get_builds_info(repo_full_name, github_token, output_csv, framework_regex)
            else:
                print(name)
                logging.error(f"Invalid URL format for project: {project}")
    
    logging.info("Build information processed and saved to output CSV.")

if __name__ == "__main__":
    main()
