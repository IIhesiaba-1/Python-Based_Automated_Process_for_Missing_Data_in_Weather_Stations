import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests

# USER INPUT 
try:
    min_lat = float(input("Min latitude (e.g., 33): "))
    max_lat = float(input("Max latitude (e.g., 45): "))
    min_lon = float(input("Min longitude (e.g., -85): "))
    max_lon = float(input("Max longitude (e.g., -70): "))
    year = int(input("Enter year (e.g., 2012): ").strip())
    month = int(input("Enter month (e.g., 10): "))
    variable = input("Enter variable (TMAX, TMIN, PRCP, TAVG): ").strip().upper()
except:
    print("Invalid input.")
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
    (inventory['FIRSTYEAR'] <= year) &
    (inventory['LASTYEAR'] >= year)
]
print(f"Inventory filtered: {len(inv_filtered)} stations with {variable} in {year}.")

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
            with open(dest, 'wb') as f:
                f.write(r.content)
            print(f"Downloaded {station_id}.dly")
        except Exception as e:
            print(f"Failed to download {station_id}: {e}")

# PARSE DLY FILE
def parse_dly(filepath, variable, year, month):
    days = [None]*31
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if line[17:21] == variable and int(line[11:15]) == year and int(line[15:17]) == month:
                    for i in range(31):
                        val = int(line[21 + i*8 : 26 + i*8][:5])
                        if val != -9999:
                            days[i] = days[i] + 1 if days[i] else 1
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    return days

# LOOP THROUGH STATIONS
total = np.zeros(31)
valid = np.zeros(31)

for station_id in stations['ID'].unique():
    path = os.path.join(dly_folder, f"{station_id}.dly")
    if os.path.exists(path):
        vals = parse_dly(path, variable, year, month)
        for i in range(31):
            if vals[i] is not None:
                valid[i] += 1
            total[i] += 1

# CREATE SUMMARY WITH MISSING STATION IDS PER DAY
days = np.arange(1, 32)
missing_station_ids = [[] for _ in range(31)]  # list of missing station IDs per day

# find and populate missing station IDs
for station_id in stations['ID'].unique():
    path = os.path.join(dly_folder, f"{station_id}.dly")
    if os.path.exists(path):
        vals = parse_dly(path, variable, year, month)
        for i in range(31):
            if vals[i] is None:
                missing_station_ids[i].append(station_id)

#summary DataFrame
summary = pd.DataFrame({
    'Day': days,
    'Stations Reporting': valid.astype(int),
    'Stations Missing': (total - valid).astype(int),
    'Total Stations': total.astype(int),
    '% Missing': np.round((1 - valid / total) * 100, 1),
    'Missing Station IDs': [', '.join(ids) if ids else '' for ids in missing_station_ids]
})

print(summary)
# PLOT
plt.figure(figsize=(10, 5))
plt.plot(summary['Day'], summary['% Missing'], marker='o', color='darkred')
plt.title(f'% Missing {variable} for {year}-{str(month).zfill(2)} in Region')
plt.xlabel('Day')
plt.ylabel('% Missing')
plt.grid(True)
plt.tight_layout()
plt.show()


print(f"Final filtered station count: {len(stations)}")
print("\nSelected Stations:")
print(stations[['ID', 'LAT', 'LON', 'NAME']].to_string(index=False))

# --- Updated: Save stations with missing data + frequency info ---
stations_with_missing_data = []

for station_id in stations['ID'].unique():
    path = os.path.join(dly_folder, f"{station_id}.dly")
    if os.path.exists(path):
        vals = parse_dly(path, variable, year, month)
        total_days = len(vals)
        missing_days = sum(1 for v in vals if v is None)
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

# Convert to DataFrame and save
missing_df = pd.DataFrame(stations_with_missing_data)
missing_df.to_csv(
    f'stations_with_missing_data_{variable}_{year}_{str(month).zfill(2)}.csv',
    index=False
)

print("Saved stations with missing data and frequency to CSV.")


# SAVE OUTPUT
summary.to_csv(f'missing_summary_{variable}_{year}_{str(month).zfill(2)}.csv', index=False)
print("Summary saved to CSV.")

# Export selected stations to CSV
stations[['ID', 'LAT', 'LON', 'NAME']].to_csv(f'selected_stations_{variable}_{year}_{str(month).zfill(2)}.csv', index=False)
print("Selected stations saved to CSV.")
