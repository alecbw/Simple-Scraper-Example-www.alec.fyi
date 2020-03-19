# Related article
https://www.alec.fyi/how-to-scrape.html

# Using this


This repo is meant as a simple example of implementing a webpage scraper. More complicated pagination, retry, data hygiene, and orchestration logic is not included here.

Please keep in mind this does not use a proxy. You should implement a proxy before productionalizing any scraping code.

To use, run
```
python3 test_scrapability.py
```

Included is an optional export to CSV (locally). To enable, add the -export flag:

```
python3 test_scrapability.py -export True
```
