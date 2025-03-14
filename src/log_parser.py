import re
import requests
import base64
from request_github import get_request
import logging

import re

def count_dependencies(content, file_type):
    """
    Count the dependencies in the content based on the file type.
    """
    if file_type in ['pom.xml', 'build.gradle', 'build.gradle.kts']:
        # Regex for Maven and Gradle dependencies
        dependency_pattern = re.compile(r'<dependency>|implementation|compile|api|testImplementation')
        return len(dependency_pattern.findall(content))
    elif file_type == 'requirements.txt':
        # Each line in requirements.txt typically represents a dependency
        return sum(1 for line in content.splitlines() if line.strip() and not line.startswith('#'))
    elif file_type == 'package.json':
        # Look for "dependencies" and "devDependencies" sections in JSON
        dependencies = re.findall(r'\"dependencies\": {([^}]+)}|\"devDependencies\": {([^}]+)}', content)
        return sum(len(dep.split(',')) for dep in dependencies if dep)
    elif file_type == 'Gemfile':
        # Each line with 'gem' represents a dependency in Gemfile
        return len(re.findall(r'^gem ', content, re.MULTILINE))
    elif file_type == 'composer.json':
        # Count dependencies and devDependencies sections in composer.json
        dependencies = re.findall(r'\"require\": {([^}]+)}|\"require-dev\": {([^}]+)}', content)
        return sum(len(dep.split(',')) for dep in dependencies if dep)
    else:
        # Default for unsupported types
        return 0


import time
import requests
import logging

def get_github_actions_log(repo_full_name, run_id, token=None, max_retries=3):
    """
    Fetch the logs for a specific GitHub Actions workflow run.
    Handles binary (ZIP) responses correctly and retries on rate limits.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/logs"
    headers = {"Authorization": f"token {token}"} if token else {}

    retries = 0  # Track retries

    while retries < max_retries:
        try:
            response = requests.get(url, headers=headers, stream=True)  # Use raw binary stream
            
            if response.status_code == 200:
                return response.content  # Return raw binary log data
            
            elif response.status_code == 403:  # Rate limit exceeded
                rate_limit_reset = response.headers.get("X-RateLimit-Reset")
                if rate_limit_reset:
                    wait_time = int(rate_limit_reset) - int(time.time()) + 1  # Ensure at least 1s wait
                    logging.warning(f"GitHub API rate limit exceeded. Sleeping for {wait_time} seconds...")
                    time.sleep(wait_time)  # Sleep until the rate limit resets
                else:
                    logging.warning("GitHub API rate limit hit but no reset time provided. Sleeping for 60s.")
                    #time.sleep(1)  # Default sleep time before retrying
                
            elif response.status_code == 404:
                logging.error(f"Logs for build {run_id} in {repo_full_name} were not found. They may have expired.")
                return None  # No point retrying if logs don't exist
            
            else:
                logging.info(f"logs data for run {run_id} in {repo_full_name} does not exist, Status: {response.status_code}")
                return None  # Other errors should not be retried
            
        except requests.exceptions.RequestException as err:
            logging.error(f"Unexpected error fetching logs for run {run_id} in {repo_full_name}: {err}")
        
        retries += 1
        logging.warning(f"Retrying log fetch for {repo_full_name}, run {run_id} (attempt {retries}/{max_retries})")
        time.sleep(5)  # Short delay before retrying

    logging.error(f"Failed to fetch logs after {max_retries} retries for run {run_id} in {repo_full_name}")
    return None  # Return None if all retries fail


    
def get_file_content(owner, repo, path, token=None):
    """
    Fetch the content of a file from a GitHub repository.
    Uses get_request to handle rate limits properly.
    Includes explicit error handling.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

    try:
        response = get_request(url, token)
        if response and 'content' in response:
            return base64.b64decode(response['content']).decode('utf-8')
        else:
            logging.error(f"Failed to fetch file content for {path} in {owner}/{repo}")
            return None
    except base64.binascii.Error as decode_err:
        logging.error(f"Error decoding file content for {path} in {owner}/{repo}: {decode_err}")
        return None
    except Exception as err:
        logging.error(f"Unexpected error fetching file content for {path} in {owner}/{repo}: {err}")
        return None


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
                    #print("content is : " , content)
                    #print("Framework: ", framework)
                    # print("Content: ", content)
                    if framework_dependencies[framework].search(content):
                        frameworks_found.append(framework)
                except Exception as e:
                    continue

    return frameworks_found



def identify_test_frameworks_and_count_dependencies(files, owner, repo, token=None):
    """
    Identify test frameworks and count dependencies based on the presence of specific dependencies in build files.
    """
    test_frameworks = identify_test_frameworks(files, owner, repo, token)
    dependency_count = 0

    for file in files:
        # Check if the file is a recognized dependency file
        if file in ['pom.xml', 'build.gradle', 'requirements.txt', 'Gemfile', 'package.json', 'composer.json']:
            try:
                # Fetch the content of the dependency file
                content = get_file_content(owner, repo, file, token)
                # Count dependencies in this file
                dependency_count += count_dependencies(content, file)
            except Exception as e:
                print(f"Error fetching or counting dependencies in {file}: {e}")
                continue
    
    return test_frameworks, dependency_count





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







def remove_ansi_escape_sequences(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)


def parse_test_results(framework, log_content, build_language , framework_regex):
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
