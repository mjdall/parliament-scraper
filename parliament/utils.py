import os
import json


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
