import random
import logging
from time import sleep

from bs4 import BeautifulSoup, element, NavigableString
import requests
from urllib3.exceptions import MaxRetryError, ProtocolError
from requests.exceptions import ProxyError, ConnectionError, HTTPError, SSLError, Timeout
from gevent import pool

logger = logging.getLogger()
logger.setLevel(logging.INFO)

################################# ~ Proxies ~ ####################################

# Get a list of free proxies. We expect many to not work.
# Credit to https://www.scrapehero.com/how-to-rotate-proxies-and-ip-addresses-using-python-3/
def fetch_proxies():
    proxy_lod = []
    response = requests.get('https://free-proxy-list.net/')

    parsed = BeautifulSoup(response.content, "html.parser")
    if not parsed:
        logging.error("No parsed in fetch_proxies")
        return None

    table = parsed.find('tbody')
    rows = table.find_all('tr')
    for row in rows:
        if row.contents[6].text == 'yes':          # Only want proxies that support HTTPS
            proxy = {
                'ip': row.contents[0].text,
                'port': row.contents[1].text,
                'full': ":".join([row.contents[0].text, row.contents[1].text]),
                'location': row.contents[3].text,
                'type': row.contents[4].text   # Options are: elite proxy, anonymous, transparent
            }
            if proxy['type'] != 'transparent': # Not a proxy at that point lol
                proxy_lod.append(proxy)

    logging.info(f'Found: {len(proxy_lod)} proxies')
    return proxy_lod


# Take the proxy list from fetch_proxies and return a tested, working proxy
def rotate_proxies(inputProxyList, **kwargs):
    if not inputProxyList:
        inputProxyList = fetch_proxies()
    if all(isinstance(x, str) for x in inputProxyList): # list recycled in
        return iteratively_test_proxies(inputProxyList, kwargs.get("location"))

    if kwargs.get("location") and isinstance(inputProxyList, list): # ie a list of dicts
        inputProxyList = [x for x in inputProxyList if all([kwargs.get("location").lower() in x['location'].lower(), x['type'] != 'transparent'])]

    proxies = [d['full'] for d in inputProxyList] # Extract full ips
    proxies = list(set(proxies))                  # Deduplicate
    proxies = random.sample(proxies, len(proxies))

    if kwargs.get("async_test"):
        proxy = asynchronously_test_proxies(proxies)
    else:
        proxy, proxies = iteratively_test_proxies(proxies, kwargs.get("location"))

    return proxy, proxies


# Test proxies, one by one
def iteratively_test_proxies(proxies, optionalLocation):
    for proxy in proxies:
        result = test_proxy(proxy)
        if result:
            logging.info('First successful response is: ' + str(proxy))
            return proxy, proxies
        else:
            proxies.remove(proxy)

    return rotate_proxies(proxies, location=optionalLocation)


# Test proxies in batches of 10 simultaneously greenlet pseudothread
def asynchronously_test_proxies(inputList):
    taskpool = pool.Pool(size=10)
    for single_task in (taskpool.imap_unordered(test_proxy, inputList, maxsize=1)):
        if single_task:
            logging.info('First successful async response is: ' + str(single_task))
            return single_task


# Makes a simple outbound request and waits up to 1.5s for a response
def test_proxy(proxy):
    try:
        requests.get('https://httpbin.org/ip', timeout=1.5, proxies={"http": f"http://{proxy}", "https": f"https://{proxy}"})
        return proxy

    except Exception as e:                 # Most free proxies will often get connection errors.
        logging.info("Skipping. Connnection error on " + str(proxy))
        return None


################################# ~ Header Modification ~ ####################################


