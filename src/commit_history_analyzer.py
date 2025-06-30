import requests
import logging
from datetime import datetime, timezone, timedelta
import os
from file_indicators import is_production_file , is_test_file
import subprocess
import json
import shutil
import platform
import stat

def ensure_executable(path):
    if platform.system() != "Windows":
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)


def get_scc_path():
    system = platform.system()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(system)

    if system == "Windows":
        return os.path.join(script_dir, "scc.exe")
    elif system == "Darwin":
        return os.path.join(script_dir, "scc_mac")
    elif system == "Linux":
        return os.path.join(script_dir, "scc_linux")
    else:
        raise RuntimeError(f"Unsupported platform: {system}")



def clone_repo_locally(repo_url, base_path):
    """Clone the repository inside a tmp/ directory in the project folder."""
    tmp_dir = os.path.join(base_path, "tmp")  # Ensure tmp directory inside project
    os.makedirs(tmp_dir, exist_ok=True)  # Create tmp/ if it doesn't exist

    repo_name = repo_url.split("/")[-1].replace(".git", "")  # Ensure clean repo name
    local_repo_path = os.path.join(tmp_dir, repo_name)  # Unique folder for each repo
    git_path = shutil.which("git") or r"C:\Program Files\Git\cmd\git.exe"  # Find git

    print(f"Cloning repo into: {local_repo_path}")

    if not os.path.exists(local_repo_path):
        result = subprocess.run([git_path, "clone", repo_url, local_repo_path], capture_output=True, text=True)

        if result.returncode != 0:
            logging.error(f"Error cloning repo: {result.stderr}")
            return None  # Return None if cloning fails
        else:
            print(f"Successfully cloned repo into {local_repo_path}")
    else:
        print(f"Repository already exists at {local_repo_path}, ensuring all commits are available.")

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



