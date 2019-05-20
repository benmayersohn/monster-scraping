from helpers import DATA_SCI_KEYWORDS
from monster import MonsterSearch, MonsterTextParser
import json
import pandas as pd
import matplotlib.pyplot as plt

"""
The search results were generated in the following way:

query = "Data Scientist"
page_limit = 10
location = "New York, NY"
alternates = ("Brooklyn, NY", "Jersey City, NJ", "Hoboken, NJ", "Secaucus, NJ", "Newark, NJ", "Manhattan, NY",
              "New York City, NY")
keywords = ("Data Science", "Data Engineer")

search = MonsterSearch(MonsterLocation.from_string(location, alternates=alternates), query, keywords=keywords)
search.fetch_listings(limit=page_limit)

Then they were saved into a file "data_scientist_nyc_search.json":

filename = 'data_scientist_nyc_search.json'
out_dict = search.json_dict()
with open(filename, 'w') as outfile:
    json.dump(out_dict, outfile)

We load this into a MonsterSearch structure.
Then we check each listing for the keywords, and tally how many we have in total.
Finally, we create a histogram visualizing keyword popularity.
"""

filename = './data/data_scientist_nyc_search.json'

with open(filename, 'r') as f:
    search = MonsterSearch.json_deserialize(in_dict=json.load(f))

# get individual keyword counts as percentage of ads mentioning the keyword
tally = MonsterTextParser(DATA_SCI_KEYWORDS).count_words(search, as_percentage=True)

top_10 = tally.iloc[:10]

fig, ax = plt.subplots(1, 1)
top_10.plot.bar(x='Keyword', rot=30, ax=ax, legend=False)
ax.set_ylabel('% of Ads Mentioning Keyword')
ax.set_title('Keyword Popularity: Data Scientist Jobs in NYC')

plt.savefig('./assets/data_sci_nyc_results.png')
plt.show()
