import requests
from datetime import datetime, timezone, timedelta
import csv
import os
import time
import math
import logging
import base64
import re
import numpy as np

def get_request(url, token):
    headers = {'Authorization': f'token {token}'}
    attempt = 0
    max_attempts = 5  # Number of attempts before applying infinite retry on connection errors

    while True:
        try:
            response = requests.get(url, headers=headers, timeout=10)  # Set a timeout to avoid hanging requests
            
            # Check rate limit headers proactively
            remaining_requests = int(response.headers.get('X-RateLimit-Remaining', 1))  # Default to 1 if missing
            reset_time = response.headers.get('X-RateLimit-Reset')

            if remaining_requests == 0 and reset_time:
                sleep_time = max(0, (datetime.fromtimestamp(int(reset_time), timezone.utc) - datetime.now(timezone.utc)).total_seconds() + 10)
                logging.warning(f"Rate limit hit! Sleeping for {sleep_time} seconds.")
                time.sleep(sleep_time)
                continue  # Retry after sleeping

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403 and reset_time:
                sleep_time = max(0, (datetime.fromtimestamp(int(reset_time), timezone.utc) - datetime.now(timezone.utc)).total_seconds() + 10)
                logging.error(f"Rate limit exceeded, sleeping for {sleep_time} seconds. URL: {url}")
                time.sleep(sleep_time)
                continue  # Retry after sleeping
            elif response.status_code in [500, 502, 503, 504]:
                # Retry on server errors
                wait_time = min(2 ** attempt, 60)  # Exponential backoff up to 60 seconds
                logging.warning(f"GitHub server error {response.status_code}. Retrying in {wait_time} seconds.")
                time.sleep(wait_time)
                attempt += 1
            else:
                return None  # Return None for non-retryable failures

        except requests.exceptions.ConnectionError:
            wait_time = min(2 ** attempt, 60)  # Exponential backoff up to 60 seconds
            logging.error(f"Network error: Connection lost. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            attempt += 1

        except requests.exceptions.Timeout:
            wait_time = min(2 ** attempt, 60)  # Exponential backoff up to 60 seconds
            logging.error(f"Request timed out. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            attempt += 1

        except requests.exceptions.RequestException as e:
            logging.error(f"Unexpected error fetching {url}: {e}")
            return None  # Return None on unknown request errors

        # If exceeded max_attempts, switch to infinite retry for connection issues
        if attempt >= max_attempts:
            logging.error("Max attempts reached. Entering infinite retry mode for connection errors.")
            attempt = max_attempts - 1  # Prevent integer overflow
