from monster import MonsterListing, MonsterLocation

city = "New York"
state = "NY"
alternates = ("Brooklyn, NY",)
location = MonsterLocation(city, state, alternates=alternates)

# We will pick a listing from Brooklyn, NY
job_id = '208183191'

listing = MonsterListing.from_id(job_id)
listing.fetch_description()  # get description from webpage

assert listing.location == location  # should be true, because "Brooklyn, NY" is listed as an alternate location

assert MonsterListing.json_deserialize(in_str=listing.json_serialize()) == listing

