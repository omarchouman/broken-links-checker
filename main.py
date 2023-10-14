# from flask import Flask, request, jsonify
# import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin
#
# app = Flask(__name__)
#
#
# def find_broken_links(base_url):
#     # Dictionary to store the results
#     results = {
#         "broken_links": [],
#         "checked_links": set(),
#     }
#
#     def check_links(url):
#         if url in results["checked_links"]:
#             return
#         results["checked_links"].add(url)
#
#         try:
#             response = requests.get(url)
#             if response.status_code != 200:
#                 results["broken_links"].append(url)
#         except Exception as e:
#             results["broken_links"].append(url)
#
#         # Parse the HTML content
#         soup = BeautifulSoup(response.text, 'html.parser')
#
#         # Find all links on the page
#         links = soup.find_all('a', href=True)
#         for link in links:
#             absolute_url = urljoin(url, link['href'])
#             check_links(absolute_url)
#
#     check_links(base_url)
#     return results
#
#
# @app.route('/check_broken_links', methods=['POST'])
# def check_broken_links_api():
#     data = request.get_json()
#     website_url = data.get('website_url')
#
#     if not website_url:
#         return jsonify({"error": "Please provide a 'website_url' in the request body"}), 400
#
#     results = find_broken_links(website_url)
#     return jsonify(results)
#
#
# if __name__ == '__main__':
#     app.run(debug=True)

from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)


def find_broken_links(base_url, max_links=3):
    # Set to store broken links
    broken_links = set()
    # Counter for limiting the number of checked links
    checked_links_count = 0

    def check_link(url):
        nonlocal checked_links_count
        if checked_links_count >= max_links:
            return
        try:
            response = requests.head(url, allow_redirects=True, timeout=5)
            if response.status_code != 200:
                broken_links.add(url)
        except requests.RequestException:
            broken_links.add(url)
        finally:
            checked_links_count += 1

    def parse_links(url):
        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [urljoin(url, link['href']) for link in soup.find_all('a', href=True)]
            return links
        except requests.RequestException:
            return []

    def check_links_recursive(url):
        nonlocal checked_links_count
        if checked_links_count >= max_links:
            return
        if url in broken_links:
            return
        try:
            links = parse_links(url)
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(check_link, links)
                executor.map(check_links_recursive, links)
        except requests.RequestException:
            pass

    check_links_recursive(base_url)

    return {"broken_links": list(broken_links)}


@app.route('/check_broken_links', methods=['POST'])
def check_broken_links_api():
    data = request.get_json()
    website_url = data.get('website_url')

    if not website_url:
        return jsonify({"error": "Please provide a 'website_url' in the request body"}), 400

    try:
        results = find_broken_links(website_url, max_links=100)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)

