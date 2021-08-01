import functools
from bs4 import element

from parliament.report_requests import request_report_from_tuple
from parliament.utils import name_attr_is_time, parse_time_attr, update_dict
from parliament.parsing import parse_tag_text
from parliament.structure import lookup_tag_type


def flatten(tag) -> str:
    content = ""
    for l in tag:
        if l.string == None:
            content = flatten(l)
        else:
            content = content + l.string
    return content.strip()


def make_preface(url, soup) -> dict:
    preface = dict()
    preface["link"] = url
    preface["title"] = flatten(soup.title)
    return preface


def get_tag_id(tag) -> str:
    if tag.name == "ul":
        return "list"
    
    tag_class = tag.get("class", None)
    if tag_class is None :
        return "note"

    return tag_class[0]


def get_tags_from_soup(soup):
    all_tags = [
        b2.find_all(["p", "ul"]) for b in soup.find_all("body")
        for b2 in b.find_all("body")
    ]

    tag_names = [
        [get_tag_id(tag) for tag in section] for section in all_tags
    ]


    for i, _ in enumerate(tag_names):
        tag_names[i].append("EndOfSection")
    
    tag_names[-1].insert(0, "Ending")
    tag_names_flat = [tag for group in tag_names for tag in group]

    return all_tags, tag_names, tag_names_flat


def initial_parse(part1, part2=None):
    url, soup = request_report_from_tuple(part1, part2)
    preface = make_preface(url, soup)
    html_tags, tag_names, tag_names_flat = get_tags_from_soup(soup)

    return preface, html_tags, tag_names, tag_names_flat


def get_tag_as_dict(bs4_tag):
    parent_attr = [bs4_tag.attrs.copy()]
    children_attr = [
        child_tag.attrs.copy() for child_tag in bs4_tag.children
        if isinstance(child_tag, element.Tag)
    ]
    children_attr = parent_attr + children_attr
    children_attr = [a for a in children_attr if a]

    if children_attr is None or not children_attr:
        return {}

    return functools.reduce(update_dict, children_attr)


def parse_tags_to_dict(html_tags, return_bs4_tag=False):
    if not isinstance(html_tags, list):
        raise RuntimeError("html tags needs to be a list of bs4 tags...")

    if isinstance(html_tags[0], list):
        html_tags = [tag for section in html_tags for tag in section]

    parsed_tags = []
    for tag in html_tags:
        tag_dict = get_tag_as_dict(tag)
        tag_dict.update(parse_tag_text(tag))

        if tag.name == "ul":
            tag_dict["class"] = "List"

        for key, val in tag_dict.items():
            if isinstance(val, list) and len(val) == 1: 
                tag_dict[key] = val[0]

        # check if name is actually time stamp
        name_part = tag_dict.get("name", "")
        if name_attr_is_time(name_part):
            tag_dict.update(parse_time_attr(name_part))
            del tag_dict["name"]

        tag_dict["tag_id"] = lookup_tag_type(tag)

        if return_bs4_tag:
            tag_dict["raw_tag"] = tag

        parsed_tags.append(tag_dict)

    return parsed_tags
