import requests
from repo_info_collector import get_workflow_ids
from datetime import datetime, timezone, timedelta
import time
import math
import logging



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


def get_jobs_for_run(repo_full_name, run_id, token):
    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/jobs"
    headers = {'Authorization': f'token {token}'}
    jobs_response = requests.get(url, headers=headers).json()
    jobs_ids = []
    if jobs_response and 'jobs' in jobs_response:
        for job in jobs_response['jobs']:
            jobs_ids.append(job['id'])
    return jobs_ids, len(jobs_ids)  # Return both job IDs and the count of jobs





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