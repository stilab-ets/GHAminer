import requests
import logging
from datetime import datetime, timezone, timedelta
import os



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
            if counter >= 100 and last_end_date is None:
                # For the first build, limit to 100 commits
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
        if counter >= 100 and last_end_date is None:
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
