## scrape.py 
## has hardcode url endpoint 

import sys
import os
import re
import requests
import json

from bs4 import BeautifulSoup
from pprint import pprint
import unicodedata


def flatten(tag):
    content = ""
    for l in tag:
        if l.string == None:
            content = flatten(l)
        else:
            content = content + l.string
    return content.strip()


def has_speaker(tag_text):
    # regex is a tad greedy but should be ok for now
    regexp = re.compile(r"(\(.+\))?:")
    return bool(regexp.search(tag_text))


def find_speech_start_and_end(sections):
    start = None
    end = None
    for i, section in enumerate(sections):
        if section.name == "ul":
            continue
        par_class = section["class"][0]
        
        if start is None and par_class == "Speech":
            start = i
        
        if end is None and par_class == "VoteReason":
            end = i

    return start, end


def remove_accents(input_str):
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


def parse_vote_text(flat_para):
    decoded = remove_accents(flat_para)
    party_regex = re.compile(r"((\b\w{2,}\b *){1,})(?= \d+)")
    vote_counts_regex = re.compile(r"(\d+)")
    vote_counts = vote_counts_regex.findall(flat_para)
    parties = party_regex.findall(decoded)

    if not isinstance(parties, list):
        raise RuntimeError(f"Could not parse vote counts: {decoded}")

    matched_groups = {}
    for party, vote_count in zip(parties, vote_counts):
        curr_party = party
        if isinstance(party, tuple):
            curr_party = party[0]

        matched_groups[curr_party] = vote_count

    return(matched_groups)



def parse_vote_section(section):
    vote_results = []

    vote_result = None
    vote_type = None
    for paragraph in section:
        par_class = paragraph["class"][0]
        flat_para = flatten(paragraph)

        if par_class == "VoteReason":
            if vote_result is not None:
                vote_results.append(vote_result)
            vote_result = {
                "class": "Vote",
                "votes": { },
                "additional_notes": [],
            }
            vote_result["text"] = flat_para

        elif par_class == "VoteCount":
            vote_regex = re.compile(r"(?<=(Ayes|Noes) )\d+")
            vote_class = "yes" if "yes" in flat_para else "no"
            vote_type = vote_class
            vote_result[vote_class] = int(vote_regex.search(flat_para).group(0))

        elif par_class == "VoteText":
            if vote_type is None:
                raise RuntimeError("Vote type not found yet")

            party_votes = parse_vote_text(flat_para)
            for party in party_votes:
                if party in vote_result["votes"]:
                    raise RuntimeError("Duplicate vote count")
                vote_result["votes"].setdefault(vote_type, dict())
                vote_result["votes"][vote_type][party] = party_votes[party]
        
        elif par_class == "VoteResult":
            vote_result["result"] = flat_para

        elif par_class == "a":
            vote_result["additional_notes"].append(flat_para)

        else:
            pprint(paragraph)
            raise RuntimeError(f"Unhandled tag in vote parsing: {par_class}")

    return vote_results


def parse_bill_or_debate(section):
    output = []
    speech_start, vote_start = find_speech_start_and_end(section)

    if speech_start is None:
        raise RuntimeError("No Speech start in bill or debate")

    tag_mapping = { "SubDebate": "subtitle", "IndentMargin": "note" }
    section_meta = {}

    for paragraph in section[:speech_start]:
        par_class = paragraph["class"][0]

        if par_class in ["BillDebate", "Debate"]:
            section_meta["class"] = par_class
            continue

        if par_class not in tag_mapping:
            pprint(paragraph)
            raise RuntimeError(f"Unhandeled class: {par_class}")

        section_meta[tag_mapping[par_class]] = flatten(paragraph)
    output.append(section_meta)

    has_vote = vote_start is not None

    # check if vote is present, get the relevant subset
    if has_vote:
        speaking_section = section[speech_start:vote_start]
    else:
        speaking_section = section[speech_start:]

    output += parse_speaking_section(speaking_section)

    # parse vote section
    if has_vote:
        output.append(parse_vote_section(section[vote_start:]))

    return output


