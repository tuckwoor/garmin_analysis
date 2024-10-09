import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Function to load data from JSON files
def load_data(data_type):
    data = []
    data_dir = os.path.join('garmin_data', data_type)
    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            with open(os.path.join(data_dir, filename), 'r') as f:
                data.append(json.load(f))
    return data

# Load data
stress_data = load_data('stress')
sleep_data = load_data('sleep')
body_battery_data = load_data('body_battery')

# Preprocess data
def preprocess_stress(data):
    # print("Debug: Stress Data Input")
    # if isinstance(data, list):
    #     print(json.dumps(data[:2], indent=2))  # Print first two items if it's a list
    # elif isinstance(data, dict):
    #     print(json.dumps(data, indent=2))  # Print the entire dict if it's a dictionary
    # else:
    #     print(f"Unexpected data type: {type(data)}")

    if not data:
        print("Debug: Stress data is empty")
        return pd.DataFrame()
    
    # Handle both list and dictionary inputs
    if isinstance(data, dict):
        data = [data]  # Convert single dict to list
    elif not isinstance(data, list):
        print(f"Debug: Unexpected data type: {type(data)}")
        return pd.DataFrame()
    
    # Flatten the data if it's nested
    flattened_data = []
    for item in data:
        if isinstance(item, dict):
            flattened_data.append(item)
        elif isinstance(item, list):
            flattened_data.extend(item)
    
    if not flattened_data:
        print("Debug: No valid stress data found after flattening")
        return pd.DataFrame()
    
    df = pd.DataFrame(flattened_data)
    # print("Debug: Stress DataFrame columns after initial creation:")
    # print(df.columns)
    
    if 'calendarDate' in df.columns:
        df['date'] = pd.to_datetime(df['calendarDate'])
    if 'avgStressLevel' in df.columns:
        df['averageStressLevel'] = pd.to_numeric(df['avgStressLevel'], errors='coerce')
    
    # print("Debug: Stress DataFrame info after processing:")
    # print(df.info())
    
    return df

def preprocess_sleep(data):
    if not data or not isinstance(data, dict):
        return pd.DataFrame()
    daily_sleep = data.get('dailySleepDTO', {})
    if not daily_sleep:
        return pd.DataFrame()
    df = pd.DataFrame([daily_sleep])
    df['date'] = pd.to_datetime(df['calendarDate'])
    df['deepSleepSeconds'] = pd.to_numeric(df['deepSleepSeconds'], errors='coerce')
    return df

def preprocess_body_battery(data):
    print("Debug: Body Battery Data")
    print(json.dumps(data[:2], indent=2))  # Print first two days of data
    
    if not data or not isinstance(data, list):
        return pd.DataFrame()
    
    body_battery_records = []
    for day_data in data:
        if 'bodyBatteryValuesArray' in day_data:
            values = [entry[1] for entry in day_data['bodyBatteryValuesArray'] if len(entry) > 1 and entry[1] is not None]
            if values:
                max_body_battery = max(values)
                min_body_battery = min(values)
                avg_body_battery = sum(values) / len(values)
                body_battery_records.append({
                    'date': day_data['date'],
                    'max_body_battery': max_body_battery,
                    'min_body_battery': min_body_battery,
                    'avg_body_battery': avg_body_battery
                })
    
    df = pd.DataFrame(body_battery_records)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

# Create DataFrames
stress_df = pd.concat([preprocess_stress(d) for d in stress_data if d], ignore_index=True)
sleep_df = pd.concat([preprocess_sleep(d) for d in sleep_data if d], ignore_index=True)
body_battery_df = pd.concat([preprocess_body_battery(d) for d in body_battery_data if d], ignore_index=True)

# After creating the stress_df
print("Debug: Stress DataFrame Info")
print(stress_df.info())
print("\nFirst few rows of Stress DataFrame:")
print(stress_df.head())

# Print data info and first few rows
for name, df in [("Stress", stress_df), ("Sleep", sleep_df), ("Body Battery", body_battery_df)]:
    print(f"\n{name} DataFrame Info:")
    print(df.info())
    print(f"\nFirst few rows of {name} DataFrame:")
    print(df.head())

# Calculate daily averages
stress_avg = pd.Series(dtype='float64')
sleep_avg = pd.Series(dtype='float64')
body_battery_avg = pd.Series(dtype='float64')

if 'date' in stress_df.columns and 'averageStressLevel' in stress_df.columns:
    stress_df['day_of_week'] = stress_df['date'].dt.day_name()
    stress_avg = stress_df.groupby('day_of_week')['averageStressLevel'].mean().reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
