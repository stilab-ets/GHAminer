import csv
import logging


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
        'build_language', 'test_framework', 'tests_passed', 'tests_failed', 'tests_skipped', 'tests_total',
        'fetch_duration'  # New field for fetch duration
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
        'build_language', 'test_framework', 'tests_passed', 'tests_failed', 'tests_skipped', 'tests_total',
        'fetch_duration'  # New field for fetch duration
    ]
    with open(output_csv, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
    logging.info(f"CSV header with fetch duration saved to {output_csv}")