def parse_speaking(tag, is_note=False):
    tag_class = tag["class"][0]
    out_dict = dict()
    tag_text = flatten(tag)

    # gets time component from tag
    if tag.a is not None:
        time_str = tag.a["name"]
        time_split = time_str.index("_") + 1
        out_dict["time"] = time_str[time_split:].strip()

    # parses speaker
    if (tag_class in [
            "Speech", "SupAnswer", "SubsAnswer", "ContinueSpeech",
            "SupQuestion", "SubsQuestion", "Interjection", "ContinuedAnswer"]
        and has_speaker(tag_text)):
        speaker_index = tag_text.index(":")
        out_dict["speaker"] = tag_text[:speaker_index].strip()

        out_class = (tag_class if tag_class
            in ["Interjection", "ContinueSpeech"] else "Speech")

        out_dict["class"] = out_class
        tag_text = tag_text[speaker_index+1:].strip()

    out_dict["text"] = tag_text

    if is_note:
        out_dict["class"] = "MeetingNote"

    return out_dict


def parse_list(tag):
    return "\n".join(["*\t" + flatten(li) for li in tag.find_all("li")])


def parse_speaking_section(section):
    output = []
    grouped_section = None
    current_speech = False
    for paragraph in section:
        # appending to previous speaker
        if (
            paragraph.name == "ul"
            or (paragraph["class"][0] == "a" and current_speech)):
            # whether to parse a list or an a tag
            if paragraph.name == "ul":
                append_text = parse_list(paragraph)
            else:
                append_text = flatten(paragraph)

            # get the previous node to append to
            if grouped_section is None:
                append_node = output[-1]
            else:
                append_node = grouped_section["speeches"][-1]

            # whether to concat a newline character to the end of the text
            if append_node["text"] and append_node["text"][-2:] != "\n":
                append_text = "\n" + append_text

            # append the previous node
            append_node["text"] += append_text

            continue

        par_class = paragraph["class"][0]
        out_tag = None

        if (grouped_section is not None
            and par_class not in ["a", "Speech", "SubDebate"]):
            output.append(grouped_section)
            grouped_section = None

        if par_class in [
            "Speech", "a", "SubDebate",
            "Interjection", "ContinueSpeech", "CentredEndingBold"]:
            out_tag = parse_speaking(
                paragraph,
                is_note=par_class not in [
                    "Speech",
                    "Interjection",
                    "ContinueSpeech"
                ]
            )

        elif par_class == "Debatealone":
            grouped_section = {
                "title": flatten(paragraph),
                "speeches": [],
                "class": "GroupedSection",
            }
            continue

        elif par_class in "IndentMarginalone":
            continue

        current_speech = par_class == "Speech"

        if out_tag is None:
            print("UNHANDLED:")
            print(par_class)
            print(paragraph)
            print()
            continue

        if grouped_section is None:
            output.append(out_tag)
        else:
            grouped_section["speeches"].append(out_tag)

    if grouped_section is not None:
        output.append(grouped_section)

    return output


def parse_directed_question(tag):
    flat_tag = flatten(tag)

    qno_i = flat_tag.index(".")
    from_i = flat_tag.index(")")
    to_i = flat_tag.index(":")

    return {
        "class": "MainQuestion",
        "question_no": flat_tag[:qno_i],
        "from": flat_tag[qno_i+1:from_i+1].strip(),
        "to": flat_tag[from_i+1:to_i][7:].strip(),
        "question": flat_tag[to_i+1:].strip(),
        "responses": [],
        "additional_notes": [],
    }


def parse_support_question(tag):
    speaking = parse_speaking(tag)
    speaking["class"] = "SupportQuestion"
    speaking["question"] = speaking["text"]
    del speaking["text"]
    speaking["responses"] = []
    speaking["additional_notes"] = []
    return speaking


def parse_answer(tag, tag_class):
    speaking = parse_speaking(tag)

    outclass = "Answer"
    if tag_class == "Interjection":
        outclass = tag_class
    elif tag_class == "ContinueSpeech":
        outclass = "ContinuedAnswer"

    speaking["class"] = outclass
    return speaking