else:
    print("Warning: Required columns for stress analysis not found.")
    print("Available columns in stress_df:", stress_df.columns)

if 'date' in sleep_df.columns and 'deepSleepSeconds' in sleep_df.columns:
    sleep_df['day_of_week'] = sleep_df['date'].dt.day_name()
    sleep_avg = sleep_df.groupby('day_of_week')['deepSleepSeconds'].mean().reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
else:
    print("Warning: Required columns for sleep analysis not found.")

if 'date' in body_battery_df.columns and 'avg_body_battery' in body_battery_df.columns:
    body_battery_df['day_of_week'] = body_battery_df['date'].dt.day_name()
    body_battery_avg = body_battery_df.groupby('day_of_week')['avg_body_battery'].mean().reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
else:
    print("Warning: Required columns for body battery analysis not found.")

# Before calculating stress_avg
print("\nDebug: Stress DataFrame columns:")
print(stress_df.columns)
print("\nUnique values in 'averageStressLevel' column:")
print(stress_df['averageStressLevel'].unique())

# Print the calculated averages
print("\nStress Average by Day of Week:")
print(stress_avg)
print("\nSleep Average by Day of Week:")
print(sleep_avg)
print("\nBody Battery Average by Day of Week:")
print(body_battery_avg)

# Calculate sleep change
if not sleep_df.empty and 'deepSleepSeconds' in sleep_df.columns:
    sleep_df['next_day_sleep'] = sleep_df['deepSleepSeconds'].shift(-1)
    sleep_df['sleep_change'] = sleep_df['next_day_sleep'] - sleep_df['deepSleepSeconds']
    sleep_change_avg = sleep_df.groupby('day_of_week')['sleep_change'].mean().reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])

    print("\nSleep Change Average by Day of Week:")
    print(sleep_change_avg)
else:
    print("Not enough sleep data to calculate sleep change.")
    sleep_change_avg = pd.Series()

# Normalize the data and calculate combined score
combined_score = None  # Initialize combined_score as None
if not stress_avg.empty and not sleep_change_avg.empty:
    stress_norm = (stress_avg - stress_avg.min()) / (stress_avg.max() - stress_avg.min())
    sleep_change_norm = (sleep_change_avg - sleep_change_avg.min()) / (sleep_change_avg.max() - sleep_change_avg.min())

    # Calculate a combined score (lower is better)
    combined_score = stress_norm + sleep_change_norm

    print("\nCombined Score by Day of Week:")
    print(combined_score)

    # Print the best day
    best_day = combined_score.idxmin()
    print(f"\nThe best day for heavy exercise is: {best_day}")

# Calculate the date range for the analysis
start_date = min(stress_df['date'].min(), sleep_df['date'].min(), body_battery_df['date'].min())
end_date = max(stress_df['date'].max(), sleep_df['date'].max(), body_battery_df['date'].max())
date_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

def safe_save_fig(filename):
    try:
        # Try to save the figure
        plt.savefig(filename, bbox_inches='tight')
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        # If there's an error, try to save with a new filename
        base, ext = os.path.splitext(filename)
        counter = 1
        while True:
            new_filename = f"{base}_{counter}{ext}"
            if not os.path.exists(new_filename):
                print(f"Attempting to save as {new_filename}")
                plt.savefig(new_filename, bbox_inches='tight')
                break
            counter += 1

# Only visualize if combined_score exists and has valid data
if combined_score is not None and not combined_score.empty:
    plt.figure(figsize=(12, 8))
    combined_score.plot(kind='bar')
    plt.title(f'Best Day for Heavy Exercise (Lower Score is Better)\nDate Range Analysed: {date_range}')
    plt.xlabel('Day of Week')
    plt.ylabel('Combined Score')
    plt.tight_layout()
    safe_save_fig('combined_score.png')
    plt.close()

    # Additional visualizations
    fig, axs = plt.subplots(2, 2, figsize=(15, 15))

    stress_avg.plot(kind='bar', ax=axs[0, 0], title=f'Average Stress Level\nDate Range: {date_range}')
    axs[0, 1].axis('off')  # Turn off the empty plot for body battery
    sleep_avg.plot(kind='bar', ax=axs[1, 0], title=f'Average Deep Sleep (seconds)\nDate Range: {date_range}')
    sleep_change_avg.plot(kind='bar', ax=axs[1, 1], title=f'Average Sleep Change (Next Day)\nDate Range: {date_range}')

    plt.tight_layout()
    safe_save_fig('additional_plots.png')
    plt.close()

    print("Plots have been saved. Please check the current directory for the output files.")
