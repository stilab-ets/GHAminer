import requests
import logging
from datetime import datetime, timezone, timedelta
import os
from file_indicators import is_production_file , is_test_file
import subprocess


import shutil

import os
import subprocess
import shutil

def clone_repo_locally(repo_url, base_path):
    """Clone the repository inside a tmp/ directory in the project folder."""
    tmp_dir = os.path.join(base_path, "tmp")  # Ensure tmp directory inside project
    os.makedirs(tmp_dir, exist_ok=True)  # Create tmp/ if it doesn't exist

    repo_name = repo_url.split("/")[-1].replace(".git", "")  # Ensure clean repo name
    local_repo_path = os.path.join(tmp_dir, repo_name)  # Unique folder for each repo
    git_path = shutil.which("git") or r"C:\Program Files\Git\cmd\git.exe"  # Find git

    print(f"📂 Cloning repo into: {local_repo_path}")

    if not os.path.exists(local_repo_path):
        result = subprocess.run([git_path, "clone", repo_url, local_repo_path], capture_output=True, text=True)

        if result.returncode != 0:
            logging.error(f"Error cloning repo: {result.stderr}")
            return None  # Return None if cloning fails
        else:
            print(f"✅ Successfully cloned repo into {local_repo_path}")
    else:
        print(f"🟡 Repository already exists at {local_repo_path}, ensuring all commits are available.")

    # Ensure full commit history is available
    try:
        subprocess.run([git_path, "-C", local_repo_path, "fetch", "--all"], check=True, capture_output=True, text=True)
        subprocess.run([git_path, "-C", local_repo_path, "pull", "--all"], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to fetch all commits for {repo_name}: {e}")

    return local_repo_path  # Return the path so it can be used later




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

def compile_final_data(
    total_added, total_removed, tests_added, tests_removed,
    src_files, doc_files, other_files, unique_files_added,
    unique_files_deleted, unique_files_modified, file_types,
    commits_on_files_touched, unique_contributors, commit_cache, commit_sha
):
    # Calculate test lines per KLOC
    tests_per_kloc = (tests_added / (total_added + tests_added) * 1000) if (total_added + tests_added) > 0 else 0

    # Prepare the aggregated data for all processed commits
    final_data = {
        'gh_sloc': total_added + tests_added,
        'gh_test_lines_per_kloc': tests_per_kloc,
        'gh_files_added': unique_files_added,
        'gh_files_deleted': unique_files_deleted,
        'gh_files_modified': unique_files_modified,
        'gh_src_files': src_files,
        'gh_doc_files': doc_files,
        'gh_other_files': other_files,
        'gh_lines_added': total_added,
        'gh_lines_deleted': total_removed,
        'file_types': ', '.join(file_types),
        'gh_tests_added': tests_added,
        'gh_tests_deleted': tests_removed,
        'gh_test_churn': tests_added + tests_removed,
        'gh_src_churn': total_added + total_removed,
        'gh_commits_on_files_touched': len(commits_on_files_touched),
        'git_num_committers': len(unique_contributors)
    }

    # Cache the final data for this commit set
    commit_cache.put(commit_sha, final_data)
    return final_data


def fetch_full_commit_data(commit_sha, repo_full_name, token, unique_contributors):
    """Fetch detailed commit data including contributors, additions, and deletions."""
    headers = {'Authorization': f'token {token}'}
    url = f"https://api.github.com/repos/{repo_full_name}/commits/{commit_sha}"

    

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logging.error(f"Error fetching commit details for {commit_sha}: {response.status_code}")
            return {}

        commit_data = response.json()
        files = commit_data.get('files', [])
        total_added = total_removed = tests_added = tests_removed = 0
        src_files = doc_files = other_files = 0
        file_types = set()

        # Update unique contributors based on the author of this commit
        author = commit_data.get('author')
        if author and author.get('login'):
            unique_contributors.add(author['login'])

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
                total_added += additions
                total_removed += deletions
                src_files += 1
            elif is_documentation_file(filename):
                doc_files += 1
            else:
                other_files += 1

            # Track unique file types
            file_types.add(os.path.splitext(filename)[1])

        return {
            'total_added': total_added,
            'total_removed': total_removed,
            'tests_added': tests_added,
            'tests_removed': tests_removed,
            'src_files': src_files,
            'doc_files': doc_files,
            'other_files': other_files,
            'file_types': file_types,
        }

    except Exception as e:
        logging.error(f"Error in fetch_full_commit_data: {e}")
        return {}
    


def fetch_full_commit_data_local(commit_sha, local_repo_path, unique_contributors):
    """Fetch detailed commit data using local Git instead of GitHub API."""
    try:
        # Ensure the repository exists
        if not os.path.exists(local_repo_path):
            logging.error(f"Repository path does not exist: {local_repo_path}")
            return {}

        # Get commit details (author name and changed files)
        result = subprocess.run(
            ["git", "-C", local_repo_path, "show", "--numstat", "--pretty=format:%an", commit_sha],
            capture_output=True, text=True, check=True
        )

        output = result.stdout.strip().split("\n")

        if not output:
            logging.error(f"Commit {commit_sha} has no valid output from git show")
            return {}

        # Extract commit author
        author_name = output[0].strip() if output else "Unknown"
        unique_contributors.add(author_name)  # Track contributor

        # Initialize commit metadata
        total_added = total_removed = tests_added = tests_removed = 0
        src_files = doc_files = other_files = 0
        file_types = set()
        file_changes = []

        # Process file changes
        for line in output[1:]:  # Skip author line
            parts = line.split("\t")
            if len(parts) != 3:
                continue  # Skip malformed lines

            added_lines, removed_lines, filename = parts
            added_lines = int(added_lines) if added_lines.isdigit() else 0
            removed_lines = int(removed_lines) if removed_lines.isdigit() else 0

            # Classify files
            if is_test_file(filename):
                tests_added += added_lines
                tests_removed += removed_lines
            elif is_production_file(filename):
                total_added += added_lines
                total_removed += removed_lines
                src_files += 1
            elif is_documentation_file(filename):
                doc_files += 1
            else:
                other_files += 1

            # Track file extensions
            file_extension = os.path.splitext(filename)[1]
            if file_extension:
                file_types.add(file_extension)

            # Store file change data
            file_changes.append({
                "file_path": filename,
                "added_lines": added_lines,
                "removed_lines": removed_lines
            })

        return {
            'author': author_name,
            'total_added': total_added,
            'total_removed': total_removed,
            'tests_added': tests_added,
            'tests_removed': tests_removed,
            'src_files': src_files,
            'doc_files': doc_files,
            'other_files': other_files,
            'file_types': file_types,
            'file_changes': file_changes  # Store file-level data
        }

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to fetch commit details for {commit_sha}: {e}")
        return {}
    except Exception as e:
        logging.error(f"Error in fetch_full_commit_data_local: {e}")
        return {}







def get_commit_data(commit_sha, repo_full_name, until_date, last_end_date, token, sloc, test, commit_cache, unique_contributors):
    # Initialize metrics
    total_added = total_removed = tests_added = tests_removed = 0
    test_additions = test_deletions = prod_additions = prod_deletions = 0
    src_files = doc_files = other_files = unique_files_added = unique_files_deleted = unique_files_modified = 0
    file_types = set()
    commits_on_files_touched = set()

    headers = {'Authorization': f'token {token}'}
    url = f"https://api.github.com/repos/{repo_full_name}/commits"

    # Check and process the initiating commit if not in cache
    cached_data = commit_cache.get(commit_sha)
    if cached_data:
        # Ensure the cached data has all expected keys
        if all(key in cached_data for key in ['total_added', 'total_removed', 'tests_added', 'tests_removed']):
            # Use cached data if it's complete
            total_added += cached_data['total_added']
            total_removed += cached_data['total_removed']
            tests_added += cached_data['tests_added']
            tests_removed += cached_data['tests_removed']
            src_files += cached_data['src_files']
            doc_files += cached_data['doc_files']
            other_files += cached_data['other_files']
            file_types.update(cached_data['file_types'])
            commits_on_files_touched.add(commit_sha)
        else:
            # If cached data is incomplete, remove it and proceed to re-fetch
            commit_cache.delete(commit_sha)
            cached_data = None

    if not cached_data:
        # Fetch and cache the initiating commit data
        commit_full_data = fetch_full_commit_data(commit_sha, repo_full_name, token, unique_contributors)
        if commit_full_data:
            commits_on_files_touched.add(commit_sha)
            total_added += commit_full_data['total_added']
            total_removed += commit_full_data['total_removed']
            tests_added += commit_full_data['tests_added']
            tests_removed += commit_full_data['tests_removed']
            src_files += commit_full_data['src_files']
            doc_files += commit_full_data['doc_files']
            other_files += commit_full_data['other_files']
            file_types.update(commit_full_data['file_types'])

            # Cache the initiating commit data only if it's complete
            commit_cache.put(commit_sha, commit_full_data)

    # Determine the commit date range
    if last_end_date is None:
        # First build: limit to 100 most recent commits
        params = {'until': until_date.isoformat() + 'Z', 'per_page': 100}
    else:
        # Subsequent builds: get commits from until_date back to last_end_date
        print("until build date of now  : ", until_date.isoformat() + 'Z')
        print("last build date :  ", last_end_date.isoformat() + 'Z')
        params = {
            'until': until_date.isoformat() + 'Z',
            'since': last_end_date.isoformat() + 'Z',
            'per_page': 100
        }

    counter = 0  # Initialize counter outside the loop to track total commits
    # Loop through paginated responses to fetch all commits within the date range
    while True:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            logging.error(f"Error fetching commit details for {repo_full_name}: {response.status_code}")
            break

        commits = response.json()
        if not commits:
            break

        for commit in commits:
            if counter >= 10 and last_end_date is None:
                # For the first build, limit to 10 commits
                break

            commit_sha = commit.get('sha')
            commit_date = commit.get('commit', {}).get('committer', {}).get('date')
            if not commit_date:
                continue

            # Convert commit_date to datetime for comparison
            commit_date = datetime.strptime(commit_date, '%Y-%m-%dT%H:%M:%SZ')

            # Stop fetching if we reach a commit date outside the range for non-first builds
            if last_end_date and commit_date < last_end_date:
                return compile_final_data(
                    total_added, total_removed, tests_added, tests_removed,
                    src_files, doc_files, other_files, unique_files_added,
                    unique_files_deleted, unique_files_modified, file_types,
                    commits_on_files_touched, unique_contributors, commit_cache, commit_sha
                )

            # Check cache to avoid redundant calls
            cached_data = commit_cache.get(commit_sha)
            if cached_data:
                # Ensure the cached data has all expected keys
                if all(key in cached_data for key in ['total_added', 'total_removed', 'tests_added', 'tests_removed']):
                    # Use cached data if it's complete
                    total_added += cached_data['total_added']
                    total_removed += cached_data['total_removed']
                    tests_added += cached_data['tests_added']
                    tests_removed += cached_data['tests_removed']
                    src_files += cached_data['src_files']
                    doc_files += cached_data['doc_files']
                    other_files += cached_data['other_files']
                    file_types.update(cached_data['file_types'])
                    commits_on_files_touched.add(commit_sha)
                    continue
                else:
                    # If cached data is incomplete, remove it and proceed to re-fetch
                    commit_cache.delete(commit_sha)
                    cached_data = None

            # Fetch full details for each commit to gather contributors and metrics
            counter += 1
            print("fetching current commit sha:", commit_sha, "counter is:", counter)
            
            commit_full_data = fetch_full_commit_data(commit_sha, repo_full_name, token, unique_contributors)
            if commit_full_data:
                commits_on_files_touched.add(commit_sha)
                total_added += commit_full_data['total_added']
                total_removed += commit_full_data['total_removed']
                tests_added += commit_full_data['tests_added']
                tests_removed += commit_full_data['tests_removed']
                src_files += commit_full_data['src_files']
                doc_files += commit_full_data['doc_files']
                other_files += commit_full_data['other_files']
                file_types.update(commit_full_data['file_types'])

            # Cache the fetched commit data only if it's complete
            if commit_full_data and all(key in commit_full_data for key in ['total_added', 'total_removed', 'tests_added', 'tests_removed']):
                commit_cache.put(commit_sha, commit_full_data)

        # Break out of the while loop if 100 commits have been fetched for the first build
        if counter >= 10 and last_end_date is None:
            break

        # Pagination: move to the next page
        params['page'] = params.get('page', 1) + 1

    # Compile and return the final data for commits up to `last_end_date`
    return compile_final_data(
        total_added, total_removed, tests_added, tests_removed,
        src_files, doc_files, other_files, unique_files_added,
        unique_files_deleted, unique_files_modified, file_types,
        commits_on_files_touched, unique_contributors, commit_cache, commit_sha
    )




def get_commit_data_local(commit_sha, local_repo_path, until_date, last_end_date, commit_cache, unique_contributors):
    # Initialize metrics
    total_added = total_removed = tests_added = tests_removed = 0
    src_files = doc_files = other_files = unique_files_added = unique_files_deleted = unique_files_modified = 0
    file_types = set()
    commits_on_files_touched = set()

    # Check if the commit data is cached
    cached_data = commit_cache.get(commit_sha)
    if cached_data:
        if all(key in cached_data for key in ['total_added', 'total_removed', 'tests_added', 'tests_removed']):
            # Use cached data if available and complete
            total_added += cached_data['total_added']
            total_removed += cached_data['total_removed']
            tests_added += cached_data['tests_added']
            tests_removed += cached_data['tests_removed']
            src_files += cached_data['src_files']
            doc_files += cached_data['doc_files']
            other_files += cached_data['other_files']
            file_types.update(cached_data['file_types'])
            commits_on_files_touched.add(commit_sha)
        else:
            # If incomplete, delete the cache and re-fetch
            commit_cache.delete(commit_sha)
            cached_data = None

    if not cached_data:
        # Fetch and cache the initiating commit data locally
        commit_full_data = fetch_full_commit_data_local(commit_sha, local_repo_path, unique_contributors)
        if commit_full_data:
            commits_on_files_touched.add(commit_sha)
            total_added += commit_full_data['total_added']
            total_removed += commit_full_data['total_removed']
            tests_added += commit_full_data['tests_added']
            tests_removed += commit_full_data['tests_removed']
            src_files += commit_full_data['src_files']
            doc_files += commit_full_data['doc_files']
            other_files += commit_full_data['other_files']
            file_types.update(commit_full_data['file_types'])

            # Cache the data only if complete
            commit_cache.put(commit_sha, commit_full_data)

    # Get commits within the date range
    if last_end_date is None:
        # First build: limit to 10 commits (to mimic the API behavior)
        git_log_command = [
            "git", "-C", local_repo_path, "log", f"--until={until_date.isoformat()}Z", "-n", "10", "--pretty=format:%H"
        ]
    else:
        # Subsequent builds: get commits between `until_date` and `last_end_date`
        git_log_command = [
            "git", "-C", local_repo_path, "log",
            f"--since={last_end_date.isoformat()}Z", f"--until={until_date.isoformat()}Z",
            "--pretty=format:%H"
        ]

    try:
        result = subprocess.run(git_log_command, capture_output=True, text=True, check=True)
        commit_shas = result.stdout.splitlines()

        # Iterate over each commit SHA and collect data
        for commit_sha in commit_shas:
            # Check cache to avoid redundant calls
            cached_data = commit_cache.get(commit_sha)
            if cached_data:
                if all(key in cached_data for key in ['total_added', 'total_removed', 'tests_added', 'tests_removed']):
                    total_added += cached_data['total_added']
                    total_removed += cached_data['total_removed']
                    tests_added += cached_data['tests_added']
                    tests_removed += cached_data['tests_removed']
                    src_files += cached_data['src_files']
                    doc_files += cached_data['doc_files']
                    other_files += cached_data['other_files']
                    file_types.update(cached_data['file_types'])
                    commits_on_files_touched.add(commit_sha)
                    continue
                else:
                    commit_cache.delete(commit_sha)

            # Fetch details for each commit locally
            commit_full_data = fetch_full_commit_data_local(commit_sha, local_repo_path, unique_contributors)
            if commit_full_data:
                commits_on_files_touched.add(commit_sha)
                total_added += commit_full_data['total_added']
                total_removed += commit_full_data['total_removed']
                tests_added += commit_full_data['tests_added']
                tests_removed += commit_full_data['tests_removed']
                src_files += commit_full_data['src_files']
                doc_files += commit_full_data['doc_files']
                other_files += commit_full_data['other_files']
                file_types.update(commit_full_data['file_types'])

                # Cache the data for efficiency
                commit_cache.put(commit_sha, commit_full_data)

    except subprocess.CalledProcessError as e:
        logging.error(f"Error running git log for {local_repo_path}: {e}")

    # Compile the final data
    return compile_final_data(
        total_added, total_removed, tests_added, tests_removed,
        src_files, doc_files, other_files, unique_files_added,
        unique_files_deleted, unique_files_modified, file_types,
        commits_on_files_touched, unique_contributors, commit_cache, commit_sha
    )




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
