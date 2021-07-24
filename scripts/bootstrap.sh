conda env create -f environment.yml

conda activate parliament_scraper

mkdir -r -p outdir/meta
python scripts/scrape_meta.py