else:
    print("Not enough data to calculate combined score and create visualizations.")

def is_sleep_file_non_empty(data):
    daily_sleep = data.get('dailySleepDTO', {})
    key_fields = ['sleepTimeSeconds', 'deepSleepSeconds', 'lightSleepSeconds', 'remSleepSeconds']
    return any(daily_sleep.get(field) is not None and daily_sleep.get(field) != 0 for field in key_fields)

def is_stress_file_non_empty(data):
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'avgStressLevel' in item:
                stress_level = item['avgStressLevel']
                if stress_level is not None and stress_level != 0:
                    return True
    elif isinstance(data, dict) and 'avgStressLevel' in data:
        stress_level = data['avgStressLevel']
        if stress_level is not None and stress_level != 0:
            return True
    return False

def is_body_battery_file_non_empty(data):
    if isinstance(data, list):
        for day_data in data:
            if any(isinstance(item, list) and len(item) > 1 and item[1] is not None for item in day_data.get('bodyBatteryValuesArray', [])):
                return True
    return False

def find_earliest_non_empty_file(directory, data_type):
    files = sorted([f for f in os.listdir(directory) if f.endswith('.json')])
    for file in files:
        file_path = os.path.join(directory, file)
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if data_type == 'sleep' and is_sleep_file_non_empty(data):
            return file_path
        elif data_type == 'stress':
            stress_level = get_stress_level(data)
            if stress_level is not None:
                return file_path, stress_level
        elif data_type == 'body_battery' and is_body_battery_file_non_empty(data):
            return file_path
    
    return None

def get_stress_level(data):
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'avgStressLevel' in item:
                stress_level = item['avgStressLevel']
                if stress_level is not None and stress_level != 0:
                    return stress_level
    elif isinstance(data, dict) and 'avgStressLevel' in data:
        stress_level = data['avgStressLevel']
        if stress_level is not None and stress_level != 0:
            return stress_level
    return None

# Define data types and their directories
data_types = ['sleep', 'stress', 'body_battery']
data_dirs = {dt: os.path.join('garmin_data', dt) for dt in data_types}

# Find earliest non-empty file for each data type and determine the overall start date
earliest_dates = []
for data_type, directory in data_dirs.items():
    result = find_earliest_non_empty_file(directory, data_type)
    if result:
        if data_type == 'stress':
            earliest_file, stress_level = result
            filename = os.path.basename(earliest_file)
            print(f"{data_type.capitalize()} - Earliest file: {filename} (Avg Stress Level: {stress_level})")
        else:
            filename = os.path.basename(result)
            print(f"{data_type.capitalize()} - Earliest file: {filename}")
        date = datetime.strptime(filename.split('.')[0].split('_')[0], '%Y-%m-%d')
        earliest_dates.append(date)
    else:
        print(f"No non-empty files found for {data_type}")

if earliest_dates:
    analysis_start_date = max(earliest_dates)
    print(f"\nAnalysis start date: {analysis_start_date.strftime('%Y-%m-%d')}")
else:
    print("No valid dates found to determine analysis start date.")

# Use this analysis_start_date for further data processing

def print_file_content(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    print(f"Content of {os.path.basename(file_path)}:")
    print(json.dumps(data, indent=2))
    print("\n")

def process_stress_files(stress_files):

    earliest_file = min(non_empty_files, key=lambda x: x['date'])
    earliest_date = earliest_file['date']
    
    # Extract the avgStressLevel from the earliest file
    earliest_stress_level = None
    with open(earliest_file['path'], 'r') as f:
        data = json.load(f)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'avgStressLevel' in item:
                    earliest_stress_level = item['avgStressLevel']
                    if earliest_stress_level is not None and earliest_stress_level != 0:
                        break
        elif isinstance(data, dict) and 'avgStressLevel' in data:
            earliest_stress_level = data['avgStressLevel']

    print(f"Debug info:")
    print(f"  Total stress files: {total_files}")
    print(f"  Non-empty stress files: {len(non_empty_files)}")
    print(f"  Earliest file: {earliest_date.strftime('%Y-%m-%d')} (Avg Stress Level: {earliest_stress_level})")
    print(f"  Latest file: {latest_date.strftime('%Y-%m-%d')}")
