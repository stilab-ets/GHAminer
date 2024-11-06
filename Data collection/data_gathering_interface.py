import requests
from datetime import datetime, timezone, timedelta
from pydriller import Repository
import csv
import os
import time
import math
import logging
import base64
import re
from collections import OrderedDict
import argparse

import zipfile
import io

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

# Setup logging to both file and console
logging.basicConfig(filename='app.log6', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# Use environment variables for sensitive information


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


def calculate_total_loc(commit, commit_cache):
    """
    Calculate LOC (lines of code) metrics for a single commit.
    """
    total_added = 0
    total_removed = 0
    tests_added = 0
    tests_removed = 0

    # Use the commit hash and committer date as cache keys
    commit_key = (commit['sha'], commit['commit']['committer']['date'])
    cached_data = commit_cache.get(commit_key)
    
    if cached_data:
        # Use cached data if available
        return (
            cached_data['total_added'],
            cached_data['total_removed'],
            cached_data['tests_added'],
            cached_data['tests_removed']
        )

    # If not cached, process the files in the commit
    for file in commit['files']:
        if is_test_file(file['filename']):
            tests_added += file['additions']
            tests_removed += file['deletions']
        else:
            total_added += file['additions']
            total_removed += file['deletions']

    # Cache the results for this commit to avoid recomputation
    commit_cache.put(commit_key, {
        'total_added': total_added,
        'total_removed': total_removed,
        'tests_added': tests_added,
        'tests_removed': tests_removed
    })

    return total_added, total_removed, tests_added, tests_removed





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


def is_test_file(file_name):
    test_indicators = ['test', 'tests', 'spec', '__tests__', 'unittest', '/tests/', '/spec/']
    return any(indicator in file_name.lower() for indicator in test_indicators)


def is_production_file(file_path):
    # Expanded list of programming language extensions
    production_extensions = [
        '.py', '.java', '.cpp', '.js', '.ts', '.c', '.h', '.cs', '.swift', '.go',
        '.rb', '.php', '.kt', '.scala', '.groovy', '.rs', '.m', '.lua', '.pl',
        '.sh', '.bash', '.sql', '.ps1', '.cls', '.trigger', '.f', '.f90', '.asm',
        '.s', '.vhd', '.vhdl', '.verilog', '.sv', '.tml', '.json', '.xml', '.html',
        '.css', '.sass', '.less', '.jsp', '.asp', '.aspx', '.erb', '.twig', '.hbs'
    ]
    test_indicators = ['test', 'tests', 'spec', '__tests__']
    return (
            not any(indicator in file_path for indicator in test_indicators) and
            file_path.endswith(tuple(production_extensions))
    )

def is_documentation_file(file_path):
    doc_extensions = ('.md', '.rst', '.txt', '.pdf')
    doc_directories = ['doc', 'docs', 'documentation', 'guide', 'help', 'manual', 'manuals', 'guides']

    lower_path = file_path.lower()
    if lower_path.endswith(doc_extensions):
        return True

    if lower_path.endswith('.html'):
        path_segments = lower_path.split('/')
        if any(doc_dir in path_segments for doc_dir in doc_directories):
            return True
        if any(doc_dir in lower_path for doc_dir in doc_directories):
            return True

        return False

    path_segments = lower_path.split('/')
    if any(doc_dir in path_segments for doc_dir in doc_directories):
        return True

    return False


def get_unique_committers(repo_full_name):
    url = f"https://api.github.com/repos/{repo_full_name}/contributors"
    headers = {}
    committers = set()

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            contributors = response.json()
            for contributor in contributors:
                # Add the login name of the contributor
                committers.add(contributor['login'])
            # Pagination: Check if there is a 'next' page
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                break
        else:
            logging.error(f"Failed to fetch contributors, status code: {response.status_code}, URL: {url}")
            break
    return len(committers), committers


def get_team_size_last_three_months(repo_full_name, token):
    last_commit_url = f"https://api.github.com/repos/{repo_full_name}/commits"
    headers = {'Authorization': f'token {token}'}
    response = requests.get(last_commit_url, headers=headers)
    if response.status_code == 200:
        last_commit_date = datetime.strptime(response.json()[0]['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ')
        start_date = last_commit_date - timedelta(days=90)  # Three months prior
        commits_url = f"{last_commit_url}?since={start_date.isoformat()}Z&until={last_commit_date.isoformat()}Z"
        committers = set()

        while True:
            response = requests.get(commits_url, headers=headers)
            if response.status_code == 200:
                commits_data = response.json()
                for commit in commits_data:
                    if commit['committer']:
                        committers.add(commit['committer']['login'])

                # Check if there's another page of commits
                if 'next' in response.links:
                    commits_url = response.links['next']['url']
                else:
                    break
            else:
                logging.error(f"Failed to fetch commits, status code: {response.status_code}")
                return None

        return len(committers)
    else:
        logging.error(f"Failed to fetch last commit, status code: {response.status_code}")
        return None


def get_repository_languages(repo_full_name, token):
    url = f"https://api.github.com/repos/{repo_full_name}/languages"
    languages_data = get_request(url, token)
    if languages_data:
        total_bytes = sum(languages_data.values())
        language = max(languages_data, key=lambda lang: languages_data[lang] / total_bytes)
        return language
    return "No language found"


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



def calculate_description_complexity(pr_details):
    if not pr_details:
        logging.error("No PR details available for complexity calculation.")
        return 0  # Return 0 complexity if pr_details is None or empty

    title_words = pr_details.get('title', '').split()
    description_words = pr_details.get('body', '').split() if pr_details.get('body') else []

    total_words = len(title_words) + len(description_words)
    logging.info(f"PR Title: {pr_details.get('title', '')}")
    logging.info(f"PR Description Length: {len(description_words)} words")
    logging.info(f"Total complexity (words in PR): {total_words}")

    return total_words


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


def get_builds_info_from_build_yml_old(repo_full_name, token):
    build_workflow_ids = get_workflow_ids(repo_full_name, token)
    total_builds = 0
    for workflow_id in build_workflow_ids:
        page = 1
        url = f"https://api.github.com/repos/{repo_full_name}/actions/workflows/{workflow_id}/runs"
        runs_response = get_request(url, token)
        if runs_response and 'workflow_runs' in runs_response:
            total_builds = runs_response['total_count']

    return total_builds


def get_builds_info_from_build_yml(repo_full_name, token, date_limit=None):
    """
    Retrieve the count of builds up to a specified date_limit.
    """
    build_workflow_ids = get_workflow_ids(repo_full_name, token)
    total_builds = 0
    for workflow_id in build_workflow_ids:
        page = 1
        while True:
            url = f"https://api.github.com/repos/{repo_full_name}/actions/workflows/{workflow_id}/runs?page={page}&per_page=100"
            runs_response = get_request(url, token)
            if not (runs_response and 'workflow_runs' in runs_response):
                break

            for run in runs_response['workflow_runs']:
                # Convert GitHub datetime string to datetime object
                run_date = datetime.strptime(run['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                # Only count runs up to the date_limit
                if date_limit and run_date > date_limit:
                    continue
                total_builds += 1

            # Break if there are no more pages
            if 'next' not in runs_response.get('links', {}):
                break
            page += 1

    return total_builds



def get_jobs_for_run(repo_full_name, run_id, token):
    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/jobs"
    headers = {'Authorization': f'token {token}'}
    jobs_response = requests.get(url, headers=headers).json()
    jobs_ids = []
    if jobs_response and 'jobs' in jobs_response:
        for job in jobs_response['jobs']:
            jobs_ids.append(job['id'])
    return jobs_ids, len(jobs_ids)  # Return both job IDs and the count of jobs


### NEWLY ADDED FUCNTIONS ##############################################################

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


# Identify the build language based on the presence of specific build files.
def identify_build_language(files):
    """
    Identify the build language based on the presence of specific build files.
    """
    build_file_mapping = {
        'ruby': ['Gemfile', 'Rakefile'],
        'java-ant': ['build.xml'],
        'java-maven': ['pom.xml'],
        'java-gradle': ['build.gradle', 'settings.gradle', 'build.gradle.kts']
    }

    for language, build_files in build_file_mapping.items():
        if any(file in files for file in build_files):
            return language
    return None


# new functions
def get_file_content(owner, repo, path, token=None):
    """
    Fetch the content of a file from a GitHub repository.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"} if token else {}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    content = response.json().get('content', '')
    return base64.b64decode(content).decode('utf-8')


def identify_test_frameworks(files, owner, repo, token=None):
    """
    Identify the test frameworks based on the presence of specific dependencies in build files.
    """
    test_framework_mapping = {
        'junit': ['pom.xml', 'build.gradle'],
        'rspec': ['Gemfile', 'Rakefile'],
        'testunit': ['Gemfile'],
        'cucumber-ruby': ['Gemfile', 'Rakefile'],
        'cucumber-java': ['pom.xml', 'build.gradle'],
        'phpunit': ['composer.json'],
        'pytest': ['requirements.txt', 'setup.py', 'pyproject.toml'],
        'unittest': ['requirements.txt', 'setup.py', 'pyproject.toml'],
        'jest': ['package.json'],
        'mocha': ['package.json']
    }
    framework_dependencies = {
        'junit': re.compile(r'junit'),
        'rspec': re.compile(r'rspec'),  # r'gem\s*[\'"]rspec[\'"]|require\s*[\'"]rspec[\'"]'),
        'testunit': re.compile(r'gem\s*[\'"]test-unit[\'"]'),
        'cucumber-ruby': re.compile(r'gem\s*[\'"]cucumber[\'"]|cucumber'),
        'cucumber-java': re.compile(r'cucumber-java|cucumber-junit|io.cucumber:cucumber'),
        'phpunit': re.compile(r'"phpunit/phpunit"'),
        'pytest': re.compile(r'pytest'),
        'unittest': re.compile(r'unittest'),
        'jest': re.compile(r'"jest"'),
        'mocha': re.compile(r'"mocha"')
    }

    frameworks_found = []

    for framework, paths in test_framework_mapping.items():
        for path in paths:
            if path in files:
                try:
                    content = get_file_content(owner, repo, path, token)
                    #print("Framework: ", framework)
                    # print("Content: ", content)
                    if framework_dependencies[framework].search(content):
                        frameworks_found.append(framework)
                except Exception as e:
                    continue

    return frameworks_found


framework_regex = {
    "pytest": re.compile(r"(?:(\d+)\s+passed)?(?:, )?(?:(\d+)\s+failed)?(?:, )?(?:(\d+)\s+skipped)?"),
    "Jest": re.compile(r"Tests: (\d+) total, (\d+) passed, (\d+) failed, (\d+) skipped"),
    "junit-gradle": re.compile(r"Passed: (\d+), Failed: (\d+), Errors: (\d+), Skipped: (\d+)"),
    "rspec": re.compile(r"(\d+) examples?, (\d+) failures?(?:, (\d+) pending)?"),
    "PHPUnit": re.compile(r"Tests: (\d+), Assertions: (\d+), Failures: (\d+), Skipped: (\d+)"),
    "NUnit": re.compile(r"Total tests: (\d+) - Passed: (\d+), Failed: (\d+), Skipped: (\d+)"),
    "Go test": re.compile(r"PASS: (\d+), FAIL: (\d+), SKIP: (\d+)"),
    "junit-maven": re.compile(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)"),
    "cucumber-ruby": re.compile(
        r"(\d+) scenarios? \((?:(\d+ skipped)(?:, )?)?(?:(\d+ undefined)(?:, )?)?(?:(\d+ failed)(?:, )?)?(?:(\d+ passed))?\)[\s\S]*?(\d+) steps? \((?:(\d+ skipped)(?:, )?)?(?:(\d+ undefined)(?:, )?)?(?:(\d+ failed)(?:, )?)?(?:(\d+ passed))?\)"),
    "Cucumber-Java": re.compile(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)"),
    "testunit": re.compile(
        r"(\d+) tests, (\d+) assertions, (\d+) failures, (\d+) errors, (\d+) pendings, (\d+) omissions, (\d+) notifications")
}


def remove_ansi_escape_sequences(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)


def get_github_repo_files(owner, repo, token=None):
    """
    Fetch the list of files in the root of a GitHub repository.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/"
    headers = {"Authorization": f"token {token}"} if token else {}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return [file['name'] for file in response.json() if file['type'] == 'file']


def get_github_actions_runs(owner, repo, token=None):
    """
    Fetch the list of workflow runs for a GitHub repository.
    """
    # fourth page of runs

    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
    headers = {"Authorization": f"token {token}"} if token else {}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    # length of runs
    print("Length of runs: ", len(response.json()['workflow_runs']))
    return response.json()['workflow_runs']


def get_github_actions_log(repo_full_name, run_id, token=None):
    """
    Fetch the logs for a specific GitHub Actions workflow run.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/logs"
    headers = {"Authorization": f"token {token}"} if token else {}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.content
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - URL: {url}")
        return None
    except Exception as err:
        print(f"Other error occurred: {err} - URL: {url}")
        return None


def parse_test_results(framework, log_content, build_language):
    """
    Parse the test results from the log content.
    """
    log_content = remove_ansi_escape_sequences(log_content)  # Remove ANSI escape codes
    if framework == "junit" and build_language == "java-maven":
        framework = "junit-maven"
    if framework == "junit" and build_language == "java-gradle":
        framework = "junit-gradle"

    if framework in framework_regex:
        #print("Framework: ", framework)
        #print("Build Language: ", build_language)

        # special case for junit-java and junit-maven
        if framework == "junit" and build_language == "java-maven":
            regex = framework_regex["junit-maven"]
            matches = regex.findall(log_content)
        elif framework == "junit" and build_language == "java-gradle":
            regex = framework_regex["junit-java"]
            matches = regex.findall(log_content)
        else:
            regex = framework_regex[framework]
            matches = regex.findall(log_content)

        # Debug statements
        # print("Log content: ", log_content)
        # print("Matches found: ", matches)

        if matches:
            passed_tests = 0
            failed_tests = 0
            skipped_tests = 0
            errors_tests = 0

            for match in matches:
                if framework == "pytest":
                    if match[0]:
                        passed_tests += int(match[0])
                    if match[1]:
                        failed_tests += int(match[1])
                    if match[2]:
                        skipped_tests += int(match[2])
                elif framework == "junit-gradle":
                    passed_tests += int(match[0])
                    failed_tests += int(match[1])
                    errors_tests += int(match[2])  # Count errors for JUnit
                    skipped_tests += int(match[3])

                elif framework == "junit-maven":
                    passed_tests += int(match[0]) - int(match[1]) - int(match[2]) - int(
                        match[3])  # Subtract failed, errors, and skipped
                    failed_tests += int(match[1])
                    errors_tests += int(match[2])  # Count errors for JUnit
                    skipped_tests += int(match[3])


                elif framework == "rspec":
                    if match[0]:
                        passed_tests += int(match[0])
                    if match[1]:
                        failed_tests += int(match[1])
                        passed_tests -= int(match[1])  # Subtract failed tests from passed
                    if match[2]:
                        skipped_tests += int(match[2])
                        passed_tests -= int(match[2])  # Subtract skipped tests from passed
                elif framework == "cucumber-ruby":
                    scenarios_skipped = int(match[1].split()[0]) if match[1] else 0
                    scenarios_undefined = int(match[2].split()[0]) if match[2] else 0
                    scenarios_failed = int(match[3].split()[0]) if match[3] else 0
                    scenarios_passed = int(match[4].split()[0]) if match[4] else 0
                    steps_skipped = int(match[6].split()[0]) if match[6] else 0
                    steps_undefined = int(match[7].split()[0]) if match[7] else 0
                    steps_failed = int(match[8].split()[0]) if match[8] else 0
                    steps_passed = int(match[9].split()[0]) if match[9] else 0

                    passed_tests += scenarios_passed + steps_passed
                    failed_tests += scenarios_failed + steps_failed
                    skipped_tests += scenarios_skipped + steps_skipped
                    # undefined_tests += scenarios_undefined + steps_undefined
                    # No skipped or errors for this format
                    # No errors for this format
                elif framework == "Cucumber-Java":
                    passed_tests += int(match[0])
                    failed_tests += int(match[1])
                    errors_tests += int(match[2])
                    skipped_tests += int(match[3])
                elif framework == "testunit":
                    passed_tests += int(match[0])
                    # assertions += int(match[1])
                    failed_tests += int(match[2])
                    errors_tests += int(match[3])
                    # pendings, omissions, and notifications are not being counted in total

            total_tests = passed_tests + failed_tests + skipped_tests + errors_tests

            return {
                'passed': passed_tests,
                'failed': failed_tests,
                'skipped': skipped_tests,
                'total': total_tests
            }

    return {'passed': 0, 'failed': 0, 'skipped': 0, 'total': 0}


def summarize_test_results(test_results):
    """
    Summarize the test results in the desired format.
    """
    summary = {
        'tr tests ok': test_results.get('passed', 0),
        'tr tests fail': test_results.get('failed', 0),
        'tr tests run': test_results.get('total', 0),
        'tr tests skipped': test_results.get('skipped', 0),
        'tr failed tests': []  # Optionally add the names of failed tests if available
    }
    return summary


# end new functions


def get_builds_info(repo_full_name, token, output_csv):
    languages = get_repository_languages(repo_full_name, token)
    build_workflow_ids = get_workflow_ids(repo_full_name, token)
    number_of_committers, _ = get_unique_committers(repo_full_name)
    gh_team_size = get_team_size_last_three_months(repo_full_name, token)
    repo_files = get_github_repo_files(repo_full_name.split('/')[0], repo_full_name.split('/')[1], token)
    build_language = identify_build_language(repo_files)
    test_framework = identify_test_frameworks(repo_files, repo_full_name.split('/')[0], repo_full_name.split('/')[1], token)
    unique_builds = set()
    commit_cache = LRUCache(capacity=10000)
    last_end_date = None  # Initialize to track end date of each build

    if not build_workflow_ids:
        logging.error("No build workflows found.")
        return

    for workflow_id in build_workflow_ids:
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

                    commit_sha = run['head_sha']
                    commit_data = get_commit_data(commit_sha, repo_full_name, last_end_date, token, sloc, test, commit_cache)
                    if commit_data.get('gh_sloc', 0) == 0:
                        logging.info(f"Skipping commit {commit_sha} with 0 SLOC")
                        continue

                    build_info = compile_build_info(run, repo_full_name, commit_data, commit_sha, languages,
                                                    number_of_committers, gh_team_size, build_language, test_framework)
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


def get_commit_data(commit_sha, repo_full_name, last_end_date, token, sloc, test, commit_cache):
    # Initialize metrics
    total_added = total_removed = tests_added = tests_removed = 0
    test_additions = test_deletions = prod_additions = prod_deletions = 0
    src_files = doc_files = other_files = unique_files_added = unique_files_deleted = unique_files_modified = 0
    file_types = set()
    commits_on_files_touched = set()

    # Check cache for commit data to avoid redundant calculations
    if commit_cache.get(commit_sha):
        return commit_cache.get(commit_sha)

    headers = {'Authorization': f'token {token}'}
    url = f"https://api.github.com/repos/{repo_full_name}/commits/{commit_sha}"

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logging.error(f"Error fetching commit details for {commit_sha}: {response.status_code}")
            return {}  # Early return on error

        commit_data = response.json()
        files = commit_data.get('files', [])
        
        for file in files:
            filename = file.get('filename', '')
            additions = file.get('additions', 0)
            deletions = file.get('deletions', 0)
            change_type = file.get('status', '')

            # Aggregate metrics based on file type
            if is_test_file(filename):
                tests_added += additions
                tests_removed += deletions
            elif is_production_file(filename):
                prod_additions += additions
                prod_deletions += deletions
                src_files += 1
            elif is_documentation_file(filename):
                doc_files += 1
            else:
                other_files += 1

            # Track file types and changes
            file_types.add(os.path.splitext(filename)[1])
            if change_type == "added":
                unique_files_added += 1
            elif change_type == "deleted":
                unique_files_deleted += 1
            elif change_type == "modified":
                unique_files_modified += 1

            # Track unique commits affecting files
            commits_on_files_touched.add(commit_sha)

        # Calculate LOC for the current commit using calculate_total_loc
        loc_added, loc_removed, test_loc_added, test_loc_removed = calculate_total_loc(commit_data, commit_cache)
        total_added += loc_added
        total_removed += loc_removed
        tests_added += test_loc_added
        tests_removed += test_loc_removed

    except Exception as e:
        logging.error(f"Error in get_commit_data: {e}")
        return {}

    # Calculate test lines per KLOC
    tests_per_kloc = (tests_added / (total_added + tests_added) * 1000) if (total_added + tests_added) > 0 else 0

    # Prepare and cache final results
    final_data = {
        'gh_sloc': total_added + tests_added,
        'gh_test_lines_per_kloc': tests_per_kloc,
        'gh_files_added': unique_files_added,
        'gh_files_deleted': unique_files_deleted,
        'gh_files_modified': unique_files_modified,
        'gh_src_files': src_files,
        'gh_doc_files': doc_files,
        'gh_other_files': other_files,
        'gh_lines_added': prod_additions,
        'gh_lines_deleted': prod_deletions,
        'file_types': ', '.join(file_types),
        'gh_tests_added': tests_added,
        'gh_tests_deleted': tests_removed,
        'gh_test_churn': tests_added + tests_removed,
        'gh_src_churn': prod_additions + prod_deletions,
        'gh_commits_on_files_touched': len(commits_on_files_touched),
    }

    # Cache and return final aggregated data for the commit
    commit_cache.put(commit_sha, final_data)
    return final_data






import requests  # Ensure requests is imported if not already

def get_commit_data_debug(commit_sha, repo_full_name, last_end_date, token, sloc, test, commit_cache):
    # Initialize metrics
    total_added = total_removed = tests_added = tests_removed = 0
    test_additions = test_deletions = prod_additions = prod_deletions = 0
    src_files = doc_files = other_files = unique_files_added = unique_files_deleted = unique_files_modified = 0
    file_types = set()
    commits_on_files_touched = set()

    # Temporarily skip cache for debugging purposes
    # if commit_cache.get(commit_sha):
    #     return commit_cache.get(commit_sha)

    # Set up API parameters for commit range fetching
    headers = {'Authorization': f'token {token}'}
    url = f"https://api.github.com/repos/{repo_full_name}/commits"
    params = {'sha': commit_sha, 'until': datetime.utcnow().isoformat() + 'Z'}
    if last_end_date:
        params['since'] = last_end_date.isoformat() + 'Z'

    try:
        # Fetch commits within the specified range
        while url:
            response = requests.get(url, headers=headers, params=params)
            print(f"URL: {response.url}")  # Debug: Print full URL with parameters
            print(f"Status Code: {response.status_code}")  # Debug: Print response status code

            if response.status_code != 200:
                logging.error(f"Error fetching commits: {response.status_code}")
                break

            commits_data = response.json()
            print("Response JSON:", commits_data)  # Debug: Print raw JSON response to inspect contents

            # Now process the data
            for commit in commits_data:
                commit_hash = commit['sha']
                commit_data = commit_cache.get(commit_hash)
                print("Processing commit hash:", commit_hash)  # Debug: Print commit being processed

                # Fetch commit details if not cached (we are still skipping cache for debugging)
                if not commit_data:
                    # Fetch detailed commit data for the specific commit to get files info
                    commit_url = f"https://api.github.com/repos/{repo_full_name}/commits/{commit_hash}"
                    commit_response = requests.get(commit_url, headers=headers)
                    print(f"Commit URL: {commit_url} Status: {commit_response.status_code}")  # Debug
                    print("Commit Response JSON:", commit_response.json())  # Debug: check 'files'

                    if commit_response.status_code == 200:
                        detailed_commit = commit_response.json()
                        # Now detailed_commit should include 'files', handle accordingly
                        # Further processing here...
                    else:
                        logging.error(f"Error fetching commit details for {commit_hash}")
                        continue

                # Update metrics here as needed, following your original logic

            # Check for pagination
            url = response.links.get('next', {}).get('url')

    except Exception as e:
        logging.error(f"Error in get_commit_data: {e}")

    # Additional debugging or final metrics aggregation logic can go here

    # Prepare and cache final results for production once resolved
    final_data = {
        # Populate as per requirements
    }
    # commit_cache.put(commit_sha, final_data)  # Uncomment after debugging

    return final_data



def compile_build_info(run, repo_full_name, commit_data, commit_sha, languages, number_of_committers, gh_team_size,
                       build_language, test_framework):
    # Parsing build start and end times
    start_time = datetime.strptime(run['created_at'], '%Y-%m-%dT%H:%M:%SZ')
    end_time = datetime.strptime(run['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
    duration = (end_time - start_time).total_seconds()
    total_builds = get_builds_info_from_build_yml(repo_full_name, github_token, date_limit=end_time)
    jobs_ids, job_count = get_jobs_for_run(repo_full_name, run['id'], github_token)  # Get job IDs and count
    repo_files = get_github_repo_files(repo_full_name.split('/')[0], repo_full_name.split('/')[1], github_token)
    test_frameworks = identify_test_frameworks(repo_files, repo_full_name.split('/')[0], repo_full_name.split('/')[1],
                                               github_token)

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
                        log_content = log_file.read().decode('utf-8')
                        if log_content:
                            test_results = parse_test_results(determined_framework, log_content, build_language)
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
        'test_framework': test_framework,
        'tests_passed': cumulative_test_results['passed'],
        'tests_failed': cumulative_test_results['failed'],
        'tests_skipped': cumulative_test_results['skipped'],
        'tests_total': cumulative_test_results['total']
    }

    # Add additional data from commit_data
    build_info.update(commit_data)

    return build_info


def save_builds_to_file(builds_info, output_csv):
    """Save builds information to a CSV file."""
    fieldnames = [
        'repo', 'id_build', 'branch', 'commit_sha', 'languages', 'status', 'conclusion', 'created_at',
        'updated_at', 'build_duration', 'total_builds', 'gh_files_added', 'gh_files_deleted', 'gh_files_modified',
        'tests_ran', 'gh_lines_added', 'gh_lines_deleted', 'file_types', 'gh_tests_added',
        'gh_tests_deleted', 'gh_test_churn', 'gh_src_churn', 'gh_pull_req_number', 'gh_is_pr', 'gh_sloc',
        'gh_description_complexity', 'gh_src_files', 'gh_doc_files', 'gh_other_files', 'git_num_committers',
        'gh_job_id', 'total_jobs', 'gh_first_commit_created_at', 'gh_team_size_last_3_month',
        'gh_commits_on_files_touched', 'gh_num_pr_comments', 'git_merged_with', 'gh_test_lines_per_kloc',
        'build_language', 'test_framework', 'tests_passed', 'tests_failed', 'tests_skipped', 'tests_total'
    ]
    with open(output_csv, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        for build in builds_info:
            writer.writerow(build)
    logging.info(f"Build information saved to {output_csv}")


def save_head(output_csv):
    """Save builds information to a CSV file."""
    fieldnames = [
        'repo', 'id_build', 'branch', 'commit_sha', 'languages', 'status', 'conclusion', 'created_at',
        'updated_at', 'build_duration', 'total_builds', 'gh_files_added', 'gh_files_deleted', 'gh_files_modified',
        'tests_ran', 'gh_lines_added', 'gh_lines_deleted', 'file_types', 'gh_tests_added',
        'gh_tests_deleted', 'gh_test_churn', 'gh_src_churn', 'gh_pull_req_number', 'gh_is_pr', 'gh_sloc',
        'gh_description_complexity', 'gh_src_files', 'gh_doc_files', 'gh_other_files', 'git_num_committers',
        'gh_job_id', 'total_jobs', 'gh_first_commit_created_at', 'gh_team_size_last_3_month',
        'gh_commits_on_files_touched', 'gh_num_pr_comments', 'git_merged_with', 'gh_test_lines_per_kloc',
        'build_language', 'test_framework', 'tests_passed', 'tests_failed', 'tests_skipped', 'tests_total'
    ]
    with open(output_csv, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
    logging.info(f"Build information saved to {output_csv}")


def main():
    global github_token
    global to_date
    global from_date
    projects_file = 'github_projects.csv'
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--token", help="github token")
    parser.add_argument("-p", "--projects", help="csv of projects list")
    parser.add_argument("-fd", "--from_date", help="since date")
    parser.add_argument("-td", "--to_date", help="to date")
    args = parser.parse_args()
    if args.token : 
        github_token = args.token
    if args.projects:
        projects_file = args.projects
    if args.to_date:
        to_date = args.to_date
    if args.from_date:
        to_date = args.from_date

    

    projects = []
    
    # Read the CSV file and append projects
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
            get_builds_info(repo_full_name, github_token, output_csv)
        else:
            print(name)
            logging.error(f"Invalid URL format for project: {project}")
    
    logging.info("Build information processed and saved to output CSV.")

if __name__ == "__main__":
    main()