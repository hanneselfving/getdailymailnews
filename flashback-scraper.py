
import urllib3
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import boto3
import os

# S3 config
BUCKET_NAME = "ec2scraperstack-scrapersitebucketa4f75f29-lbpem4zyqdki"
KEY = "index.html"
LOCAL_PATH = "/tmp/index.html"

# ScraperAPI config
SCRAPERAPI_KEY = "795b300a8c3d0a5a5bb02f06c7beea44"
TARGET_URL = "https://www.flashback.org/nya-amnen"
SCRAPERAPI_URL = "https://api.scraperapi.com/"

# Create S3 client
s3 = boto3.client("s3")

# Create HTTP session with retries
session = requests.Session()
retry = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

try:
    # Step 1: Fetch page through ScraperAPI
    payload = {
        'api_key': SCRAPERAPI_KEY,
        'url': TARGET_URL
    }
    response = session.get(SCRAPERAPI_URL, params=payload, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    # Step 2: Extract threads and reader counts
    rows = soup.find_all("tr")
    results = []
    for row in rows:
        row_text = row.get_text(strip=True)
        match = re.search(r'(\d+)\s*läsare', row_text)
        readers_count = int(match.group(1)) if match else 0
        thread_title = row_text.split('•')[0]
        results.append({"text": thread_title, "readers": readers_count})
    results.sort(key=lambda x: x['readers'], reverse=True)
    top_results = results[:10]

    # Step 3: Download existing HTML from S3 (if it exists)
    try:
        s3.download_file(BUCKET_NAME, KEY, LOCAL_PATH)
        with open(LOCAL_PATH, "r", encoding="utf-8") as f:
            existing_html = f.read()
    except Exception:
        existing_html = "<html><head><title>Top Commented Articles</title><style>body { font-family: sans-serif; padding: 2rem; } h1 { color: #444; } li { margin-bottom: 10px; }</style></head><body>"

    # Step 4: Append new section
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_section = f"<h2>Top Threads on Flashback — {now}</h2><ol>"
    for article in top_results:
        new_section += f"<li><b>{article['text']}</b> — {article['readers']} läsare</li>"
    new_section += "</ol>"

    if "</body></html>" in existing_html:
        updated_html = existing_html.replace("</body></html>", new_section + "</body></html>")
    else:
        updated_html = existing_html + new_section + "</body></html>"

    # Step 5: Save updated HTML
    with open(LOCAL_PATH, "w", encoding="utf-8") as f:
        f.write(updated_html)

    # Step 6: Upload back to S3
    s3.upload_file(LOCAL_PATH, BUCKET_NAME, KEY, ExtraArgs={"ContentType": "text/html"})

    print("index.html updated and uploaded to S3")

except requests.exceptions.RequestException as e:
    print(f"An error occurred while fetching data: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
