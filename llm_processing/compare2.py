import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import re
import csv
import json
import time
import math
from llm_processing.edit_distance import WeightedLevenshtein

class TranscriptComparer:
    def __init__(self, transcript, edit_distance_config=None):
        self.transcript = transcript
        self.edit_distance_config = edit_distance_config

    def is_match(self, valA, valB):
        return valA.strip().lower() == valB.strip().lower() 

    def get_graded_match(self, valA, valB, is_a_match):
        wl = WeightedLevenshtein(self.edit_distance_config)
        if not is_a_match and (valA=="N/A" or valB=="N/A"):
            return 0
        return 1 - wl.calculate_weighted_difference(valA, valB, scaled=True)

    def tally(self, d: dict, use_graded_match=False):
        return sum([val if use_graded_match else math.floor(val) for val in d.values()]) 

    def compare_all_versions(self):
        print(f"compare_all_versions called")
        new_version_name, *old_version_names = self.transcript.versions["version name"][-2::-1]
        new_version_content, *old_version_contents = self.transcript.versions["content"][-2::-1]
        new_version_gen_info, *old_version_gen_infos = self.transcript.versions["generation info"][-2::-1]
        comparisons_dicts = []
        for old_version_name, old_version_content, old_version_gen_info in zip(old_version_names, old_version_contents, old_version_gen_infos):
            d = self.compare_versions(new_version_content, old_version_content, new_version_gen_info, old_version_gen_info)
            comparisons_dicts.append({"version name": old_version_name} | d)
        return comparisons_dicts    
                
    def compare_versions(self, versionA_content, versionB_content, versionA_gen_info, versionB_gen_info):
        created_by_typeA, created_by_typeB = versionA_gen_info["created by type"], versionB_gen_info["created by type"]
        alignment_type = [created_by_typeA, created_by_typeB]
        d = {}
        for fieldname in versionA_content:
            valA = versionA_content[fieldname]["value"]
            valB = versionB_content[fieldname]["value"]
            is_a_match = self.is_match(valA, valB) or self.get_graded_match(valA, valB, is_a_match=False)
            d[fieldname] = is_a_match
        num_matches = self.tally(d)
        alignment_rating = num_matches / len(versionA_content)
        return {"alignment rating": alignment_rating, "number matches": num_matches, "alignment type": alignment_type} | d    

if __name__ == "__main__":
    pass      
