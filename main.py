from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)


def find_broken_links(base_url, max_links=None):
    """Find broken links on a website.

    Args:
        base_url: The base URL of the website.
        max_links: The maximum number of links to check.

    Returns:
        A list of broken links.
    """

    broken_links = set()
    checked_links_count = 0
    executor = ThreadPoolExecutor(max_workers=10)

    def check_link(url):
        nonlocal checked_links_count
        if checked_links_count >= max_links:
            return
        try:
            response = requests.get(url, allow_redirects=True, timeout=5)
            if response.status_code != 200:
                broken_links.add(url)
        except requests.RequestException:
            broken_links.add(url)
        finally:
            checked_links_count += 1

    def parse_links(url):
        """Parse the links on a web page.

        Args:
            url: The URL of the web page.

        Returns:
            A list of links on the web page.
        """

        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [urljoin(url, link['href']) for link in soup.find_all('a', href=True)]

            # Only check links on the same domain
            domain = urlparse(base_url).netloc
            links = [link for link in links if urlparse(link).netloc == domain]

            return links
        except requests.RequestException:
            return []

    check_link(base_url)

    executor.map(check_link, parse_links(base_url))

    executor.shutdown(wait=True)

    return list(broken_links)


@app.route('/check_broken_links', methods=['POST'])
def check_broken_links_api():
    data = request.get_json()
    website_url = data.get('website_url')

    if not website_url:
        return jsonify({"error": "Please provide a 'website_url' in the request body"}), 400

    try:
        results = find_broken_links(website_url, max_links=None)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)

