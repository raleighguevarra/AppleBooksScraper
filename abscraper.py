import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
from bs4 import BeautifulSoup
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.chrome.options import Options

def clean_html(html_text):
    """Utility function to clean HTML content"""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text()

def fetch_book_details(url):
    """Fetches book details from the given URL"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    service = Service(executable_path='chromedriver.exe')
    with webdriver.Chrome(service=service, options=options) as driver:
        driver.get(url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        title = clean_html(soup.find('h1').text) if soup.find('h1') else 'No Title Found'
        
        author_div = soup.find('div', class_='book-header__author')
        if author_div and author_div.find('a'):
            author = clean_html(author_div.find('a').text)
        else:
            author = 'No Author Found'
        
        meta_description = soup.find('meta', attrs={'name': 'description'})
        if meta_description:
            description = clean_html(meta_description['content'])
        else:
            description = 'No Description Found'

        return {
            'title': title,
            'author': author,
            'description': description,
            'url': url
        }

def process_url(url):
    """Process a single URL to fetch and write book details to a CSV file"""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    service = Service(executable_path='chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.get(url)
    
    page_title = driver.title
    removals = [" - Apple Books", " - Apple_Books", " | Apple Books", "_-_Apple_Books", " – Apple Books"]
    for removal in removals:
        page_title = page_title.replace(removal, "")
    page_title = page_title.replace(" ", "_").replace("|", "_").replace(":", "_").replace("?", "").replace("*", "").replace("\"", "").replace("<", "").replace(">", "").replace("\\", "").replace("/", "")
    csv_file = f'{page_title}.csv'

    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    
    book_links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith("https://books.apple.com/us/book/")]
    
    books_details = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_book_details, url): url for url in book_links}
        for future in as_completed(future_to_url):
            try:
                book_details = future.result()
                books_details.append(book_details)
            except Exception as exc:
                print(f'{future_to_url[future]} generated an exception: {exc}')
    
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Title', 'Author', 'Description', 'URL'])
        for book in books_details:
            writer.writerow([book['title'], book['author'], book['description'], book['url']])
    
    print(f"Books information has been successfully written to {csv_file}")

def main(urls):
    """Main function to process either a single URL or a list of URLs from a file"""
    for url in urls:
        process_url(url)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch book details from Apple Books URLs.')
    parser.add_argument('-u', '--url', type=str, help='A single URL to fetch book details from')
    parser.add_argument('-f', '--file', type=str, help='A file containing a list of URLs, each on a new line')

    args = parser.parse_args()

    urls = []
    if args.url:
        urls.append(args.url)
    elif args.file:
        with open(args.file, 'r') as file:
            urls = [line.strip() for line in file if line.strip()]
    else:
        print("Please provide either a URL with -u or a file with -f.")
        exit(1)

    main(urls)