def calculate_sloc_and_test_lines(local_repo_path, commit_sha=None, timestamp=None):
    """
    Calculates SLOC and test lines for the repository at a specific commit or timestamp.

    Args:
        local_repo_path (str): Path to the local repository.
        commit_sha (str): Specific commit to checkout. If None, use the latest state.
        timestamp (str): If commit_sha is None, use the latest state at this timestamp.

    Returns:
        tuple: (SLOC, Test lines)
    """
    import json
    from datetime import datetime

    SCC_PATH = get_scc_path()
    ensure_executable(SCC_PATH)
    
    # Ensure repository path exists
    if not os.path.exists(local_repo_path):
        logging.error(f"Repository path not found: {local_repo_path}")
        return None, None

    # Flag to track if checkout was successful
    checkout_successful = False

    # Attempt to checkout the specific commit if provided
    if commit_sha:
        try:
            print(f"Attempting to checkout to commit: {commit_sha}")
            subprocess.run(["git", "-C", local_repo_path, "checkout", commit_sha],
                           check=True, capture_output=True, text=True)
            checkout_successful = True
            print(f"Checked out to commit: {commit_sha}")

        except subprocess.CalledProcessError as e:
            logging.warning(f"Failed to checkout to commit {commit_sha}: {e}")

    # If checkout failed or commit not provided, use timestamp to find the commit
    if not checkout_successful and timestamp:
        try:
            print(f"Finding commit at timestamp: {timestamp}")
            git_timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
            result = subprocess.run(
                ["git", "-C", local_repo_path, "rev-list", "-1", "--before", git_timestamp, "HEAD"],
                capture_output=True, text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                commit_sha = result.stdout.strip()
                print(f"Found commit at timestamp: {commit_sha}")

                # Try to checkout to the found commit
                try:
                    subprocess.run(["git", "-C", local_repo_path, "checkout", commit_sha],
                                   check=True, capture_output=True, text=True)
                    checkout_successful = True
                    print(f"Checked out to commit at timestamp: {commit_sha}")

                except subprocess.CalledProcessError as e:
                    logging.warning(f"Failed to checkout to commit at timestamp {timestamp}: {e}")

        except Exception as e:
            logging.error(f"Error finding commit by timestamp: {e}")

    # If both commit and timestamp failed, log a warning
    if not checkout_successful:
        print(f"Proceeding with the latest state of the repo at {local_repo_path}.")

    # Calculate SLOC and test lines using scc
    try:
        print(f"Running scc on: {local_repo_path}")
        result = subprocess.run(
            [SCC_PATH, "--no-cocomo", "--format", "json", local_repo_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )

        if result.returncode != 0:
            logging.error(f"scc execution failed: {result.stderr}")
            return None, None

        # Parse the JSON output
        loc_data = json.loads(result.stdout)
        sloc = sum(entry["Code"] for entry in loc_data)

        # Identify potential test files
        print("Identifying potential test files...")
        result = subprocess.run(
            ["git", "-C", local_repo_path, "ls-files"],
            capture_output=True, text=True
        )

        test_lines = 0

        if result.returncode == 0:
            files_in_repo = result.stdout.strip().split("\n")
            
            for file_path in files_in_repo:
                # Identify test files based on name
                if "test" in file_path.lower() or "spec" in file_path.lower():
                    full_path = os.path.join(local_repo_path, file_path)
                    
                    # Check if file exists before counting lines
                    if os.path.exists(full_path):
                        try:
                            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                                lines = f.readlines()
                                test_lines += len(lines)
                            print(f"Test file: {file_path} - {len(lines)} lines")
                        except Exception as e:
                            logging.warning(f"Error reading file {file_path}: {e}")

        print(f"SLOC: {sloc}, Test Lines: {test_lines}")
        return sloc, test_lines

    except Exception as e:
        logging.error(f"Error running scc: {e}")
        return None, None

    finally:
        # Checkout back to the main branch to avoid repo lock issues
        try:
            subprocess.run(["git", "-C", local_repo_path, "checkout", "main"], check=True,
                           capture_output=True, text=True)
        except subprocess.CalledProcessError:
            pass




def get_file_line_count(commit_sha, file_path, local_repo_path):
    """
    Get the total number of lines in a file at a specific commit SHA.
    Returns the line count or None if the file doesn't exist at that commit.
    """
    try:
        result = subprocess.run(
            ["git", "-C", local_repo_path, "show", f"{commit_sha}:{file_path}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
        )
        return len(result.stdout.splitlines())  # Count total lines in the file
    except subprocess.CalledProcessError:
        return None  # File does not exist at this commit

def get_last_commit_containing_file(file_path, commit_sha, local_repo_path):
    """
    Find the last commit before `commit_sha` where `file_path` existed.
    """
    try:
        result = subprocess.run(
            ["git", "-C", local_repo_path, "log", "--format=%H", "--", file_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
        )
        commits = result.stdout.strip().split("\n")
        return commits[1] if len(commits) > 1 else None  # Get the last known commit before deletion
    except subprocess.CalledProcessError:
        return None  # File has no prior history

def fetch_full_commit_data_local(commit_sha, local_repo_path):
    """Fetch detailed commit data using local Git, ensuring the commit exists before retrieving details."""
    try:
        if not os.path.exists(local_repo_path):
            logging.error(f"Repository path does not exist: {local_repo_path}")
            return {}

        # **Ensure the commit exists locally by fetching it explicitly**
        fetch_result = subprocess.run(
            ["git", "-C", local_repo_path, "fetch", "origin", commit_sha],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if fetch_result.returncode != 0:
            logging.warning(f"Failed to fetch commit {commit_sha}: {fetch_result.stderr.strip()}")

        # **Try to show commit details**
        result = subprocess.run(
            ["git", "-C", local_repo_path, "show", "--numstat", "--pretty=format:%an", commit_sha],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )

        if result.returncode != 0:
            logging.error(f"Failed to fetch commit details for {commit_sha}: {result.stderr.strip()}")
            return {}

        output = result.stdout.strip().split("\n")
        if not output:
            logging.error(f"Commit {commit_sha} has no valid output from git show")
            return {}

        # **Extract commit author**
        author_name = output[0].strip() if output else "Unknown"
        # **Initialize commit metadata**
        total_added = total_removed = tests_added = tests_removed = 0
        src_files = doc_files = other_files = 0
        file_types = set()
        file_changes = []
        dockerfile_changed = 0
        docker_compose_changed = 0


        unique_files_added = set()
        unique_files_deleted = set()
        unique_files_modified = set()

        # **Process file changes**
        for line in output[1:]:  # Skip author line
            parts = line.split("\t")
            if len(parts) != 3:
                continue  # Skip malformed lines

            added_lines, removed_lines, filename = parts
            added_lines = int(added_lines) if added_lines.isdigit() else 0
            removed_lines = int(removed_lines) if removed_lines.isdigit() else 0

            # **Track total added/removed lines**
            total_added += added_lines
            total_removed += removed_lines

            # **Get previous commit SHA (parent of current commit)**
            parent_commit_result = subprocess.run(
                ["git", "-C", local_repo_path, "rev-parse", f"{commit_sha}^"],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            parent_commit = parent_commit_result.stdout.strip() if parent_commit_result.returncode == 0 else None

            # **Determine file status more accurately**
            prev_line_count = get_file_line_count(parent_commit, filename, local_repo_path) if parent_commit else None
            current_line_count = get_file_line_count(commit_sha, filename, local_repo_path)

            if prev_line_count is None and removed_lines > 0:
                last_known_commit = get_last_commit_containing_file(filename, commit_sha, local_repo_path)
                prev_line_count = get_file_line_count(last_known_commit, filename, local_repo_path)

            if prev_line_count is None and current_line_count is not None:
                unique_files_added.add(filename)
            elif prev_line_count is not None and current_line_count is None:
                unique_files_deleted.add(filename)
            else:
                unique_files_modified.add(filename)

            # **Classify files**
            if is_test_file(filename):
                tests_added += added_lines
                tests_removed += removed_lines
            elif is_production_file(filename):
                src_files += 1
            elif is_documentation_file(filename):
                doc_files += 1
            else:
                other_files += 1

            # Count Docker-related files
            if "dockerfile" in filename.lower():
                dockerfile_changed += 1
            elif "docker-compose" in filename.lower():
                docker_compose_changed += 1


            # **Track file extensions**
            file_extension = os.path.splitext(filename)[1]
            if file_extension:
                file_types.add(file_extension)

            # **Store file change data**
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
            'file_changes': file_changes,
            'gh_files_added': len(unique_files_added),
            'gh_files_deleted': len(unique_files_deleted),
            'gh_files_modified': len(unique_files_modified),
            'dockerfile_changed': dockerfile_changed,
            'docker_compose_changed': docker_compose_changed,
        }

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to fetch commit details for {commit_sha}: {e}")
        return {}
    except Exception as e:
        logging.error(f"Error in fetch_full_commit_data_local: {e}")
        return {}



from datetime import datetime, timedelta

def count_commits_on_files_last_3_months(local_repo_path, commit_sha):
    """
    Counts the number of unique commits on each file in the given commit within the last 3 months.

    Args:
        local_repo_path (str): Path to the local repository.
        commit_sha (str): Commit SHA to analyze.

    Returns:
        int: Total number of unique commits on the files in the given commit within the last 3 months.
    """
    # Get the list of files in the given commit
    try:
        result = subprocess.run(
            ["git", "-C", local_repo_path, "show", "--name-only", "--pretty=format:", commit_sha],
            capture_output=True, text=True, check=True
        )
        files_in_commit = result.stdout.strip().splitlines()

    except subprocess.CalledProcessError as e:
        logging.error(f"Error fetching files for commit {commit_sha}: {e}")
        return 0

    if not files_in_commit:
        logging.warning(f"No files found for commit {commit_sha}")
        return 0

    # Determine the time range (last 3 months)
    try:
        # Get the commit date
        result = subprocess.run(
            ["git", "-C", local_repo_path, "show", "-s", "--format=%ci", commit_sha],
            capture_output=True, text=True, check=True
        )
        commit_date_str = result.stdout.strip()
        commit_date = datetime.strptime(commit_date_str, "%Y-%m-%d %H:%M:%S %z")
        three_months_ago = commit_date - timedelta(days=90)

    except subprocess.CalledProcessError as e:
        logging.error(f"Error fetching commit date for {commit_sha}: {e}")
        return 0

    # Track unique commits per file
    unique_commits = set()

    # For each file, get the commits within the last 3 months
    for file_path in files_in_commit:
        try:
            result = subprocess.run(
                [
                    "git", "-C", local_repo_path, "log", "--since", three_months_ago.isoformat(), 
                    "--pretty=format:%H", "--", file_path
                ],
                capture_output=True, text=True, check=True
            )
            commits = set(result.stdout.strip().splitlines())
            unique_commits.update(commits)

        except subprocess.CalledProcessError as e:
            logging.warning(f"Error fetching commits for file {file_path}: {e}")

    return len(unique_commits)



def get_unique_committers(local_repo_path, run_date):
    """
    Retrieves the list of unique committers to the repository since the start of the project until the run date.

    Args:
        local_repo_path (str): Path to the local repository.
        run_date (datetime): Date of the run.

    Returns:
        set: Set of unique committers (names and emails).
    """
    unique_committers = set()

    try:
        print(f"Fetching committers using run date: {run_date}")

        # Fetch committers from the start of the project until the run date
        result = subprocess.run(
            [
                "git", "-C", local_repo_path, "log",
                "--until", run_date.isoformat(),
                "--format=%an <%ae>"
            ],
            capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )

        if result.stdout:
            committers = result.stdout.strip().splitlines()
            unique_committers.update(committers)

    except subprocess.CalledProcessError as e:
        logging.error(f"Error fetching committers by run date: {e}")
    except Exception as e:
        logging.error(f"Unexpected error fetching committers: {e}")

    return unique_committers



from datetime import timedelta

def get_unique_committers_3_months(local_repo_path, run_date):
    """
    Retrieves the number of unique committers to the repository within the last 3 months 
    from the given run date.

    Args:
        local_repo_path (str): Path to the local repository.
        run_date (datetime): Date of the run.

    Returns:
        set: Set of unique committers (names and emails).
    """
    unique_committers = set()

    # Calculate the 3-month window
    start_date = run_date - timedelta(days=90)

    try:
        print(f"Fetching committers from {start_date} to {run_date}")

        # Fetch committers within the 3-month window
        result = subprocess.run(
            [
                "git", "-C", local_repo_path, "log",
                f"--since={start_date.isoformat()}",
                f"--until={run_date.isoformat()}",
                "--format=%an <%ae>"
            ],
            capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )

        if result.stdout:
            committers = result.stdout.strip().splitlines()
            unique_committers.update(committers)

    except subprocess.CalledProcessError as e:
        logging.error(f"Error fetching committers for 3-month window: {e}")
    except Exception as e:
        logging.error(f"Unexpected error fetching committers for 3-month window: {e}")

    return unique_committers



def get_commit_count_until_date(local_repo_path, run_date):
    """
    Calculates the number of commits in the repository up until the specified run date.

    Args:
        local_repo_path (str): Path to the local repository.
        run_date (datetime): Date of the run.

    Returns:
        int: Total number of commits up until the run date.
    """
    commit_count = 0

    try:
        print(f"Calculating commit count until {run_date.isoformat()}")

        # Fetch commit count until the run date
        result = subprocess.run(
            [
                "git", "-C", local_repo_path, "rev-list",
                "--count", "--before", run_date.isoformat(), "HEAD"
            ],
            capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )

        if result.stdout.strip():
            commit_count = int(result.stdout.strip())

    except subprocess.CalledProcessError as e:
        logging.error(f"Error fetching commit count until {run_date}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error fetching commit count: {e}")

    return commit_count



# gets commits details from a last end date till and untill date
def get_commit_data_local(commit_sha, local_repo_path, run_date, run_plus_1_date):
    """
    Aggregates commit-related information, ensuring the run's commit_sha is always included,
    along with commits between the last run's end date and this run's creation date.
    """
    # Initialize aggregated metrics
    total_added = total_removed = tests_added = tests_removed = 0
    src_files = doc_files = other_files = 0
    file_types = set()
    #commits_on_files_touched = set()

    unique_files_added = 0
    unique_files_deleted = 0
    unique_files_modified = 0
    dockerfile_changed = 0
    docker_compose_changed = 0

    # **Ensure commit_sha is always included**
    commit_shas = [commit_sha]  # Start with the head commit of the run

    # Determine the git log command based on the presence of run_plus_1_date
    if run_plus_1_date is None:
        # No previous run, only analyze the specific `commit_sha`
        git_log_command = [
            "git", "-C", local_repo_path, "show", "--pretty=format:%H", "--no-patch", commit_sha
        ]
    else:
        # Subsequent builds: get commits between `until_date` and `last_end_date`
        git_log_command = [
            "git", "-C", local_repo_path, "log",
            f"--since={run_plus_1_date.isoformat()}Z", f"--until={run_date.isoformat()}Z",
            "--pretty=format:%H"
        ]

    try:
        result = subprocess.run(git_log_command, capture_output=True, text=True, check=True)
        additional_commits = result.stdout.splitlines()

        # **Ensure commit_sha is at the beginning of the list**
        for sha in additional_commits:
            if sha not in commit_shas:
                commit_shas.append(sha)

    except subprocess.CalledProcessError as e:
        logging.error(f"Error running git log for {local_repo_path}: {e}")

    # **Process each commit, ensuring commit_sha is processed first**
    for sha in commit_shas:

        # **Get detailed file changes for this commit**
        commit_full_data = fetch_full_commit_data_local(sha, local_repo_path)
        if commit_full_data:
            #commits_on_files_touched.add(sha)
            total_added += commit_full_data['total_added']
            total_removed += commit_full_data['total_removed']
            tests_added += commit_full_data['tests_added']
            tests_removed += commit_full_data['tests_removed']
            src_files += commit_full_data['src_files']
            doc_files += commit_full_data['doc_files']
            other_files += commit_full_data['other_files']
            file_types.update(commit_full_data['file_types'])

            # Aggregate unique file changes
            unique_files_added += commit_full_data['gh_files_added']
            unique_files_deleted += commit_full_data['gh_files_deleted']
            unique_files_modified += commit_full_data['gh_files_modified']

            dockerfile_changed += commit_full_data['dockerfile_changed']
            docker_compose_changed += commit_full_data['docker_compose_changed']

    commits_on_files_touched_count = count_commits_on_files_last_3_months(local_repo_path, commit_sha)
    committers_3_months = get_unique_committers_3_months(local_repo_path, run_date)
    unique_committers = get_unique_committers(local_repo_path, run_date=run_date)
    commit_count = get_commit_count_until_date(local_repo_path, run_date)

    # **Return aggregated commit data**
    return {
        'gh_files_added': unique_files_added,
        'gh_files_deleted': unique_files_deleted,
        'gh_files_modified': unique_files_modified,
        'gh_lines_added': total_added,
        'gh_lines_deleted': total_removed,
        'gh_tests_added': tests_added,
        'gh_tests_deleted': tests_removed,
        'gh_test_churn': tests_added + tests_removed,
        'gh_src_churn': total_added + total_removed,
        'gh_src_files': src_files,
        'gh_doc_files': doc_files,
        'gh_other_files': other_files,
        'gh_commits_on_files_touched': commits_on_files_touched_count,
        'file_types': list(file_types),
        'dockerfile_changed': dockerfile_changed,
        'docker_compose_changed': docker_compose_changed,
        'unique_committers' : len(unique_committers),
        "committers_3_months" : len(committers_3_months),
        "git_commits" : commit_count
    }
