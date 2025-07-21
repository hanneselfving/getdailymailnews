from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import pandas as pd
import boto3

def get_articles_dm():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless")  # Recommended for cron usage

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.dailymail.co.uk/home/latest/index.html")
    time.sleep(5)

    seen_titles = set()
    results = []

    for _ in range(10):  # Scroll multiple times
        driver.execute_script("window.scrollBy(0, 3500);")
        time.sleep(4)
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

    driver.quit()

    sorted_articles = sorted(results, key=lambda x: x["comments"], reverse=True)[:10]

    # Generate simple HTML
    html = "<html><head><title>Top Commented Articles</title><style>body { font-family: sans-serif; padding: 2rem; } h1 { color: #444; } li { margin-bottom: 10px; }</style></head><body>"
    html += "<h1>Top 10 Commented Articles</h1><ol>"
    for article in sorted_articles:
        html += f"<li><b>{article['title']}</b> — {article['comments']} comments</li>"
    html += "</ol></body></html>"

    # Write to file
    with open("/tmp/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    # Upload to S3
    s3 = boto3.client("s3")
    s3.upload_file("/tmp/index.html", "ec2scraperstack-scrapersitebucketa4f75f29-k3fpfcawabry", "index.html", ExtraArgs={"ContentType": "text/html", "ACL": "public-read"})

get_articles_dm()
