from pprint import pprint


# properties the config needs
GLOBAL_START = "global_start"
VALID_TAGS = "valid_tags"
VALIDATION_GROUPS = "validation_groups"
END_ON = "end_on"
EOS_START = "eos_start"
IGNORE_START = "ignore_start"
OVERRIDE_GROUP = "override_group"

# global starters
BILL_DEBATE = "BillDebate"
Q_AND_A = "QAndA"
BEGINNING_OF_DAY = "BeginningOfDay"

# local starters
CONT_SPEECH = "ContSpeech"
DEBATE = "Debate"
DEBATE_ALONE = "Debatealone"
EOS = "EOS"
MARGIN = "Margin"
MARGIN_NEXT = "MarginNext"
INTERJECTION = "Interjection"
QUESTION = "Question"
ANSWER = "Answer"
QA_END = "QandAEnd"
VOTE = "Vote"
NOTE = "Note"
SPEECH = "Speech"
FLAG = "Flag"
ENDING = "Ending"
LIST = "List"

TAG_LOOKUP = {
    BEGINNING_OF_DAY: ["BeginningOfDay"],
    SPEECH: ["Speech"],
    CONT_SPEECH: ["a", "ContinueSpeech", "list"],
    LIST: ["ul", "List"],
    BILL_DEBATE: ["BillDebate"],
    DEBATE: ["Debate", "SubDebate", "DebateDebate"],
    DEBATE_ALONE: ["Debatealone"],
    EOS: ["EndOfSection"],
    MARGIN: ["MarginHeading", "IndentMarginalone", "IndentMargin"],
    MARGIN_NEXT: ["IndentMarginTextFollowing"],
    INTERJECTION: ["Interjection", "Intervention", "Urgency"],
    Q_AND_A: ["QOA"],
    QUESTION: ["QType", "QTypealone", "SubsQuestion", "SupQuestion"],
    ANSWER: ["SubsAnswer", "SupAnswer"],
    QA_END: ["QOAEnd"],
    VOTE: ["VoteReason", "VoteCount", "VoteResult", "VoteText"],
    NOTE: ["note"],
    FLAG: ["Incorporation", "Default", "ClauseAlone"],
    ENDING: ["CentredEndingBold", "CentredEndingItalics"],
    EOS: ["EndOfSection"],
}


TAG_LOOKUP_FLAT = { t: k for k, tags in TAG_LOOKUP.items() for t in tags }


CLASS_ORDER = {
    BILL_DEBATE: {
        GLOBAL_START: True,
        VALID_TAGS: [
            DEBATE, SPEECH, CONT_SPEECH, INTERJECTION, VOTE, DEBATE_ALONE],
        OVERRIDE_GROUP: [DEBATE],
    },
    BEGINNING_OF_DAY: {
        GLOBAL_START: True
    },
    DEBATE: {
        EOS_START: True,
        IGNORE_START: [BILL_DEBATE],
        VALID_TAGS: [
            BILL_DEBATE, DEBATE, SPEECH, CONT_SPEECH,
            INTERJECTION, NOTE, VOTE, DEBATE_ALONE
        ],
    },
    DEBATE_ALONE: {
        EOS_START: True,
    },
    Q_AND_A: {
        GLOBAL_START: True,
        OVERRIDE_GROUP: [QUESTION],
        VALID_TAGS: [QUESTION, SPEECH, CONT_SPEECH, INTERJECTION],
        END_ON: [QA_END],
    },
    QUESTION: {
        GLOBAL_START: True,
        IGNORE_START: [Q_AND_A],
        VALID_TAGS: [Q_AND_A, QUESTION, SPEECH, CONT_SPEECH, INTERJECTION],
        END_ON: [QA_END],
    },
    MARGIN: {
        EOS_START: True,
        OVERRIDE_GROUP: [MARGIN_NEXT],
    },
    MARGIN_NEXT: {
        EOS_START: True
    },
    SPEECH: {
        EOS_START: False,
        IGNORE_START: [BILL_DEBATE],
        VALID_TAGS: [SPEECH, CONT_SPEECH],
    },
    ENDING: {
        EOS_START: True
    }
}


class State():
    def __init__(self, starting_tag, ignore_validation=False):
        tag_group = self._lookup_tag_type(starting_tag)

        self._tag_raw = starting_tag
        self.group = tag_group
        self.current = tag_group
        self.group_config = CLASS_ORDER.get(tag_group, {})
        self.was_eos = False
        self.end_next = False
        self.previous = None
        self.validate = not ignore_validation


    def get_state(self):
        return {
            "group": self.group,
            "current": self.current,
            "raw_tag": self._tag_raw,
            "previous": self.previous,
            "was_eos": self.was_eos,
            "config": self.group_config,
            "ignore_validation": not self.validate,
        }


    def print_state(self):
        pprint(
            f"Current Group: {self.group}" +
            f"    Current Tag: {self.current}" +
            f"    Previous Tag: {self.previous}" +
            f"    Was EOS: {self.was_eos}"
        )


    def _lookup_tag_type(self, tag_name):
        tag_class = TAG_LOOKUP_FLAT.get(tag_name,)
        if tag_class is None:
            print(f"Coudnt find: `{tag_name}`, returning Note")
            tag_class = NOTE

        return tag_class


    def _eval_group_property(self, new_group, config_property, config=None):
        if config is None:
            config = self.group_config
        config_property = config.get(config_property, [])
        return config_property and new_group in config_property


    def _is_new_state(self, new_conf):
        global_start = new_conf.get(GLOBAL_START, False)
        eos_start = new_conf.get(EOS_START, False) and self.was_eos
        ignore_start = self.group in new_conf.get(IGNORE_START, [])

        return not ignore_start and (global_start or eos_start)


    def update_state(self, next_tag):
        new_group = self._lookup_tag_type(next_tag)

        if new_group == EOS:
            self.was_eos = True
            return False

        if self._eval_group_property(new_group, VALID_TAGS) and self.validate:
            self.print_state()
            raise RuntimeError(
                f"Unallowed tag: `{new_group}` for group: `{self.group}`")

        new_conf = CLASS_ORDER.get(new_group, {})

        # happen regardless
        self._tag_raw = next_tag
        self.previous = self.current
        self.current = new_group

        state_change = self._is_new_state(new_conf) or self.end_next

        # start state here
        if state_change:
            self.group = new_group
            self.group_config = new_conf

        if not self.end_next:
            self.end_next = self._eval_group_property(new_group, END_ON)
        else:
            self.end_next = False

        self.was_eos = False
        return state_change


def lookup_tag_type(tag):
    tag_name = tag.name
    if tag_name != "ul":
        tag_name = tag["class"]

    if isinstance(tag_name, list):
        tag_name = tag_name[0]

    return TAG_LOOKUP_FLAT.get(tag_name, NOTE)


def parse_tag_structure(html_tags):
    curr_state = State(html_tags[0], ignore_validation=True)
    curr_state.print_state()

    new_groupings = []
    curr_grouping = []
    for i, next_tag in enumerate(html_tags[1:]):
        if curr_state.update_state(next_tag):
            new_groupings.append(curr_grouping)
            curr_grouping = []
        curr_grouping.append(next_tag)

    return(new_groupings)
