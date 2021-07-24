import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..")) 

from parliament.link_crawler import scrape_report_links
from parliament.tags import find_tag_structure
from parliament.utils import save_json


all_report_links = scrape_report_links()
save_json(all_report_links, "output/meta/all_report_links.json")
print(f"scraped {len(all_report_links)} in total")


print("finding tag structure on last 50 reports...")
tag_structure = find_tag_structure(all_report_links[:100])
start_tags, unique_tags, tag_counts, group_order = tag_structure

save_json(start_tags, "output/meta/starter_tags.json")
save_json(unique_tags, "output/meta/unique_tags.json")
save_json(tag_counts, "output/meta/tag_counts.json")
save_json(group_order, "output/meta/tag_order.json")

print("meta data saved to output/meta/")
