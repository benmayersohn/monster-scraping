from monster import MonsterSearch, MonsterTextParser
from helpers import DATA_SCI_KEYWORDS
import json

# Inspired by Jesse Steinweg-Woods' code for web scraping on Indeed: https://jessesw.com/Data-Science-Skills/

filename = './data/data_scientist_nyc_search.json'
with open(filename, 'r') as f:
    search = MonsterSearch.json_deserialize(in_dict=json.load(f))

listing = next(search)
word_counts = MonsterTextParser(DATA_SCI_KEYWORDS).count_words(listing)

print(word_counts)
