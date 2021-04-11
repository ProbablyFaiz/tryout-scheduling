import requests
import os
from dotenv import load_dotenv
from io import StringIO


def fetch_avail_csv():
    load_dotenv()
    avail_csv_path = os.getenv("AVAIL_CSV_PATH")
    r = requests.get(avail_csv_path)
    return StringIO(r.text)