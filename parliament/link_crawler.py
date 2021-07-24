import re
from parliament.report_requests import request_report


def try_parse_href(href):
    link_regex_s = r"/en/pb/hansard-debates/rhr/combined/HansD_(\d{8})_(\d{8})"
    link_regex = re.compile(link_regex_s)

    # see if the href is a combined report
    combined_report = link_regex.findall(href)
    if combined_report:
        # return combined report
        return combined_report[0] + ("combined",)

    document_regex_s = r"/en/pb/hansard-debates/rhr/document/(\w+)/((?:\w|-)+)"
    document_regex = re.compile(document_regex_s)

    # see if the href is a document instead
    document_report = document_regex.findall(href)
    if not document_report:
        return []

    # return document
    return document_report[0] + ("document",)


def extract_links(soup):
    # gind all a tags with theme__link class with an href attribute
    links = soup.find_all("a", class_="theme__link", attrs="href")

    # get the href element
    hrefs = [link["href"] for link in links]

    # try find the date pair
    hrefs = [try_parse_href(href) for href in hrefs]

    # filter out the hrefs that weren't report links
    return [date_pair for date_pair in hrefs if date_pair]


def scrape_report_links(max_links=None, max_pages=None, start_index=1):
    base_url = "https://www.parliament.nz/en/pb/hansard-debates/rhr/" \
        + "?Criteria.page=HansardReports" \
        + "&Criteria.ParliamentNumber=-1"

    has_link_limit = isinstance(max_links, int)
    has_page_limit = isinstance(max_pages, int)

    # ensure both params aren't set
    if has_link_limit and has_page_limit:
        raise RuntimeError(
            "Only one of `max_links` or `max_pages` can be set at once"
        )

    report_dates = []

    i = start_index
    while True:
        # get the current page we're scraping
        request_url = f"{base_url}&Criteria.PageNumber={i}"
        response = request_report(request_url)

        # get number of pages scraped so far
        scraped_pages = i - start_index + 1

        # get the links from the page, if none, stop scraping
        scraped_links = extract_links(response[1])
        if not scraped_links:
            print(f"scraped {scraped_pages-1} pages in total")
            break

        # add all the links from the report
        report_dates += scraped_links

        # break early by user specified number of reports
        if has_link_limit and len(report_dates) >= max_links:
            print(f"scraped {i-1} page(s) in total")
            return report_dates[:max_links]

        # break early by user specified number of pages
        if has_page_limit and scraped_pages == max_pages:
            print(f"scraped {scraped_pages} pages in total")
            break

        # print progress
        if scraped_pages == 1:
            print(f"p{i}. scraped 1 page")
        elif not i % 10:
            print(f"p{i}. scraped {scraped_pages} pages")

        i += 1

    # return reports
    return report_dates
