import os
import json
import datetime
import time
import argparse
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the client
client = Garmin(os.getenv('GARMIN_EMAIL'), os.getenv('GARMIN_PASSWORD'))

# Login to Garmin Connect
client.login()

# Base directory for storing data
data_dir = 'garmin_data'
os.makedirs(data_dir, exist_ok=True)

# Rate limiting parameters
MAX_REQUESTS_PER_MINUTE = 30
request_times = []

def rate_limit():
    now = time.time()
    request_times.append(now)
    if len(request_times) > MAX_REQUESTS_PER_MINUTE:
        oldest = request_times.pop(0)
        if now - oldest < 60:
            sleep_time = 60 - (now - oldest)
            print(f"[SCRIPT RATE LIMIT] Maximum requests per minute ({MAX_REQUESTS_PER_MINUTE}) reached. Pausing for {sleep_time:.2f} seconds.")
            time.sleep(sleep_time)

# Function to get and store data for a specific date and data type
def get_and_store_data(date_str, data_type, get_data_func):
    type_dir = os.path.join(data_dir, data_type)
    os.makedirs(type_dir, exist_ok=True)
    file_path = os.path.join(type_dir, f"{date_str}.json")
    
    if not os.path.exists(file_path):
        rate_limit()
        try:
            data = get_data_func(date_str)
            with open(file_path, 'w') as f:
                json.dump(data, f)
            print(f"Stored {data_type} data for {date_str}")
        except (GarminConnectTooManyRequestsError, requests.exceptions.HTTPError) as e:
            error_message = str(e).lower()
            if "too many request" in error_message or "rate limit" in error_message:
                print(f"[GARMIN API RATE LIMIT] Rate limit exceeded for {data_type} data on {date_str}. Error: {e}")
                print("Waiting for 60 seconds before retrying...")
                time.sleep(60)  # Wait for 60 seconds before retrying
                return get_and_store_data(date_str, data_type, get_data_func)  # Retry the request
            else:
                print(f"[HTTP ERROR] Error fetching {data_type} data for {date_str}: {e}")
        except GarminConnectConnectionError as e:
            print(f"[CONNECTION ERROR] Failed to connect to Garmin API for {data_type} data on {date_str}: {e}")
        except GarminConnectAuthenticationError as e:
            print(f"[AUTHENTICATION ERROR] Failed to authenticate with Garmin API for {data_type} data on {date_str}: {e}")
        except Exception as e:
            print(f"[UNEXPECTED ERROR] An unexpected error occurred while fetching {data_type} data for {date_str}: {e}")
    else:
        print(f"{data_type} data for {date_str} already exists")

# Function to find the last scanned date
def find_last_scanned_date():
    heart_rate_dir = os.path.join(data_dir, 'heart_rate')
    if not os.path.exists(heart_rate_dir):
        return None
    
    files = os.listdir(heart_rate_dir)
    if not files:
        return None
    
    latest_file = max(files)
    return datetime.datetime.strptime(latest_file.split('.')[0], "%Y-%m-%d").date()

# New function to check if data exists for a given date
def check_data_exists(date):
    rate_limit()
    try:
        data = client.get_heart_rates(date.strftime("%Y-%m-%d"))
        return len(data) > 0
    except Exception:
        return False

# New function to perform binary search for the first date with data
def find_first_data_date():
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365)
    
    while start_date <= end_date:
        mid_date = start_date + (end_date - start_date) // 2
        if check_data_exists(mid_date):
            end_date = mid_date - datetime.timedelta(days=1)
        else:
            start_date = mid_date + datetime.timedelta(days=1)
    
    return start_date

# Parse command line arguments
parser = argparse.ArgumentParser(description="Fetch Garmin Connect data")
parser.add_argument("--date", help="Start date in YYYY-MM-DD format")
args = parser.parse_args()

# Set the start date and determine the run mode
today = datetime.date.today()
if args.date:
    start_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
    single_week_mode = True
else:
    last_scanned_date = find_last_scanned_date()
    if last_scanned_date:
        start_date = last_scanned_date + datetime.timedelta(days=1)
    else:
        print("No existing data found. Performing binary search to find the first date with data...")
        start_date = find_first_data_date()
        print(f"First date with data found: {start_date}")
    single_week_mode = False

# Check if start_date is in the future or today
if start_date > today:
    print(f"Start date {start_date} is in the future. No data to fetch. Exiting.")
    exit(0)
elif start_date == today:
    print(f"Start date {start_date} is today. All available data has been fetched. Exiting.")
    exit(0)

# Main loop to process data
while True:
    end_date = start_date + datetime.timedelta(days=6)
    if end_date > today:
        end_date = today

    if end_date < start_date:
        print(f"End date {end_date} is before start date {start_date}. No data to fetch. Exiting.")
        exit(0)

    print(f"Fetching data from {start_date} to {end_date}")

    # Get data for the specified date range
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        get_and_store_data(date_str, 'sleep', client.get_sleep_data)
        get_and_store_data(date_str, 'stress', client.get_stress_data)
        get_and_store_data(date_str, 'heart_rate', client.get_heart_rates)
        get_and_store_data(date_str, 'hrv', client.get_hrv_data)
        get_and_store_data(date_str, 'training_readiness', client.get_training_readiness)
        get_and_store_data(date_str, 'resting_heart_rate', client.get_rhr_day)
        
        current_date += datetime.timedelta(days=1)

    # Get and store body battery data for the entire date range
    body_battery_dir = os.path.join(data_dir, 'body_battery')
    os.makedirs(body_battery_dir, exist_ok=True)
    body_battery_file = os.path.join(body_battery_dir, f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.json")

    if not os.path.exists(body_battery_file):
        rate_limit()
        try:
            body_battery_data = client.get_body_battery(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            with open(body_battery_file, 'w') as f:
                json.dump(body_battery_data, f)
            print(f"Stored body battery data from {start_date} to {end_date}")
        except GarminConnectTooManyRequestsError:
            print(f"Too many requests for body battery data. Skipping for now.")
        except (GarminConnectConnectionError, GarminConnectAuthenticationError) as e:
            print(f"Error fetching body battery data: {e}")
    else:
        print(f"Body battery data from {start_date} to {end_date} already exists")

    print(f"Data retrieval and storage complete for {start_date} to {end_date}")
    
    if single_week_mode or end_date >= today:
        print("Reached end of specified range or current date. Exiting.")
        break
    
    # Move to the next week
    start_date = end_date + datetime.timedelta(days=1)
    
    # Wait for 60 seconds before starting the next week
    print("Waiting 60 seconds before processing the next week...")
    time.sleep(60)

print("Script execution complete.")