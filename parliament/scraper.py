import re
from pprint import pprint

from parliament.tags import parse_tags_to_dict
from parliament.structure import BILL_DEBATE, State, INTERJECTION, QUESTION, ANSWER, CONT_SPEECH, SPEECH, NOTE, LIST, VOTE, DEBATE, MARGIN


def parse_speaker_brackets(speaker_text):
    return_dict = {}
    speaker_subtext = re.findall(r"(.*?) ?(\(.+\))", speaker_text)
    if not speaker_subtext:
        return_dict["speaker"] = speaker_text
    else:
        return_dict["speaker"] = speaker_subtext[0][0]
        speaker_subtitle = speaker_subtext[0][1]
        speaker_subtitle = re.sub(r"(\(|\))", "", speaker_subtitle)
        return_dict["speaker_subtitle"] = speaker_subtitle
    return return_dict


def split_speaker_subtext(parsed_tags):
    for section in parsed_tags:
        for tag in section:
            tag_speaker = tag.get("speaker", )
            if tag_speaker is None:
                continue
            tag.update(parse_speaker_brackets(tag_speaker))
    return parsed_tags


def fill_speaker(parsed_tags):
    for section in parsed_tags:
        current_speaker = ""
        current_subtitle = ""
        for tag in section:
            # skip interjection
            tag_id = tag.get("tag_id",)
            if tag_id == INTERJECTION:
                continue

            # if the tag has speaker, 
            tag_speaker = tag.get("speaker",)
            if tag_speaker is not None:
                current_speaker = tag_speaker
                current_subtitle = tag.get("speaker_subtitle", "")
                continue

            if tag_id in [SPEECH, CONT_SPEECH] and current_speaker:
                tag["speaker"] = current_speaker
                tag["speaker_subtitle"] = current_subtitle
                tag["filled_speaker"] = True

    return parsed_tags


def concat_list_tags(parsed_tags):
    for i, section in enumerate(parsed_tags):
        if not any([tag["class"] == LIST for tag in section]):
            continue
        reconstructed = []
        prev = section[0]
        for tag in section[1:]:
            if tag["class"] == LIST:
                prev["text"] += tag["text"]
                continue
            reconstructed.append(tag)
            prev = tag
        parsed_tags[i] = reconstructed
    return parsed_tags


def parse_qa_speaker(speaker_text):
    question_no = re.findall(r"(\d+)\. ?(.*)", speaker_text)
    return_dict = { "speaker": speaker_text }
    if question_no:
        return_dict
        return_dict["speaker"] = question_no[0][1]
        return_dict["question_no"] = question_no[0][0]
    return return_dict


# bit messy will need to refactor at some point
def q_and_a_grouper(parsed_tags):
    for i, section in enumerate(parsed_tags):
        if not any([tag["tag_id"] in [QUESTION, ANSWER] for tag in section]):
            continue

        current_question_group = {}
        current_sup_question = {}
        restructured = []
        for _, tag in enumerate(section):
            tag_id = tag.get("tag_id", )
            tag_class = tag.get("class", )

            not_follow_on = tag_id not in [
                QUESTION,
                ANSWER,
                INTERJECTION,
                CONT_SPEECH,
                SPEECH,
                NOTE,
                MARGIN]

            # adding in current support answer
            if (current_sup_question
                and not (tag_class == "SupAnswer"
                or tag_id in [INTERJECTION, SPEECH, CONT_SPEECH, NOTE])):
                current_question_group["follow_up_questions"].append(
                    current_sup_question
                )
                current_sup_question = {}

            # not QA tag
            if not_follow_on:
                if current_question_group:
                    restructured.append(current_question_group)
                current_question_group = {}
                restructured.append(tag)
                continue

            if tag_class == "SubsQuestion":
                if current_question_group:
                    restructured.append(current_question_group)
                current_question_group = {
                    "main_question": tag["text"],
                    "main_answer": [],
                    "follow_up_questions": [],
                }
                del tag["text"]

                tag_speaker = tag.get("speaker",)
                if tag_speaker is not None:
                    tag.update(parse_qa_speaker(tag_speaker))
                current_question_group.update(tag)

            elif tag_class == "SubsAnswer":
                current_question_group["main_answer"].append(tag)

            elif tag_class == "SupQuestion":
                if current_sup_question:
                    if current_question_group:
                        current_question_group["follow_up_questions"].append(
                        current_sup_question)
                tag["question"] = tag["text"]
                del tag["text"]
                current_sup_question = tag
                current_sup_question["answers"] = []

            elif tag_class == "SupAnswer":
                if "answers" not in current_sup_question:
                    print("error in parsing, no `answers` field...")

                current_sup_question.setdefault("answers", [])
                current_sup_question["answers"].append(tag)

            else:
                if current_sup_question:
                    current_sup_question["answers"].append(tag)
                elif current_question_group:
                    current_question_group["main_answer"].append(tag)
                else:
                    restructured.append(tag)

        if current_sup_question:
            current_question_group["follow_up_questions"].append(
                current_sup_question)

        if current_question_group:
            restructured.append(current_question_group)

        parsed_tags[i] = restructured
    return parsed_tags


