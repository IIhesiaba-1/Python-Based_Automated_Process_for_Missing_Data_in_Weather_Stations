import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
from datetime import datetime, timedelta, date

# USER INPUT 
try:
    min_lat = float(input("Min latitude (e.g., 33): "))
    max_lat = float(input("Max latitude (e.g., 45): "))
    min_lon = float(input("Min longitude (e.g., -85): "))
    max_lon = float(input("Max longitude (e.g., -70): "))
    start_date_str = input("Enter start date (YYYY-MM-DD): ").strip()
    end_date_str = input("Enter end date (YYYY-MM-DD): ").strip()
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    if end_date < start_date:
        raise ValueError("End date must be after start date.")
    variable = input("Enter variable (TMAX, TMIN, PRCP, TAVG): ").strip().upper()
except Exception as e:
    print(f"Invalid input: {e}")
    exit()

# FILE PATHS
station_file = 'ghcnd-stations.txt'
inventory_file = 'ghcnd-inventory.txt'
dly_folder = 'dly_files'
os.makedirs(dly_folder, exist_ok=True)

# CHECK FILES EXIST 
for required_file in [station_file, inventory_file]:
    if not os.path.exists(required_file):
        print(f"Missing file: {required_file}")
        print("Download from: https://www.ncei.noaa.gov/pub/data/ghcn/daily/")
        exit()

#  LOAD & FILTER INVENTORY
inventory = pd.read_csv(inventory_file, delim_whitespace=True, header=None,
                        names=["ID", "LAT", "LON", "ELEMENT", "FIRSTYEAR", "LASTYEAR"])
inventory['ID'] = inventory['ID'].astype(str).str.strip()

inv_filtered = inventory[
    (inventory['ELEMENT'] == variable) &
    (inventory['FIRSTYEAR'] <= start_date.year) &
    (inventory['LASTYEAR'] >= end_date.year)
]
print(f"Inventory filtered: {len(inv_filtered)} stations with {variable} between {start_date} and {end_date}.")

#LOAD & FILTER STATIONS 
station_data = []
with open(station_file, 'r') as f:
    for line in f:
        station_id = line[0:11].strip()
        lat = float(line[12:20].strip())
        lon = float(line[21:30].strip())
        name = line[41:71].strip()
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            station_data.append((station_id, lat, lon, name))

station_df = pd.DataFrame(station_data, columns=["ID", "LAT", "LON", "NAME"])
station_df['ID'] = station_df['ID'].astype(str).str.strip()
print(f"Found {len(station_df)} stations in bounding box.")

# MERGE FILTERED STATIONS 
stations = pd.merge(station_df, inv_filtered[['ID']], on='ID', how='inner')
print(f"Final filtered station count: {len(stations)}")

# DOWNLOAD .DLY FILES
base_url = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/all"
for station_id in stations['ID'].unique():
    url = f"{base_url}/{station_id}.dly"
    dest = os.path.join(dly_folder, f"{station_id}.dly")
    if not os.path.exists(dest):
        try:
            r = requests.get(url)
            if r.status_code == 200:
                with open(dest, 'wb') as f:
                    f.write(r.content)
                print(f"Downloaded {station_id}.dly")
            else:
                print(f"Failed to download {station_id}: HTTP {r.status_code}")
        except Exception as e:
            print(f"Failed to download {station_id}: {e}")

# PARSE DLY FILE FOR DATE RANGE
def parse_dly(filepath, variable, start_date, end_date):
    days_dict = {}  # maps date objects to counts
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if line[17:21] == variable:
                    year = int(line[11:15])
                    month = int(line[15:17])
                    for i in range(31):
                        try:
                            val = int(line[21 + i*8 : 26 + i*8][:5])
                            day = i + 1
                            d = date(year, month, day)
                            if start_date <= d <= end_date and val != -9999:
                                if d not in days_dict:
                                    days_dict[d] = 1
                                else:
                                    days_dict[d] += 1
                        except:
                            continue
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    return days_dict

# Generate date list for summary
date_list = []
cur_date = start_date
while cur_date <= end_date:
    date_list.append(cur_date)
    cur_date += timedelta(days=1)

total = np.zeros(len(date_list))
valid = np.zeros(len(date_list))
missing_station_ids = [[] for _ in range(len(date_list))]

# LOOP THROUGH STATIONS
for station_id in stations['ID'].unique():
    path = os.path.join(dly_folder, f"{station_id}.dly")
    if os.path.exists(path):
        vals = parse_dly(path, variable, start_date, end_date)
        for i, d in enumerate(date_list):
            total[i] += 1
            if d in vals:
                valid[i] += 1
            else:
                missing_station_ids[i].append(station_id)

# SUMMARY TABLE
summary = pd.DataFrame({
    'Date': [d.strftime("%Y-%m-%d") for d in date_list],
    'Stations Reporting': valid.astype(int),
    'Stations Missing': (total - valid).astype(int),
    'Total Stations': total.astype(int),
    '% Missing': np.round((1 - valid / total) * 100, 1),
    'Missing Station IDs': [', '.join(ids) if ids else '' for ids in missing_station_ids]
})

print(summary)

# PLOT
plt.figure(figsize=(12, 5))
plt.plot(summary['Date'], summary['% Missing'], marker='o', color='darkred')
plt.title(f'% Missing {variable} from {start_date_str} to {end_date_str}')
plt.xlabel('Date')
plt.ylabel('% Missing')

plt.ylim(0, 100)
plt.yticks(np.arange(0, 101, 10))

plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()
plt.show()
print(f"Final filtered station count: {len(stations)}")
print("\nSelected Stations:")
print(stations[['ID', 'LAT', 'LON', 'NAME']].to_string(index=False))

# --- Save stations with missing data ---
stations_with_missing_data = []

for station_id in stations['ID'].unique():
    path = os.path.join(dly_folder, f"{station_id}.dly")
    if os.path.exists(path):
        vals = parse_dly(path, variable, start_date, end_date)
        total_days = len(date_list)
        missing_days = sum(1 for d in date_list if d not in vals)
        if missing_days > 0:
            station_info = stations[stations['ID'] == station_id].iloc[0]
            stations_with_missing_data.append({
                'ID': station_id,
                'LAT': station_info['LAT'],
                'LON': station_info['LON'],
                'NAME': station_info['NAME'],
                'Total Days': total_days,
                'Missing Days': missing_days,
                'Missing %': round((missing_days / total_days) * 100, 2)
            })

missing_df = pd.DataFrame(stations_with_missing_data)
missing_df.to_csv(
    f'stations_with_missing_data_{variable}_{start_date_str}_to_{end_date_str}.csv',
    index=False
)

print("Saved stations with missing data and frequency to CSV.")

# SAVE OUTPUT
summary.to_csv(f'missing_summary_{variable}_{start_date_str}_to_{end_date_str}.csv', index=False)
print("Summary saved to CSV.")

stations[['ID', 'LAT', 'LON', 'NAME']].to_csv(f'selected_stations_{variable}_{start_date_str}_to_{end_date_str}.csv', index=False)
print("Selected stations saved to CSV.")