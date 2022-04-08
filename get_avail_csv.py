import requests
import os
from dotenv import load_dotenv
from io import StringIO


def fetch_avail_csv() -> StringIO:
    load_dotenv()
    avail_csv_path = os.getenv("AVAIL_CSV_PATH")
    r = requests.get(avail_csv_path)
    r.encoding = r.apparent_encoding
    return StringIO(r.text)
