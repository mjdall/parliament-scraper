import os
import re
import json
import unicodedata


def save_json(json_structure, outfilename):
    _, file_extension = os.path.splitext(outfilename)

    if not file_extension:
        outfilename += ".json"

    if os.path.exists(outfilename):
        os.remove(outfilename)

    if isinstance(json_structure, set):
        json_structure = list(json_structure)

    with open(outfilename, "w", encoding="utf-8") as f:
        json.dump(json_structure, f, indent=2, sort_keys=True)


def load_json(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError(f"could not find: `{filename}`...")

    loaded_json = None
    with open(filename, "r", encoding="utf-8") as f:
        loaded_json = json.load(f)
    
    return loaded_json


def remove_accents(input_str):
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


def update_dict(a, b):
    if all([key not in a for key in b]):
        a.update(b)
        return(a)

    for bkey, val in b.items():
        if bkey not in a:
            a[bkey] = val
            continue
        
        if val == a[bkey]:
            continue
        
        if not isinstance(a[bkey], list):
            a[bkey] = [a[bkey]]
        
        a[bkey].append(val)

    return a


def name_attr_is_time(name_attr):
    return bool(re.search(r"time_\d{8} ?\d{2}:\d{2}:\d{2}", name_attr))


def parse_time_attr(time_attr):
    if not name_attr_is_time(time_attr):
        raise RuntimeError("`time_attr` does not look like time.")

    # extract groups and validate length
    time_re = re.findall(r"time_(\d{8}) ?(\d{2}:\d{2}:\d{2})", time_attr)
    if not time_re or len(time_re[0]) != 2:
        raise RuntimeError("Couldnt parse time string...")
    
    # extract date and time parts
    date_part = time_re[0][0]
    time_string = time_re[0][1]

    date_string = f"{date_part[6:]}/{date_part[4:6]}/{date_part[:4]}"
    return { "date": date_string, "time": time_string }
