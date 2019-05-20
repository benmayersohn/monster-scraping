from __future__ import annotations
import requests
from typing import Optional, Union
from bs4 import BeautifulSoup
from collections import Counter
from helpers import NA
from bs4.element import Tag
import json
from time import sleep
from requests.exceptions import ConnectionError
from urllib3.exceptions import MaxRetryError, NewConnectionError
from socket import gaierror
import re
from nltk.corpus import stopwords
from pandas import DataFrame
import pandas as pd

"""
Classes that allow us to scrape Monster.com listings
Inspired by Jesse Steinweg-Woods' project on web scraping from Indeed.com
His blog post: https://jessesw.com/Data-Science-Skills/
"""


class MonsterTextParser:
    def __init__(self, keywords: tuple):
        self.keywords = keywords

    def count_words(self, results: Union[MonsterListing, MonsterSearch], as_percentage: bool = False,
                    delete_matching: str = "[^a-zA-Z]") -> DataFrame:

        freqs = Counter()
        if type(results) == MonsterListing:
            freqs.update(self.words_from_description(results, delete_matching=delete_matching))
        else:
            [freqs.update(self.words_from_description(listing, delete_matching=delete_matching)) for listing in results]

        out_dict = dict([(x, freqs[x.lower()]) for x in self.keywords])

        df = pd.DataFrame.from_dict(out_dict, orient='index', columns=['Frequency']).reset_index()
        df = df.rename(columns={'index': 'Keyword'})
        if as_percentage:
            df['Frequency'] = df['Frequency'] * 100 / (1 if type(results) == MonsterListing else len(results))
        return df.sort_values(by='Frequency', ascending=False).reset_index(drop=True)

    def words_from_description(self, listing: MonsterListing, delete_matching: str = "[^a-zA-Z]") -> list:
        """
        Extract words from description in listing. Some code lifted from Jesse Steinweg-Woods' blog post.
        :param listing: MonsterListing to get words from
        :param delete_matching: delete any character not matching
        :return:
        """
        if listing.description is None:
            listing.fetch_description()

        description = listing.description

        lines = (line.strip() for line in description.splitlines())

        # break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))

        # Get rid of all blank lines and ends of line
        text = ''.join(chunk + ' ' for chunk in chunks if chunk).encode('utf-8')

        # Now clean out all of the unicode junk
        text = text.decode('unicode_escape')

        # Get rid of any terms that aren't words
        text = re.sub(delete_matching, " ", text)

        text = text.lower().split()  # Go to lower case and split them apart

        stop_words = set(stopwords.words("english"))

        words = list()
        keywords_lower = [x.lower() for x in self.keywords]
        for w in text:
            if w not in keywords_lower:
                w = w.replace('.', '')
            if w not in stop_words and len(w) > 0:
                words.append(w)

        # Last, just get the set of these.
        return list(set(words))


class MonsterLocation:

    @staticmethod
    def format_location(city: str, state: str) -> tuple:
        """
        :param city: Search city
        :param state: Search state
        :return: (city, state) formatted properly
        """

        state = state.upper()
        city = ' '.join([x.lower().capitalize() for x in city.split(' ')])  # capitalize all words
        return city, state

    @classmethod
    def from_string(cls, loc_string: str, alternates: tuple = ()) -> MonsterLocation:
        """
        :param loc_string: e.g. "New York, NY". A location string.
        :param alternates: e.g. ("Brooklyn, NY", "Jersey City, NJ", "Manhattan, NY")
        :return: A MonsterLocation from the location string
        """
        city, state = [x.strip() for x in loc_string.split(',')]

        return cls(*cls.format_location(city, state), alternates=alternates)

    def __init__(self, city: str, state: str, alternates: tuple = ()):
        """
        :param city: Search city
        :param state: Search state
        :param alternates: e.g. for "New York, NY": ("Brooklyn, NY", "Jersey City, NJ", "Manhattan, NY")
        """

        self.city, self.state = self.format_location(city, state)

        # We store the alternates
        if len(alternates) > 0:
            self.alternates = [MonsterLocation.from_string(x) for x in alternates]
        else:
            self.alternates = alternates

    @staticmethod
    def search_var_from_arguments(city: str, state: str) -> str:
        return f'{"-".join(city.split(" "))}__2C-{state}'

    # applies search_var_from_arguments to object's city and state
    def search_var(self) -> str:
        return self.search_var_from_arguments(self.city, self.state)

    # compares two locations. comparisons are also made between each location and the other's alternates.
    def __eq__(self, other) -> bool:
        if isinstance(other, MonsterLocation):
            if self.city == other.city and self.state == other.state:
                return True
            else:
                if len(self.alternates) > 0:
                    for alt in self.alternates:
                        if alt.city == other.city and alt.state == other.state:
                            return True
                elif len(other.alternates) > 0:
                    for alt in other.alternates:
                        if alt.city == self.city and alt.state == self.state:
                            return True
        return False

    def __str__(self) -> str:
        return f'{self.city}, {self.state}'


