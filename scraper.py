from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime
from zoneinfo import ZoneInfo
import boto3
import os
import re

# S3 config
BUCKET_NAME = "ec2scraperstack-scrapersitebucketa4f75f29-lbpem4zyqdki"
KEY = "index.html"
LOCAL_PATH = "/tmp/index.html"

# Setup Selenium
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=2000,2500")
driver = webdriver.Chrome(options=options)

# Open Daily Mail page
driver.get("https://www.dailymail.co.uk/home/latest/index.html")
driver.implicitly_wait(5)

# Scrape articles
seen_titles = set()
results = []

for _ in range(10):  # Scroll multiple times
    articles = driver.find_elements(By.CSS_SELECTOR, ".article")
    for article in articles:
        try:
            title_tag = article.find_element(By.CSS_SELECTOR, "h3 > a")
            title = title_tag.text.strip()
        except:
            continue

        if title in seen_titles:
            continue
        seen_titles.add(title)

        try:
            comment_tag = article.find_element(By.CSS_SELECTOR, "span.readerCommentNo")
            comments = int(comment_tag.text.strip())
        except:
            comments = 0

        results.append({"title": title, "comments": comments})

    driver.execute_script("window.scrollBy(0, 2500);")

driver.quit()

# Top 10 by comments
sorted_articles = sorted(results, key=lambda x: x["comments"], reverse=True)[:10]

# Create new Daily Mail section
swedish_time = datetime.now(ZoneInfo("Europe/Stockholm")).strftime("%Y-%m-%d %H:%M")
dm_section = f"<!-- DAILYMAIL-START -->\n<h1>Top 10 Commented Articles — {swedish_time}</h1><ol>"
for article in sorted_articles:
    dm_section += f"<li><b>{article['title']}</b> — {article['comments']} comments</li>"
dm_section += "</ol>\n<!-- DAILYMAIL-END -->"

# Download existing HTML if exists
s3 = boto3.client("s3")
try:
    s3.download_file(BUCKET_NAME, KEY, LOCAL_PATH)
    with open(LOCAL_PATH, "r", encoding="utf-8") as f:
        existing_html = f.read()
except Exception:
    # Fresh fallback layout with placeholders for both sections
    existing_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8'>
    <title>Top Commented Articles</title>
    <style>
        body { font-family: sans-serif; padding: 2rem; }
        h1 { color: #444; }
        li { margin-bottom: 10px; }
    </style>
</head>
<body>
<!-- DAILYMAIL-START -->
<!-- Will be replaced by Daily Mail scraper -->
<!-- DAILYMAIL-END -->

<!-- FLASHBACK-START -->
<!-- Will be replaced by Flashback scraper -->
<!-- FLASHBACK-END -->
</body>
</html>"""

# Replace or insert the Daily Mail section
if "<!-- DAILYMAIL-START -->" in existing_html and "<!-- DAILYMAIL-END -->" in existing_html:
    updated_html = re.sub(
        r"<!-- DAILYMAIL-START -->(.*?)<!-- DAILYMAIL-END -->",
        dm_section,
        existing_html,
        flags=re.DOTALL,
    )
else:
    if "</body>" in existing_html:
        updated_html = existing_html.replace("</body>", dm_section + "\n</body>")
    else:
        updated_html = existing_html + dm_section

# Save and upload to S3
with open(LOCAL_PATH, "w", encoding="utf-8") as f:
    f.write(updated_html)

s3.upload_file(LOCAL_PATH, BUCKET_NAME, KEY, ExtraArgs={"ContentType": "text/html; charset=utf-8"})

print("index.html updated with Daily Mail section and uploaded to S3")
