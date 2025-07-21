# scraper.py
import boto3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import pandas as pd
import os

def get_articles_dm():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.dailymail.co.uk/home/latest/index.html")
    time.sleep(5)

    seen_titles = set()
    results = []

    for i in range(8):
        print(f"Scroll {i+1}/8")
        driver.execute_script("window.scrollBy(0, 3500);")
        time.sleep(3)

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
    df = pd.DataFrame(sorted_articles)

    # Output as HTML
    html_output = df.to_html(index=False)
    with open("/tmp/index.html", "w") as f:
        f.write("<h1>Top 10 DailyMail Commented Articles</h1>" + html_output)

    # Upload to S3
    s3 = boto3.client('s3')
    s3.upload_file("/tmp/index.html", os.environ['S3_BUCKET'], "index.html", ExtraArgs={'ContentType': 'text/html'})

get_articles_dm()
