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

    def get_alignment_type(self, latest_version, old_version):
        latest_version_type = "user" if latest_version["data"]["is user"] else "model"
        latest_version_creator = latest_version["data"]["created by"] 
        old_version_type = "user" if old_version["data"]["is user"] else "model"
        old_version_creator = old_version["data"]["created by"]
        return {"created by names": [old_version_creator, latest_version_creator], "created by types": [old_version_type, latest_version_type]}   

    def compare_last_two_versions(self):
        latest_version_name, latest_version = self.transcript.get_latest_version(self.transcript.versions)
        old_version_name = latest_version["data"]["old version name"]
        old_version = self.transcript.get_version_by_name(old_version_name)
        matches_dict = self.compare_versions(latest_version, old_version)
        num_matches = self.tally(matches_dict)
        alignment_rating = num_matches / len(matches_dict)
        alignment_type_dict = self.get_alignment_type(latest_version, old_version)
        return {"compared to": old_version_name,"alignment rating": alignment_rating, "number matches": num_matches} | alignment_type_dict | matches_dict
                
    def compare_versions(self, versionA, versionB):
        d = {}
        contentA, contentB = versionA["content"], versionB["content"]
        for fieldname in contentA:
            valA = contentA[fieldname]
            valB = contentB[fieldname]
            is_a_match = self.is_match(valA, valB) or self.get_graded_match(valA, valB, is_a_match=False)
            d[fieldname] = is_a_match
        return d

if __name__ == "__main__":
    tc = TranscriptComparer(0,0,0)  
    d = {1:True, 2:0.5, 3:True, 4:0.25} 
    score = tc.tally(d, use_graded_match=True)
    print(f"{score = }")         