class MonsterSearch:
    """
    Search results for a particular query on monster.

    The search results are stored in a dictionary. The key is the job ID, and the value is a MonsterListing
    """

    def __init__(self, location: MonsterLocation, query: str, extra_titles: tuple = None, results: dict = None,
                 job_ids: list = None):
        """
        Parameters
        ----------
        :param location: Location to search in
        :param query: The term we will be searching for
        :param extra_titles: Other valid title substrings
        :param results: dictionary of search results indexed by unique job id
        :param job_ids: list of job ids in order they were fetched
        """

        self.location = location
        self.base_url = f'https://www.monster.com/jobs/search/?q={"-".join(query.lower().split(" "))}' \
            f'&where={self.location.search_var()}'
        self.query = query
        self.extra_titles = extra_titles
        self.results = results
        self.job_ids = job_ids  # job ids of results; helps us maintain an order...
        self.job_id_index = 0  # for iteration

    def is_valid_listing(self, listing: MonsterListing) -> bool:
        """
        Checks to see if a listing matches our desired search.
        :param listing: search result from Monster
        :return: True if the listing matches our query and is in the right location, False otherwise
        """
        if self.location == listing.location:
            if self.query.lower() in listing.job_title.lower():
                return True
            for title in self.extra_titles:
                if title.lower() in listing.job_title.lower():
                    return True
        return False

    def fetch_listings(self, limit: int = 10, refetch: bool = False):

        if self.results is not None and len(self.results) != 0 and not refetch:
            print("You've already fetched the results for this query. Set refetch to True to fetch them again.")
        else:
            self.results = dict()
            self.job_ids = list()
            search_url = f'{self.base_url}&stpage=1&page={limit}'  # tack on page ranges to base URL

            try:
                response = requests.get(search_url)

                soup = BeautifulSoup(response.text, 'html.parser')

                all_listings = soup.find_all('section', attrs={'data-jobid': True})

                for item in all_listings:
                    listing = MonsterListing.from_search_results(item)
                    if listing is not None and self.is_valid_listing(listing) and listing.job_id not in self.results:
                        self.results[listing.job_id] = listing
                        self.job_ids.append(listing.job_id)
            except (gaierror, ConnectionError, MaxRetryError, NewConnectionError) as e:
                print(e)

    def fetch_descriptions(self, suppress_output=False):
        desc_count = 0
        if self.results is not None:
            for job_id in self.job_ids:
                listing = self.results[job_id]
                desc_count += 1
                if len(listing.description) > 0 and not suppress_output:
                    print(f'Description #{desc_count} is already present.')
                else:
                    listing.fetch_description()
                    if not suppress_output:
                        if len(listing.description) > 0:
                            print(f'Description #{desc_count} successfully fetched.')
                        else:
                            print(f'Listing #{desc_count} appears to be dead...')
                    sleep(1)  # so we don't overwhelm the server (idea courtesy of Jesse Steinweg-Woods)
        else:
            print("You need to fetch the listings first: use fetch_listings(...)")

    def json_dict(self) -> dict:
        out_dict = dict()
        out_dict['location'] = {'main': self.location.__str__(),
                                'alternates': [x.__str__() for x in self.location.alternates]}
        out_dict['query'] = self.query
        out_dict['extra_titles'] = self.extra_titles
        out_dict['base_url'] = self.base_url
        out_dict['results'] = dict()
        out_dict['job_ids'] = list()

        for job_id in self.job_ids:
            out_dict['results'][job_id] = self.results[job_id].json_dict()
            out_dict['job_ids'].append(job_id)
        return out_dict

    def json_serialize(self) -> str:
        return json.dumps(self.json_dict())

    @classmethod
    def json_deserialize(cls, in_dict=None, in_str=None) -> MonsterSearch:
        if in_str is not None:
            in_dict = json.loads(in_str)
        loc_dict = in_dict['location']
        location = MonsterLocation.from_string(loc_dict['main'], alternates=loc_dict['alternates'])
        query = in_dict['query']
        extra_titles = in_dict['extra_titles']
        results = in_dict['results']
        job_ids = in_dict['job_ids']

        deser_results = dict([(job_id, MonsterListing.json_deserialize(in_dict=results[job_id])) for job_id in results])

        return cls(location, query, extra_titles=extra_titles, results=deser_results, job_ids=job_ids)

    # for iterating through results
    def __iter__(self):
        self.job_id_index = 0
        return self

    def __next__(self):
        if self.job_id_index < len(self.job_ids):
            job_id_index = self.job_id_index
            self.job_id_index += 1

            return self.results[self.job_ids[job_id_index]]
        else:
            raise StopIteration

    # length of MonsterSearch = length of results
    def __len__(self):
        return len(self.job_ids)

    def __str__(self):
        out_str = \
            f'Search Query: {self.query}\n' \
            f'Location: {self.location}\n'

        out_str += f'Number of Listings: {0 if self.results is None else len(self.results)}'

        return out_str


