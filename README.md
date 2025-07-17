# Python-Based_Automated_Process_for_Missing_Data_in_Weather_Stations

This script helps the user to automatically find and analyze weather stations from GHCN based on region, variable, and date; producing a graph that shows the missing data percentages per day. 

Setup:
	Before running the script, make sure to download the following files from https://www.ncei.noaa.gov/pub/data/ghcn/daily/:
ghcnd-stations.txt
This file contains metadata for all global GHCN-Daily stations.
ghcnd-inventory.txt
This file lists which variables (e.g. TMAX, PRCP) are available at each station and for what years.

Save both files in the same directory as the Python script. 

	When running the script (preferably through Spyder), the user will be prompted to enter the following:
    1. Minimum latitude 
    2. Maximum latitude 
    3. Minimum longitude 
    4. Maximum longitude
    5. Year (e.g. 2012)
    6. Month (e.g. 10)
    7. Variable: must be only of the standard GHCN-Daily variable codes
    8. TMAX: Maximum daily temperature (C)
    9. TMIN: Minimum daily temperature (C)
    10. TAVG: Average daily temperature (C)
    11. PRCP: Total daily precipitation (mm)
    12. SNWD: Snow depth (mm)

How the Script Works:
Filters all GHCN stations within the selected lat/lon bounding box.
Matches those stations to ones that recorded the selected variable in the chosen year.
Downloads .dly files only for relevant stations from NOAA’s FTP.
Parses and checks which days each station reported valid data.
Outputs: 
A graph of % missing data per day for the chosen region and variable
A CSV file: missing_summary_<VARIABLE>_<YEAR>_<MONTH>.csv
It is saved automatically into the user’s working file.