# Mock a series of different browser / OS types
def rotate_agent():
    agents = ["Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.86 Safari/537.36",           # Desktop
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.7 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.7",   # Desktop
              "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.86 Safari/537.36",          # Desktop
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/602.2.14 (KHTML, like Gecko) Version/10.0.1 Safari/602.2.14",
              "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36",
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36",
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36",
              "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36",
              "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36",
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
              "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0",
              "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.86 Safari/537.36",
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/601.1.56 (KHTML, like Gecko) Version/9.0 Safari/601.1.56",
              "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36",
              "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36",
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36", # recent chrome
              "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.106 Mobile Safari/537.36",
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36", # # 1 Browser: Chrome 68.0 Win10 16-bit
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36", # # 2 Browser: Chrome 69.0 Win10 16-bit
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36"] # # 3 Browser: Chrome 68.0 macOS 16-bit
    return random.choice(agents)


# Mock the refering domain. The mulitple occurance of certain search engines reflects their relative popularity
def rotate_referer():
    referers = ["www.bing.com",
                "www.yahoo.com",
                "www.google.com", "www.google.com", "www.google.com", "www.google.com"
                "www.duckduckgo.com"]
    return random.choice(referers)


def rotate_encoding():
    encodings = ["gzip, deflate, br, sdch", "gzip, deflate, br"]
    return random.choice(encodings)


def rotate_language():
    languages = ["en-US,en;q=0.8", "en-US,en;q=0.9"]
    return random.choice(languages)


def rotate_accept():
    accepts = ["text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"]
    return random.choice(accepts)


################################# ~ Outbound Requests ~ ####################################


# Mock a browser and visit a site
def site_request(url, proxy, wait, **kwargs):
    if wait and wait != 0:
        sleep(random.uniform(wait, wait+1))    # +/- 0.5 sec from specified wait time. Pseudorandomized.

    if kwargs.get("clean_url"):
        url = url.split("://", 1)[1] if "://" in url else url
        url = url.split("www.", 1)[1] if "www." in url else url
        url = "https://" + url

    # Spoof a typical browser header. HTTP Headers are case-insensitive.
    headers = {
        'user-agent': kwargs.get("agent", rotate_agent()),
        'referer': kwargs.get("referer", rotate_referer()),          # Note: this is intentionally a misspelling of referrer
        'accept-encoding': rotate_encoding(),
        'accept-language': rotate_language(),
        'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        'cache-control': "no-cache",
        'upgrade-insecure-requests': "1",                        # Allow redirects from HTTP -> HTTPS
        'DNT': "1",                                              # Ask the server to not be tracked (lol)
    }
    try:
        request_kwargs = {}
        if proxy:
            request_kwargs["proxies"] = {"http": f"http://{proxy}", "https": f"https://{proxy}"}

        # TODO needs more testing
        if kwargs.get("prevent_redirects"):
            request_kwargs["allow_redirects"] = False

        response = requests.get(url, headers=headers, **request_kwargs)

    except (MaxRetryError, ProxyError, SSLError, ProtocolError, Timeout, ConnectionError, HTTPError) as e:
        logging.warning(f'-----> ERROR. ROTATE YOUR PROXY. {e}<-----')
        return '-----> ERROR. ROTATE YOUR PROXY. <-----', 666
    except Exception as e:
        logging.warning(f'-----> ERROR. Request Threw: Unknown Error. {e}<-----')
        return '-----> ERROR. Request Threw: Unknown Error. <-----', 666

    if response.status_code not in [200, 202, 301, 302]:
        logging.warning(f'-----> ERROR. Request Threw: {response.status_code} <-----')
    if response.status_code in [502, 503, 999]:
        return f'-----> ERROR. Request Threw: {response.status_code}. ROTATE YOUR PROXY <-----', 666

    if kwargs.get("soup"):                       # Allow functions to specify if they want parsed soup or plain request resopnse
        return BeautifulSoup(response.content, 'html.parser'), response.status_code
    else:
        return response, response.status_code


# This will handle 1) Fetching and Rotating proxies and 2) Handling and Retrying failed requests
def fully_managed_site_request(url, **kwargs):
    proxies = fetch_proxies()
    proxy, proxies = rotate_proxies(proxies, location=kwargs.get("location"), async_test=True)
    response, status_code = site_request(url, proxy, kwargs.get("wait", 1), **kwargs)

    while isinstance(response, str): # Returned error messaged
        proxy, proxies = rotate_proxies(proxies, location=kwargs.get("location"), async_test=True)
        response, status_code = site_request(url, proxy, wait=kwargs.get("wait", 0), **kwargs)

    return response, status_code


# Will extract the text from, and concatenate together, all elements of a given selector
def flatten_multiple_selectors(enclosing_element, selector_type, **kwargs):
    textlist = []

    for ele in enclosing_element.findAll(selector_type):
        if not ele:
            continue
        text = str(ele.get_text()).strip().replace("\n", "")
        if text:
            textlist.append(text)

    if kwargs.get("output_str"):
        return ", ".join(textlist)
    return textlist


# Will extract the text from, and concatenate together, all child elements of a given selector
def flatten_neigboring_selectors(enclosing_element, selector_type, **kwargs):
    textlist = []

    for ele in enclosing_element.findAll(selector_type):
        next_s = ele.nextSibling
        if not (next_s and isinstance(next_s, NavigableString)):
            continue
        text = str(next_s).strip().replace("\n", "")
        if text:
            textlist.append(text)

    if kwargs.get("output_str"):
        return ", ".join(textlist)
    return textlist


# A safer way to execute a find -> .get_text() statement e.g. parsed.find('div', {class : 'example'})
def safely_get_text(parsed, html_type, property_type, identifier, **kwargs):
    if not parsed:
        return None

    html_tag = parsed.find(html_type, {property_type : identifier})

    if not html_tag:
        return None

    return html_tag.text.replace("\n", "").strip() if html_tag else None
