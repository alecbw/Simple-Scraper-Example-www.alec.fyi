from util_requests import rotate_proxies, site_request, fully_managed_site_request


import csv
import argparse
import random

import requests
from bs4 import BeautifulSoup, element, NavigableString
from urllib3.exceptions import MaxRetryError, ProtocolError
from requests.exceptions import ProxyError, ConnectionError, HTTPError, SSLError, Timeout
from gevent import pool

argparser = argparse.ArgumentParser()
argparser.add_argument('-export', nargs='?', help="If you want the program to export the data to CSV")
argparser.add_argument('-use_proxy', nargs='?', help="If you want the program to fetch and rotate proxies")

args = argparser.parse_args()


################################################################################

if __name__ == "__main__":

    url = "https://en.wikipedia.org/wiki/Outline_of_science"
    if args.use_proxy:
        parsed, status_code = fully_managed_site_request(url, soup=True)
    else:
        parsed, status_code = site_request(url=url, proxy=None, wait=0, clean_url=True, soup=True)

    containing_div = parsed.find("div", {"id": "toc"})

    all_toctext_spans = containing_div.find_all("span", {"class": "toctext"})

    output_lod = []
    for n, toctext_span in enumerate(all_toctext_spans):
        print(toctext_span.get_text())
        output_lod.append({
            "Section": toctext_span.get_text(),
            "Input_URL": url
        })

    if args.export:
        with open('output.csv', 'w') as output_file:
            dict_writer = csv.DictWriter(output_file, output_lod[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(output_lod)
            print("Finished writing data to output.csv")
