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


def get_jobs_for_run_old(repo_full_name, run_id, token):
    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/jobs"
    headers = {'Authorization': f'token {token}'}
    jobs_response = requests.get(url, headers=headers).json()
    jobs_ids = []
    if jobs_response and 'jobs' in jobs_response:
        for job in jobs_response['jobs']:
            jobs_ids.append(job['id'])
    return jobs_ids, len(jobs_ids)  # Return both job IDs and the count of jobs



def get_jobs_for_run_old_2(repo_full_name, run_id, token):
    """
    Fetch job details for a specific run. Handles retries and rate limits.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/jobs"
    jobs_response = get_request(url, token)

    jobs_ids = []
    #print("jobs response : " , jobs_response)
    # Ensure the response is a valid dictionary with the 'jobs' key
    if jobs_response and isinstance(jobs_response, dict):
        if 'jobs' in jobs_response:
            for job in jobs_response['jobs']:
                jobs_ids.append(job['id'])
        else:
            logging.warning(f"Expected 'jobs' key in response for run {run_id}, but not found. Response: {jobs_response}")
    else:
        logging.error(f"Invalid or empty response for jobs endpoint. URL: {url}, Response: {jobs_response}")

    return jobs_ids, len(jobs_ids)  # Return job IDs and count



def get_jobs_for_run(repo_full_name, run_id, token):
    """
    Fetch job details for a specific run. Handles retries and rate limits.
    Returns a list of job IDs, job details with steps info, and the count of jobs.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{run_id}/jobs"
    jobs_response = get_request(url, token)

    jobs_ids = []
    job_details = []

    if jobs_response and isinstance(jobs_response, dict):
        if 'jobs' in jobs_response:
            for job in jobs_response['jobs']:
                job_id = job['id']
                job_name = job.get('name', 'Unknown')
                start_time = job.get('started_at')
                end_time = job.get('completed_at')
                result = job.get('conclusion', 'unknown')

                # Calculate job duration
                job_duration = "N/A"
                if start_time and end_time:
                    try:
                        start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
                        end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%SZ")
                        job_duration = (end_dt - start_dt).total_seconds()
                    except Exception as e:
                        logging.error(f"Error calculating duration for job {job_id}: {e}")

                # Collect step details
                steps = []
                if 'steps' in job:
                    for step in job['steps']:
                        step_name = step.get('name', 'Unknown')
                        step_conclusion = step.get('conclusion', 'unknown')
                        step_start = step.get('started_at')
                        step_end = step.get('completed_at')

                        # Calculate step duration
                        step_duration = "N/A"
                        if step_start and step_end:
                            try:
                                step_start_dt = datetime.strptime(step_start, "%Y-%m-%dT%H:%M:%SZ")
                                step_end_dt = datetime.strptime(step_end, "%Y-%m-%dT%H:%M:%SZ")
                                step_duration = (step_end_dt - step_start_dt).total_seconds()
                            except Exception as e:
                                logging.error(f"Error calculating duration for step {step_name} in job {job_id}: {e}")

                        steps.append({
                            "step_name": step_name,
                            "step_conclusion": step_conclusion,
                            "step_start": step_start,
                            "step_end": step_end,
                            "step_duration": step_duration
                        })

                # Append job details
                jobs_ids.append(job_id)
                job_details.append({
                    "job_name": job_name,
                    "job_start": start_time,
                    "job_end": end_time,
                    "job_duration": job_duration,
                    "job_result": result,
                    "steps": steps
                })

        else:
            logging.warning(f"Expected 'jobs' key in response for run {run_id}, but not found. Response: {jobs_response}")
    else:
        logging.error(f"Invalid or empty response for jobs endpoint. URL: {url}, Response: {jobs_response}")

    return jobs_ids, job_details, len(jobs_ids)




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