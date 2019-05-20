from monster import MonsterSearch, MonsterLocation
import json

filename = './data/data_scientist_nyc_search_test.json'

query = "Data Scientist"
page_limit = 1
location = "New York, NY"
alternates = ("Brooklyn, NY", "Jersey City, NJ", "Hoboken, NJ", "Secaucus, NJ", "Newark, NJ", "Manhattan, NY",
              "New York City, NY")
extra_titles = ("Data Science", "Data Engineer")  # extra keywords for title, other than "Data Scientist"

# create search and fetch first page
search = MonsterSearch(MonsterLocation.from_string(location, alternates=alternates), query, extra_titles=extra_titles)

search.fetch_listings(limit=page_limit)
search.fetch_descriptions()

out_dict = search.json_dict()
with open(filename, 'w') as outfile:
    json.dump(out_dict, outfile)

# load file
with open(filename, 'r') as f:
    new_search = MonsterSearch.json_deserialize(in_dict=json.load(f))

assert len(search) == len(new_search)
assert [search.results.get(job_id) == new_search.results.get(job_id) for job_id in search.job_ids]
