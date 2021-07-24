import requests
import re
from bs4 import BeautifulSoup


def make_combined_link(date, date2=None):
    if date2 is None:
        date2 = date

    base_url = "https://www.parliament.nz/en/pb/hansard-debates/rhr/combined"
    date_string = f"{date}_{date2}"
    return f"{base_url}/HansD_{date_string}"


def make_document_link(hans_str, date_str):
    base_url = "https://www.parliament.nz/en/pb/hansard-debates/rhr/docuemnt"
    date_string = f"{hans_str}/{date_str}"
    return f"{base_url}/{date_string}"


def request_report(url, return_none_on_error=False):
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    }

    r = requests.get(url, headers=headers)

    # check for error response
    error_response = r.status_code != 200
    if error_response and return_none_on_error:
        return None
    elif error_response:
        print(url)
        raise RuntimeError("error response")

    data = r.text
    return url, BeautifulSoup(data, "html.parser")


def is_combined_format(tuple_part):
    return bool(re.findall(r"\d{8}", str(tuple_part)))



def request_report_from_tuple(part1, part2=None):
    link_func = make_combined_link
    tuple_type = "combined" if is_combined_format(part1) else "document"

    if tuple_type == "document":
        if part2 is None:
            raise RuntimeError(f"`{tuple_type}` requires `part2` to be set...")
        link_func = make_document_link

    report_url = link_func(part1, part2)
    return request_report(report_url)