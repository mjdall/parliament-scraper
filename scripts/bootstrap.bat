conda env create -f environment.yml
call activate parliament_scraper

python scripts\scrape_meta.py