class MonsterListing:
    def __init__(self, job_id: str, job_url: str, location: MonsterLocation,
                 company: str, job_title: str, description: str = ''):
        """
        Set up MonsterListing class
        :param job_id: unique job ID that allows one to find the listing
        :param job_url: URL to the STATIC page where the listing is located; NOT search result page
        :param location: Geographic location of job
        :param company: Company name
        :param job_title: Job title used on website
        :param description: Long description of job duties, expectations, requirements, etc.
        """
        self.job_id = job_id
        self.job_url = job_url
        self.location = location
        self.company = company
        self.job_title = job_title
        self.description = description

    @classmethod
    def from_search_results(cls, item: Tag) -> Optional[MonsterListing]:
        """
        Parses listing properties from source. Useful for when we're looping through search results.
        :param item: Search results from BeautifulSoup
        :return: MonsterListing with all fields filled except description, which requires another HTTP request.
        """
        if item is not None:
            job_id = item['data-jobid']
            loc_string = item \
                .find('div', attrs={'class': 'location'}) \
                .find('span', attrs={'class': 'name'}).text.strip()
            if ',' in loc_string:
                city, state = [a.strip() for a in loc_string.split(',')]
                state = state[:2]  # two-letter state format
                location = MonsterLocation(city, state)
            else:
                location = MonsterLocation(NA, NA)  # NA value; will not match any valid locations

            job_title = item.find('h2', attrs={'class': 'title'}).find('a', href=True).string.strip()

            company = item \
                .find('div', attrs={'class': 'company'}) \
                .find('span', attrs={'class': 'name'}).text.strip()

            job_url = item.find('h2', attrs={'class': 'title'}).find('a', href=True)['href']

            # add MonsterListing to results
            return cls(job_id, job_url, location, company, job_title)

    @classmethod
    def from_id(cls, job_id) -> Optional[MonsterListing]:
        temp_url = f'https://www.monster.com/jobs/search/?jobid={job_id}'

        # get HTML
        response = requests.get(temp_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # get first item
        item = soup.find('section', attrs={'data-jobid': True})
        return cls.from_search_results(item)

    def __str__(self) -> str:
        out_str = \
            f'Job Title: {self.job_title}\n' \
            f'Company: {self.company}\n' \
            f'Location: {self.location}\n' \
            f'ID: {self.job_id}'
        return out_str

    def __eq__(self, other) -> bool:
        if type(other) == MonsterListing:
            return self.job_id == other.job_id
        return False

    def json_dict(self) -> dict:
        out_dict = {'job_id': self.job_id, 'job_url': self.job_url, 'location': self.location.__str__(),
                    'company': self.company, 'job_title': self.job_title, 'description': self.description}
        return out_dict

    def json_serialize(self) -> str:
        return json.dumps(self.json_dict())

    @classmethod
    def json_deserialize(cls, in_dict=None, in_str=None) -> MonsterListing:
        if in_str is not None:
            in_dict = json.loads(in_str)

        # convert to MonsterListing
        job_id = in_dict['job_id']
        job_url = in_dict['job_url']
        location = MonsterLocation.from_string(in_dict['location'])
        description = in_dict['description']
        company = in_dict['company']
        job_title = in_dict['job_title']
        return cls(job_id, job_url, location, company, job_title, description)

    def fetch_description(self):
        response = requests.get(self.job_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        job_body = soup.find('div', attrs={'id': 'JobDescription'})

        if job_body is not None:
            self.description = job_body.get_text(separator=' ')  # add whitespace between HTML tags
        else:
            self.description = ''

    def get_excerpt(self, word_limit=1000, end_string='...'):
        if self.description is None:
            self.fetch_description()

        return self.description[:word_limit] + end_string
