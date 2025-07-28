
import os
import zipfile
import pandas as pd
from typing import List


def extract_and_concat_uber_csvs(data_dir: str = "data/uber_raw") -> pd.DataFrame:
    """
    Detects zipped Uber NYC trip files in the given directory, unzips them if needed, and loads all CSVs in time order.
    Returns a concatenated DataFrame with all trips.
    """
    # Ensure directory exists
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    # Unzip all .zip files in the directory
    for fname in os.listdir(data_dir):
        if fname.lower().endswith(".zip"):
            zip_path = os.path.join(data_dir, fname)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for member in zf.namelist():
                    if member.lower().endswith(".csv"):
                        out_path = os.path.join(data_dir, os.path.basename(member))
                        if not os.path.exists(out_path):
                            zf.extract(member, data_dir)
                            if os.path.dirname(member):
                                os.rename(os.path.join(data_dir, member), out_path)

    # Find all CSVs in the directory (ignore subfolders)
    csvs = [
        os.path.join(data_dir, f)
        for f in os.listdir(data_dir)
        if f.lower().endswith('.csv') and os.path.isfile(os.path.join(data_dir, f))
    ]
    if not csvs:
        raise FileNotFoundError(f"No Uber CSV files found in {data_dir}")

    # Load all CSVs, append, and sort by date
    dfs = []
    for path in sorted(csvs):
        try:
            df = pd.read_csv(
                path,
                usecols=["Date/Time", "Lat", "Lon", "Base"],
                parse_dates=["Date/Time"],
                infer_datetime_format=True,
            )
            dfs.append(df)
        except Exception as e:
            print(f"Warning: Could not load {path}: {e}")
    if not dfs:
        raise ValueError("No valid Uber CSVs could be loaded.")
    full_df = pd.concat(dfs, ignore_index=True)
    # Sort by date ascending
    full_df = full_df.sort_values(by="Date/Time").reset_index(drop=True)
    return full_df
