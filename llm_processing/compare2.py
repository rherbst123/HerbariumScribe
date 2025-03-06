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
        new_version = self.transcript.versions[0]
        old_versions = self.transcript.versions[1:]
        d = {}
        for old_version in old_versions:
            old_version_name = old_version["new version name"]
            d[f"compared to {old_version_name}"] = self.compare_versions(new_version, old_version)
        return d    
                
    def compare_versions(self, versionA, versionB):
        created_by_typeA, created_by_typeB = versionA["generation info"]["created by type"], versionB["generation info"]["created by type"]
        alignment_type = [created_by_typeA, created_by_typeB]
        d = {}
        contentA, contentB = versionA["content"], versionB["content"]
        for fieldname in contentA:
            valA = contentA[fieldname]["value"]
            valB = contentB[fieldname]["value"]
            is_a_match = self.is_match(valA, valB) or self.get_graded_match(valA, valB, is_a_match=False)
            d[fieldname] = is_a_match
        num_matches = self.tally(d)
        alignment_rating = num_matches / len(contentA)
        return {"alignment rating": alignment_rating, "number matches": num_matches, "alignment type": alignment_type} | d    

if __name__ == "__main__":
    pass      
