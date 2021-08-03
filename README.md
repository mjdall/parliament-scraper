# Parliament Scraper

Web scraper for scraping [Hansard Reports](https://www.parliament.nz/en/pb/hansard-debates/rhr/)
 from the parliament website.
 Still a work progress but I'll look at implementing a robust scraper for
 scraping parliament notes and neatly formatting the output in JSON.
 Already there is a helpful structure to the report, providing us with
 question and answer pairs, debates and general talk. This can then be used
 for NLP projects to obtain pre/semi-labelled data. As it's parliament reports
 we can use party alignment to visualise and validate different aspects of
 natual language in a very controlled talking space with clean data.

## Usage

Install conda environment with `conda env create -f environment.yml`, 
and then activate it with `conda activate parliament_scraper`.

**OUTDATED**
Call the scraper with: `python scraper.py <DATE1> <optional: DATE2>`

Date format is YYYYMMDD, a possible 2 dates are passed, check the URL of the
 report you are looking to scrape, they are formatted as:
 `https://www.parliament.nz/en/pb/hansard-debates/rhr/combined/HansD_<DATE1>_<DATE2>`.
If DATE1 and DATE2 are the same, only one date needs to be passed to the scraper.

## Output

The scraper will write to a file called `debate_DATE1_DATE2.json` in the current
 directory.

Check `example_out.json` for an example of the output format.

## State
* ~~Needs work, can ony scrape `20210708` currently~~
* ~~Needs to be more robust to tag structure~~
* Update: Scraper code working more robust to tag structure,
    see `notebooks/parser.ipynb`, `scraper.py` needs to be updated with changes
* BillDebate -> Debate -> Subdebate structure doesn't nest
    when parent is BillDebate
* Code needs better formatting and structure
    * `parliament` module and submodules need better naming and documentation
* All report links can be crawled, see `notebooks/crawler.ipynb`
* Vote parsing needs to be properly re-implemented
