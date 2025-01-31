import requests
from datetime import datetime, timezone, timedelta
import csv
import os
import time
import math
import logging
import base64
import re


def get_request(url, token):
    headers = {'Authorization': f'token {token}'}
    attempt = 0

    while attempt < 5:
        response = requests.get(url, headers=headers)
        
        # Check rate limit headers proactively
        remaining_requests = int(response.headers.get('X-RateLimit-Remaining', 1))  # Default to 1 if missing
        reset_time = response.headers.get('X-RateLimit-Reset')

        if remaining_requests == 0 and reset_time:
            sleep_time = (datetime.fromtimestamp(int(reset_time), timezone.utc) - datetime.now(timezone.utc)).total_seconds() + 10
            logging.warning(f"Rate limit hit! Sleeping for {sleep_time} seconds.")
            time.sleep(sleep_time)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403 and reset_time:
            sleep_time = (datetime.fromtimestamp(int(reset_time), timezone.utc) - datetime.now(timezone.utc)).total_seconds() + 10
            logging.error(f"Rate limit exceeded, sleeping for {sleep_time} seconds. URL: {url}")
            time.sleep(sleep_time)
        else:
            logging.error(
                f"Failed to fetch data, status code: {response.status_code}, URL: {url}, Response: {response.text}")
            #time.sleep(math.pow(2, attempt) * 10)  # Exponential backoff
        
        attempt += 1

    return None  # Return None if all attempts fail