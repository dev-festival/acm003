import pandas as pd
import os
import pyodbc
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import warnings
import time       # for timing longer cells (running the sql query)

from datetime import datetime,timedelta


# Automatically search for .env in parent directories
load_dotenv(find_dotenv())

# Load from environment variables
DSN = os.getenv('MAXIMO_DSN')
USER = os.getenv('MAXIMO_USER')
PASSWORD = os.getenv('MAXIMO_PASS')

#Confirm Credentials
print(f"DSN: {DSN}")
print(f"User: {USER}")

# Suppress the pandas warning
warnings.filterwarnings('ignore', category=UserWarning)

def run_query_from_file(sql_path: str) -> pd.DataFrame:
    conn = pyodbc.connect(f"DSN={DSN};UID={USER};PWD={PASSWORD}")
    query = open(sql_path).read()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Start timing
start_time = time.time()

# Run the sql script
asset_rank = run_query_from_file('query/asset_rank.sql')

# Calculate and print execution time
execution_time = time.time() - start_time
print(f"Query execution time: {execution_time:.2f} seconds \n")

asset_rank['ASSETNUM'] = asset_rank['ASSETNUM'].astype('category')
asset_rank['ASSET_DESC'] = asset_rank['ASSET_DESC'].astype('category')
asset_rank['ASSET_CLASS'] = asset_rank['ASSET_CLASS'].astype('category')
asset_rank['ASSET_DEPT'] = asset_rank['ASSET_DEPT'].astype('category')
asset_rank['RANK'] = asset_rank['RANK'].astype('category')


asset_rank.info()