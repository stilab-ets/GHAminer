import csv
import logging


import csv
import pandas as pd
import os
import logging

def save_builds_to_file(builds_info, output_csv):
    """Save only new builds information to a CSV file without duplicates."""
    if not builds_info:
        return  # Skip if no new builds

    fieldnames = [
        'repo', 'id_build', 'branch', 'commit_sha', 'languages', 'status', 'conclusion', 'workflow_event_trigger', 'issuer_name', 'workflow_id', 'created_at',
        'updated_at', 'build_duration', 'total_builds', 'gh_files_added', 'gh_files_deleted', 'gh_files_modified',
        'tests_ran', 'gh_lines_added', 'gh_lines_deleted', 'file_types', 'gh_tests_added',
        'gh_tests_deleted', 'gh_test_churn', 'gh_src_churn', 'gh_pull_req_number', 'gh_is_pr', 'gh_sloc',
        'gh_description_complexity', 'gh_src_files', 'gh_doc_files', 'gh_other_files', 'git_num_committers',
        'gh_job_id', 'total_jobs', 'gh_first_commit_created_at', 'gh_team_size_last_3_month',
        'gh_commits_on_files_touched', 'gh_num_pr_comments', 'git_merged_with', 'gh_test_lines_per_kloc',
        'build_language', 'dependencies_count', 'workflow_size', 'test_framework', 'tests_passed', 
        'tests_failed', 'tests_skipped', 'tests_total', 'workflow_name', 'dockerfile_changed' , 'docker_compose_changed' , 'fetch_duration' 
    ]

    # **Load existing IDs from CSV to prevent duplicates**
    existing_build_ids = set()
    if os.path.exists(output_csv):
        try:
            existing_df = pd.read_csv(output_csv, usecols=['id_build'])
            existing_build_ids = set(existing_df['id_build'].astype(str))
        except Exception as e:
            logging.error(f"Error reading existing build IDs from {output_csv}: {e}")

    # **Filter out duplicate entries before writing**
    new_builds = [build for build in builds_info if str(build['id_build']) not in existing_build_ids]

    if new_builds:
        with open(output_csv, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if os.stat(output_csv).st_size == 0:
                writer.writeheader()  # Write header if file is empty
            writer.writerows(new_builds)
        logging.info(f"✅ {len(new_builds)} new build(s) added to {output_csv}.")
    else:
        logging.info(f"⚠️ No new builds to add, skipping file write.")



import os

def save_head(output_csv):
    """Save builds information to a CSV file, avoiding duplicate headers."""
    fieldnames = [
        'repo', 'id_build', 'branch', 'commit_sha', 'languages', 'status', 'conclusion', 'workflow_event_trigger', 'issuer_name', 'workflow_id', 'created_at',
        'updated_at', 'build_duration', 'total_builds', 'gh_files_added', 'gh_files_deleted', 'gh_files_modified',
        'tests_ran', 'gh_lines_added', 'gh_lines_deleted', 'file_types', 'gh_tests_added',
        'gh_tests_deleted', 'gh_test_churn', 'gh_src_churn', 'gh_pull_req_number', 'gh_is_pr', 'gh_sloc',
        'gh_description_complexity', 'gh_src_files', 'gh_doc_files', 'gh_other_files', 'git_num_committers',
        'gh_job_id', 'total_jobs', 'gh_first_commit_created_at', 'gh_team_size_last_3_month',
        'gh_commits_on_files_touched', 'gh_num_pr_comments', 'git_merged_with', 'gh_test_lines_per_kloc',
        'build_language', 'dependencies_count', 'workflow_size', 'test_framework', 'tests_passed', 'tests_failed',
        'tests_skipped', 'tests_total', 'workflow_name' , 'dockerfile_changed' , 'docker_compose_changed' ,'fetch_duration'  # New field for fetch duration
    ]

    # Check if the file exists and already contains data
    if os.path.exists(output_csv) and os.path.getsize(output_csv) > 0:
        with open(output_csv, mode='r', encoding='utf-8') as file:
            first_line = file.readline()
            if first_line.strip() == ','.join(fieldnames):
                logging.info(f"Header already exists in {output_csv}. Skipping header write.")
                return  # Header already exists, skip writing it

    # Write the header if the file is empty or does not exist
    with open(output_csv, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
    logging.info(f"CSV header with fetch duration saved to {output_csv}")
