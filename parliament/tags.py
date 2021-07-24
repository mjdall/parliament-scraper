from parliament.report_requests import request_report_from_tuple


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


def extract_group_order(tag_names, group_order=dict()):
    start_tags = [section[0] for section in tag_names]
    n_tags = len(start_tags)

    for i, tag in enumerate(start_tags):
        if i + 1 == n_tags:
            break

        group_order.setdefault(tag, {"first": {}, "second": {}})

        # find what tags come after this current one
        next_tag = start_tags[i+1]
        next_next = next_tag
        next_count = 0
        j = i+1
        while j < n_tags and next_next == next_tag:
            next_next = start_tags[j]
            if next_tag == next_next:
                next_count += 1
            j += 1

        # increment counts
        group_order[tag]["first"].setdefault(
            next_tag,
            {
                "count": 0,
                "consequetive": []
            })
        group_order[tag]["second"].setdefault(next_next, 0)

        # increment counts
        group_order[tag]["first"][next_tag]["count"] += 1
        group_order[tag]["first"][next_tag]["consequetive"].append(next_count)
        group_order[tag]["second"][next_next] += 1
    return group_order


def extract_tag_counts(flat_tags,
                       start_tags=dict(), 
                       unique_tags=dict(),
                       tag_counts=dict()):

    add_to_start_tag = True

    for tag in flat_tags:
        if add_to_start_tag and tag != "Ending":
            start_tags.setdefault(tag, 0)
            start_tags[tag] += 1
            add_to_start_tag = False

        elif tag in ["Ending", "EndOfSection"]:
            add_to_start_tag = True
            continue

        # add tag to unique tag list
        unique_tags.add(tag)

        # add to counter
        tag_counts.setdefault(tag, 0)
        tag_counts[tag] += 1

    return start_tags, unique_tags, tag_counts


def find_tag_structure(report_tuples):
    start_tags = dict()
    unique_tags = set()
    tag_counts = dict()
    group_order = dict()

    for report_tuple in report_tuples:
        if isinstance(report_tuple, tuple):
            results = initial_parse(report_tuple[0], report_tuple[1])
        else:
            results = initial_parse(report_tuple)

        extract_tag_counts(results[3], start_tags, unique_tags, tag_counts)
        extract_group_order(results[2], group_order)

    return start_tags, unique_tags, tag_counts, group_order
