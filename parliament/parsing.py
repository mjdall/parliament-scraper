import re
from parliament.utils import remove_accents


def parse_list_tag(tag):
    return "\n".join(["*\t" + li.get_text() for li in tag.find_all("li")])


def has_speaker(tag_text):
    # regex is a tad greedy but should be ok for now (hint: not ok)
    regexp = re.compile(r"(\(.+\))?:")
    return bool(regexp.search(tag_text))


def get_speaker(tag_text):
    # 100 char limit on how early a : can appear
    if not has_speaker(tag_text[:100]):
        return None, tag_text

    # split on : for speaker
    speaker_index = tag_text.index(":")

    speaker = tag_text[:speaker_index].strip()
    text = tag_text[speaker_index+1:].strip()
    return speaker, text


def parse_regular_tag(tag_text):
    speaker, tag_text = get_speaker(tag_text)

    result_dict = { "text": tag_text }
    if speaker is not None:
        result_dict["speaker"] = speaker
    
    return result_dict


def parse_tag_text(tag):
    tag_text = tag.get_text()
    if tag.name == "ul":
        results_dict = { "text": parse_list_tag(tag) }
    else:
        results_dict = parse_regular_tag(tag_text)
    results_dict["text"] = remove_accents(results_dict["text"]).strip()

    return results_dict
