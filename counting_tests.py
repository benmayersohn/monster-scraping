from monster import MonsterSearch, MonsterTextParser
from helpers import DATA_SCI_KEYWORDS
import json

# Inspired by Jesse Steinweg-Woods' code for web scraping on Indeed: https://jessesw.com/Data-Science-Skills/

filename = './data/data_scientist_nyc_search.json'
with open(filename, 'r') as f:
    search = MonsterSearch.json_deserialize(in_dict=json.load(f))

listing = next(search)

delete_matching = "[^a-zA-Z.+3]"  # the "." and "3" are for D3.js
word_counts = MonsterTextParser(DATA_SCI_KEYWORDS).count_words(listing, delete_matching=delete_matching)

print(word_counts)