def get_debate_priority(tag_class):
    mapping = {
        "BillDebate": 4,
        "Debate": 3,
        "SubDebate": 2,
        "Debatealone": 1,
    }

    return mapping.get(tag_class, -1)


def bill_debate_grouper(parsed_tags):
    for i, section in enumerate(parsed_tags):
        if not any([tag["tag_id"] == DEBATE for tag in section]):
            continue

        bill_debates = []
        parent_debate = {}
        child_debate = {}
        current_priority = 0
        for _, tag in enumerate(section):
            tag_class = tag["class"]
            tag_id = tag["tag_id"]
            is_debate_tag = "debate" in tag_class.lower()
            if not is_debate_tag and not parent_debate:
                bill_debates.append(tag)
                continue

            if is_debate_tag:
                tag["title"] = tag["text"]
                del tag["text"]

            tag_priority = get_debate_priority(tag_class)
            if tag_priority >= current_priority:
                if child_debate:
                    parent_debate["debates"].append(child_debate)
                if parent_debate:
                    bill_debates.append(parent_debate)

                current_priority = tag_priority
                child_debate = {}
                parent_debate = {}
                parent_debate.update(tag)
                parent_debate["debates"] = []

            elif tag_class in ["Debate", "SubDebate"]:
                if child_debate:
                    parent_debate["debates"].append(child_debate)
                    child_debate = {}

                child_debate.update(tag)
                child_debate["speeches"] = []

            elif tag_id == VOTE:
                parent_debate.setdefault("voting", [])
                parent_debate["voting"].append(tag)
                # todo: end bill debate at end of voting

            elif child_debate:
                assert tag_id != BILL_DEBATE
                child_debate["speeches"].append(tag)

            else:
                assert tag_id != BILL_DEBATE
                parent_debate["debates"].append(tag)

        # append to the end
        # TODO: FIX THIS APPENDING EMPTY
        if child_debate:
            parent_debate["debates"].append(child_debate)
        if parent_debate:
            bill_debates.append(parent_debate)

        parsed_tags[i] = bill_debates

    return parsed_tags



def parse_all_html(html_tags):
    flat_parsed_tags = []

    for section in html_tags:
        if not section:
            continue
        parsed_section = parse_tags_to_dict(section, return_bs4_tag=True)
        parsed_section.append({ "class": "EndOfSection" })
        flat_parsed_tags += parsed_section

    tag_classes = [tag.get("class", "note") for tag in flat_parsed_tags]
    curr_state = State(tag_classes[0], ignore_validation=True)

    resturctured_tags = []
    curr_grouping = [flat_parsed_tags[0]]
    for next_tag, parsed_tag in zip(tag_classes[1:], flat_parsed_tags[1:]):
        if curr_state.update_state(next_tag):
            resturctured_tags.append(curr_grouping)
            curr_grouping = []

        if parsed_tag.get("class", "EndOfSection") == "EndOfSection":
            continue

        curr_grouping.append(parsed_tag)

    list_concat = concat_list_tags(resturctured_tags)
    speakers_filled = fill_speaker(list_concat)
    for section in speakers_filled:
        for tag in section:
            if "raw_tag" in tag:
                del tag["raw_tag"]
    speakers_split = split_speaker_subtext(speakers_filled)
    q_and_a_grouped = q_and_a_grouper(speakers_split)
    bill_debate_grouped = bill_debate_grouper(q_and_a_grouped)

    return bill_debate_grouped
