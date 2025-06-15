import requests
import json
import os
import whois
import argparse
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

SHODAN_API_KEY = os.getenv("SHODAN_API_KEY") or "shodan_api_key" # change the keys with your API key
CENSYS_API_ID = os.getenv("CENSYS_API_ID") or "censys_api_id"
CENSYS_API_SECRET = os.getenv("CENSYS_API_SECRET") or "your_censys_api_secret"

def print_banner():
    banner = r"""
  _____  ______  _____  ____  _   _  _  __
 |  __ \|  ____|/ ____|/ __ \| \ | |\ \/ /
 | |__) | |__  | |    | |  | |  \| | \  / 
 |  _  /|  __| | |    | |  | | . ` | > <  
 | | \ \| |____| |____| |__| | |\  | /  \ 
 |_|  \_\______|\_____|\____/|_| \_|/_/\_\

            RECONX - OSINT Tool
              By coder2205

"""
    print(banner)

def setup_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    return driver

def shodan_search(domain):
    print("[*] Searching Shodan...")
    try:
        url = f"https://api.shodan.io/dns/domain/{domain}?key={SHODAN_API_KEY}"
        return requests.get(url).json()
    except Exception as e:
        return {"error": str(e)}

def censys_search(domain):
    print("[*] Searching Censys...")
    try:
        res = requests.get(
            f"https://search.censys.io/api/v2/hosts/search?q={domain}",
            auth=(CENSYS_API_ID, CENSYS_API_SECRET),
        )
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def webarchive_search(domain):
    print("[*] Searching Wayback Machine...")
    url = f"http://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&fl=timestamp,original&collapse=urlkey"
    try:
        res = requests.get(url)
        return res.json()[1:] if res.status_code == 200 else []
    except Exception as e:
        return {"error": str(e)}

def whois_lookup(domain):
    print("[*] Performing WHOIS lookup...")
    try:
        info = whois.whois(domain)
        return {k: str(v) for k, v in info.items()}
    except Exception as e:
        return {"error": str(e)}

def github_search(domain):
    print("[*] Searching GitHub...")
    try:
        url = f"https://github.com/search?q={domain}&type=code"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        results = soup.find_all("a", class_="v-align-middle")
        return [f"https://github.com{a['href']}" for a in results[:5]]
    except Exception as e:
        return {"error": str(e)}

def dnsdumpster_search(domain):
    print("[*] Scraping DNSDumpster...")
    try:
        session = requests.Session()
        headers = {"User-Agent": "Mozilla/5.0"}
        homepage = session.get("https://dnsdumpster.com/", headers=headers)
        soup = BeautifulSoup(homepage.text, "html.parser")
        csrf = soup.find("input", {"name": "csrfmiddlewaretoken"})["value"]
        cookies = homepage.cookies.get_dict()

        res = session.post(
            "https://dnsdumpster.com/",
            headers={**headers, "Referer": "https://dnsdumpster.com/"},
            cookies=cookies,
            data={"csrfmiddlewaretoken": csrf, "targetip": domain},
        )
        result_soup = BeautifulSoup(res.text, "html.parser")
        tables = result_soup.find_all("table")
        data = []
        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:
                cols = row.find_all("td")
                data.append([col.text.strip() for col in cols])
        return data
    except Exception as e:
        return {"error": str(e)}

def search_facebook(domain):
    print("[*] Searching Facebook via Selenium...")
    results = []
    try:
        driver = setup_selenium()
        driver.get(f"https://www.facebook.com/search/top?q={domain}")
        time.sleep(5)
        links = driver.find_elements("xpath", "//a[contains(@href, 'facebook.com')]")
        for link in links:
            href = link.get_attribute("href")
            if href and domain in href:
                results.append(href)
        driver.quit()
        return list(set(results))[:5]
    except Exception as e:
        return [f"Error: {e}"]

def search_linkedin(domain):
    print("[*] Searching LinkedIn via Selenium...")
    results = []
    try:
        driver = setup_selenium()
        driver.get(f"https://www.linkedin.com/search/results/all/?keywords={domain}")
        time.sleep(5)
        links = driver.find_elements("xpath", "//a[contains(@href, 'linkedin.com')]")
        for link in links:
            href = link.get_attribute("href")
            if href and domain in href:
                results.append(href)
        driver.quit()
        return list(set(results))[:5]
    except Exception as e:
        return [f"Error: {e}"]

def search_social_media(domain):
    print("[*] Searching Social Media...")
    results = {}
    try:
        query = f"https://nitter.net/search?f=tweets&q={domain}"
        res = requests.get(query)
        soup = BeautifulSoup(res.text, 'html.parser')
        tweets = soup.find_all('div', class_='tweet-content')
        results["twitter"] = [tweet.text.strip() for tweet in tweets[:5]]
    except Exception as e:
        results["twitter"] = [f"Error: {e}"]

    results["linkedin"] = search_linkedin(domain)
    results["facebook"] = search_facebook(domain)

    return results

def save_report(domain, data):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_file = f"{domain}_report_{timestamp}.txt"
    json_file = f"{domain}_report_{timestamp}.json"

    with open(txt_file, "w", encoding='utf-8') as f:
        f.write(f"OSINT Report for {domain}\nGenerated: {datetime.now()}\n\n")
        for section, result in data.items():
            f.write(f"--- {section.upper()} ---\n")
            f.write(json.dumps(result, indent=2))
            f.write("\n\n")
    print(f"[+] Text report saved to {txt_file}")

    with open(json_file, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"[+] JSON report saved to {json_file}")

def main():
    print_banner()
    parser = argparse.ArgumentParser(description="OSINT tool by Coder2205")
    parser.add_argument("domain", help="Target domain")
    parser.add_argument("--no-shodan", action="store_true")
    parser.add_argument("--no-censys", action="store_true")
    parser.add_argument("--no-whois", action="store_true")
    parser.add_argument("--no-webarchive", action="store_true")
    parser.add_argument("--no-github", action="store_true")
    parser.add_argument("--no-dnsdumpster", action="store_true")
    parser.add_argument("--no-social", action="store_true")

    args = parser.parse_args()
    domain = args.domain.strip()
    results = {}

    if not args.no_shodan:
        results["shodan"] = shodan_search(domain)
    if not args.no_censys:
        results["censys"] = censys_search(domain)
    if not args.no_webarchive:
        results["webarchive"] = webarchive_search(domain)
    if not args.no_whois:
        results["whois"] = whois_lookup(domain)
    if not args.no_github:
        results["github"] = github_search(domain)
    if not args.no_dnsdumpster:
        results["dnsdumpster"] = dnsdumpster_search(domain)
    if not args.no_social:
        results["social_media"] = search_social_media(domain)

    save_report(domain, results)

if __name__ == "__main__":
    main()
