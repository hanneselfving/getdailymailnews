import urllib3
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

#TODO Format text only thread name and readers, maybe by using html element to get title

# Function to save results to a text file with the current date and time
def save_results_to_file(results):
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"flashback_threads_{current_time}.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write("Top Most Read Threads (Sorted by Readers)\n")
        file.write(f"Scraped at: {now}\n\n")
        for index, result in enumerate(results):
            file.write(f"Thread {index + 1}: {result['text']} readers: {result['readers']}\n")
    print(f"Results saved to {filename}")

# Define the URL and headers (including a custom user agent)
url = "https://www.flashback.org/nya-amnen"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
}

# Create a session with retry mechanism
session = requests.Session()
retry = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])

# Mount retry for HTTP and HTTPS
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Fetch the page content with retries
try:
    response = session.get(url, headers=headers)
    response.raise_for_status()  # Raise exception if the request failed
    html_content = response.content

    # Parse the page with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Collect data from all <tr> elements
    rows = soup.find_all("tr")
    results = []
    
    for row in rows:
        row_text = row.get_text(strip=True)  # Get all text within the <tr>

        # Extract the number of readers (läsare) using a regex
        match = re.search(r'(\d+)\s*läsare', row_text)
        if match:
            readers_count = int(match.group(1))  # Extract the number of readers
        else:
            readers_count = 0  # Default to 0 if no 'läsare' is found
        
        #row_text = row_text.split("tim sedan", 1)[0]
        row_text = row_text.split('•')[0]
        results.append({"text": row_text, "readers": readers_count})

    # Sort the results by the number of readers in descending order
    results.sort(key=lambda x: x['readers'], reverse=True)

    # Save results to a file
    save_results_to_file(results)
    print(results[:10])

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
