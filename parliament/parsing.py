import re
import numpy as np
from parliament.utils import remove_accents


def parse_list_tag(tag):
    return "\n".join(["*\t" + li.get_text() for li in tag.find_all("li")])


def count_uppercase_words(tag_text, return_perc = True):
    if not tag_text:
        return 0

    word_starts = re.findall(r"(?<=\s).", tag_text) + [tag_text[0]]
    n_uppercase = np.array([w.isupper() for w in word_starts]).sum()

    if return_perc:
        n_uppercase = n_uppercase / len(word_starts)

    return n_uppercase


def has_speaker(tag_text):
    if ":" not in tag_text:
        return False

    colon_split = tag_text.index(":")
    tag_text = tag_text[:colon_split].strip()

    n_spaces = len(re.findall(r"\s", tag_text))
    n_uppercase = count_uppercase_words(tag_text)

    return not (n_spaces > 4 and n_uppercase < .75)


def get_speaker(tag_text):
    # 100 char limit on how early a : can appear
    if not has_speaker(tag_text[:100]):
        return None, tag_text

    # split on : for speaker
    speaker_index = tag_text.index(":")

    speaker = tag_text[:speaker_index].strip()
    text = tag_text[speaker_index+1:].strip()
    return speaker.title(), text


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