def parse_question_section(section):
    start_ended = False
    grouped_section = None
    output = []
    for paragraph in section:
        if paragraph.name == "ul":
            raise RuntimeError("list in question section")

        par_class = paragraph["class"][0]

        start_ended = (start_ended
            or par_class not in ["QOA", "QType", "Speech", "a"])

        if (grouped_section is not None
            and par_class not in [
                "a", "Speech", "SubsAnswer", "SupAnswer",
                "Interjection", "ContinueSpeech"]
            and start_ended):
            output.append(grouped_section)
            grouped_section = None

        if par_class == "QOA":
            grouped_section = {
                "class": "QAStart",
                "title": flatten(paragraph),
                "subtitle": "",
                "speeches": [],
                "additional_notes": [],
            }

        elif par_class == "QType":
            if grouped_section is None:
                raise RuntimeError("QType with no grouped section")
            grouped_section["subtitle"] = flatten(paragraph)

        elif par_class == "Speech" and not start_ended:
            if grouped_section is None:
                raise RuntimeError("Speech with no grouped section in question")
            grouped_section["speeches"].append(parse_speaking(paragraph))

        elif par_class == "SubsQuestion":
            grouped_section = parse_directed_question(paragraph)

        elif par_class == "SupQuestion":
            if grouped_section is not None:
                raise RuntimeError("group section not cleared")
            grouped_section = parse_support_question(paragraph)

        elif par_class in [
            "SubsAnswer", "SupAnswer", "Interjection", "ContinueSpeech"]:
            if grouped_section is None:
                # todo: fix for answer section showing up
                raise RuntimeError(f"{par_class} with no grouped section")
            answer = parse_answer(paragraph, par_class)
            grouped_section["responses"].append(answer)

        elif par_class == "QOAEnd":
            continue

        else:
            if grouped_section is not None:
                grouped_section["additional_notes"].append(
                    parse_speaking(paragraph))

    return output 


def find_bill_or_debate_end(sections_from_bill_start, start_index):
    start_section = sections_from_bill_start[0][0]["class"][0]

    section_classes = [
        [p["class"][0] for p in section]
        for section in sections_from_bill_start
    ]

    for i, section in enumerate(section_classes):
        section_start = section[0]

        if ("CentredEndingBold" in set(section)
            or section_start not in [start_section, "Speech", "VoteReason"]):
            return start_index + i

    return None


def re_order_sections(all_sections):
    reordered = []
    index = 0
    while index < len(all_sections):
        section = all_sections[index]
        section_start = section[0]["class"][0]

        if section_start in ["BillDebate", "Debate"]:
            section_end = find_bill_or_debate_end(
                all_sections[index:],
                start_index=index)

            debate_sections = all_sections[index:section_end]

            # flatten to one level
            reordered.append([i for s in debate_sections for i in s])
            index = section_end
            continue

        reordered.append(section)
        index += 1

    return(reordered)


def scrape_hansard_report(date, date2=None):
    if date2 is None:
        date2 = date

    base_url = "https://www.parliament.nz/en/pb/hansard-debates/rhr/combined"
    date_string = f"{date}_{date2}"
    url = f"{base_url}/HansD_{date_string}"

    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    }

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return

    data = r.text
    soup = BeautifulSoup(data, "html.parser")
    
    preface = dict()
    preface["link"] = url
    preface["title"] = flatten(soup.title)

    output = []
    debate_tags = [
        b2.find_all(["p", "ul"]) for b in soup.find_all("body")
        for b2 in b.find_all("body")
    ]

    debate_tags = re_order_sections(debate_tags)

    for section in debate_tags:
        if not section:
            continue

        section_start = section[0]["class"][0]

        if section_start == "BeginningOfDay":
            preface["date"] = flatten(section[0])
            if len(section) > 1:
                output.append(parse_speaking_section(section[1:]))
        elif section_start in ["QOA", "SubsQuestion"]:
            output.append(parse_question_section(section))
        elif section_start in ["BillDebate", "Debate"]:
            output.append(parse_bill_or_debate(section))
        elif section_start in ["Debatealone", "Speech"]:
            output.append(parse_speaking_section(section))
        else:
            raise RuntimeError(f"Unhandeled section: {section_start}")

    # insert preface to the start
    output.insert(0, preface)

    outfilename = f"debate_{date_string}.json"
    if os.path.exists(outfilename):
        os.remove(outfilename)

    with open(outfilename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        date = sys.argv[1]
        date2 = None
        if len(sys.argv) > 2:
            date2 = sys.argv[2]
        scrape_hansard_report(date, date2)
    else:
        print('[*] usage: python scraper.py "DATE" "<Optional Second Date>"')
        print('[*]   e.g: python scraper.py 20170726')
        print('[*]   e.g: python scraper.py 20210707 20210708')

# python parliament.py 20210708 - working
# python parliament.py 20210707 20210708 - not working
#   need to handle not strictly defined section starts
