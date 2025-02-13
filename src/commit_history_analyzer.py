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



import subprocess
import logging
import os

import subprocess
import logging
import os

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

def fetch_full_commit_data_local(commit_sha, local_repo_path, unique_contributors):
    """Fetch detailed commit data using local Git instead of GitHub API, including accurate files added, deleted, and modified."""
    try:
        if not os.path.exists(local_repo_path):
            logging.error(f"Repository path does not exist: {local_repo_path}")
            return {}

        # Get commit details (author name and changed files)
        result = subprocess.run(
            ["git", "-C", local_repo_path, "show", "--numstat", "--pretty=format:%an", commit_sha],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
        )

        output = result.stdout.strip().split("\n")
        if not output:
            logging.error(f"Commit {commit_sha} has no valid output from git show")
            return {}

        # Extract commit author
        author_name = output[0].strip() if output else "Unknown"
        unique_contributors.add(author_name)

        # Initialize commit metadata
        total_added = total_removed = tests_added = tests_removed = 0
        src_files = doc_files = other_files = 0
        file_types = set()
        file_changes = []

        unique_files_added = set()
        unique_files_deleted = set()
        unique_files_modified = set()

        # Process file changes
        for line in output[1:]:  # Skip author line
            parts = line.split("\t")
            if len(parts) != 3:
                continue  # Skip malformed lines

            added_lines, removed_lines, filename = parts
            added_lines = int(added_lines) if added_lines.isdigit() else 0
            removed_lines = int(removed_lines) if removed_lines.isdigit() else 0

            # Track total added/removed lines
            total_added += added_lines
            total_removed += removed_lines

            # Get previous commit SHA (parent of current commit)
            parent_commit = subprocess.run(
                ["git", "-C", local_repo_path, "rev-parse", f"{commit_sha}^"],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            ).stdout.strip()

            # Get file line count at the parent commit (before the change)
            prev_line_count = get_file_line_count(parent_commit, filename, local_repo_path)

            # Get file line count at the current commit (after the change)
            current_line_count = get_file_line_count(commit_sha, filename, local_repo_path)

            # **Fix for Deleted Files**:
            # If the file was removed, try to get its last known commit
            if prev_line_count is None and removed_lines > 0:
                last_known_commit = get_last_commit_containing_file(filename, commit_sha, local_repo_path)
                prev_line_count = get_file_line_count(last_known_commit, filename, local_repo_path)

            # Determine file status more accurately
            if prev_line_count is None and current_line_count is not None:
                unique_files_added.add(filename)  # File was newly created
            elif prev_line_count is not None and current_line_count is None:
                unique_files_deleted.add(filename)  # File was entirely removed
            else:
                unique_files_modified.add(filename)  # File was modified

            # Classify files
            if is_test_file(filename):
                tests_added += added_lines
                tests_removed += removed_lines
            elif is_production_file(filename):
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
            'file_changes': file_changes,  # Store file-level data
            'gh_files_added': len(unique_files_added),
            'gh_files_deleted': len(unique_files_deleted),
            'gh_files_modified': len(unique_files_modified),
        }

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to fetch commit details for {commit_sha}: {e}")
        return {}
    except Exception as e:
        logging.error(f"Error in fetch_full_commit_data_local: {e}")
        return {}







def get_commit_data_local(commit_sha, local_repo_path, until_date, last_end_date, commit_cache, unique_contributors):
    """
    Aggregates commit-related information, including accurate number of unique files added, deleted, and modified
    between two workflow runs.
    """
    # Initialize aggregated metrics
    total_added = total_removed = tests_added = tests_removed = 0
    src_files = doc_files = other_files = 0
    file_types = set()
    commits_on_files_touched = set()

    unique_files_added = 0
    unique_files_deleted = 0
    unique_files_modified = 0

    # **Extract commits in the range**
    if last_end_date is None:
        # First build: limit to 10 commits (to mimic API behavior)
        git_log_command = [
            "git", "-C", local_repo_path, "log", f"--until={until_date.isoformat()}Z",
            "-n", "10", "--pretty=format:%H"
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

        # **Iterate over each commit to track file changes**
        for commit_sha in commit_shas:
            # Check cache to avoid redundant calls
            cached_data = commit_cache.get(commit_sha)
            if cached_data:
                total_added += cached_data['total_added']
                total_removed += cached_data['total_removed']
                tests_added += cached_data['tests_added']
                tests_removed += cached_data['tests_removed']
                src_files += cached_data['src_files']
                doc_files += cached_data['doc_files']
                other_files += cached_data['other_files']
                file_types.update(cached_data['file_types'])
                commits_on_files_touched.add(commit_sha)

                unique_files_added += commit_full_data['gh_files_added']
                unique_files_deleted += commit_full_data['gh_files_deleted']
                unique_files_modified += commit_full_data['gh_files_modified']

                continue  # Skip redundant processing

            # **Get detailed file changes for this commit**
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

                # Aggregate unique file changes
                unique_files_added += commit_full_data['gh_files_added']
                unique_files_deleted += commit_full_data['gh_files_deleted']
                unique_files_modified += commit_full_data['gh_files_modified']

                # Cache the commit data for efficiency
                commit_cache.put(commit_sha, commit_full_data)

    except subprocess.CalledProcessError as e:
        logging.error(f"Error running git log for {local_repo_path}: {e}")

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
        'gh_commits_on_files_touched': len(commits_on_files_touched),
        'gh_test_lines_per_kloc': (tests_added + tests_removed) / max((total_added + total_removed) / 1000, 1),
        'file_types': list(file_types)
    }
