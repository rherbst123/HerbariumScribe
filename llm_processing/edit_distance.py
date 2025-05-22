import math
from nltk.metrics.distance import edit_distance as nltk_edit_distance 
from nltk.metrics.distance import edit_distance_align as nltk_edit_distance_align 
import numpy as np

class StringDistance:
        
    def scale(self, val, minimum, maximum):
        return (val-minimum) / (maximum-minimum)     

class NLTKDistance(StringDistance):

    # exposed method
    def calculate_edit_distance(self, s1, s2, scaled=True):
        edit_distance = nltk_edit_distance(s1, s2)
        return self.scale(edit_distance, minimum=0, maximum=max(len(s1), len(s2))) if scaled else edit_distance
