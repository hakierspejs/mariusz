'''Describes the logic of the .covid command.'''

import requests
import re
from functools import partial
from humanize import intcomma

from dataclasses import dataclass


_API = 'https://coronavirus-tracker-api.herokuapp.com/v2/locations'


def tracker_api():
    '''Returns dict parsed from JSON from coronavirus-tracker-api.

    Check for more info at:
    https://github.com/ExpDev07/coronavirus-tracker-api
    '''
    res = requests.get(_API)
    return res.json()


@dataclass
class CoronavirusStats:
    '''Contains numbers of coronavirus occurences.'''
    location: str
    confirmed: int
    deaths: int
    recovered: int

    def __str__(self) -> str:
        s = 'SARS-CoV-2 Raport\n'
        s += f'Location: {self.location}\n' if self.location else ''
        s += f'Confirmed: {intcomma(self.confirmed)}\n'
        s += f'Deaths: {intcomma(self.deaths)}\n'
        s += f'Recovered: {intcomma(self.recovered)}'
        return s


def world() -> CoronavirusStats:
    '''Returns CoronavirusStats containing plague information about
    whole world.'''
    latest_world_stats = tracker_api()['latest']
    return CoronavirusStats(location='',
                            confirmed=int(latest_world_stats['confirmed']),
                            deaths=int(latest_world_stats['deaths']),
                            recovered=int(latest_world_stats['recovered']))


def country(country_id) -> CoronavirusStats:
    '''Returns CoronavirusStats containing plague information about
    country with given country id.'''
    latest_stats = tracker_api()

    country_stats = partial(_country_stats, country_id, latest_stats)

    location = _build_country_location(country_id, latest_stats)
    confirmed = country_stats('confirmed')
    deaths = country_stats('deaths')
    recovered = country_stats('recovered')

    return CoronavirusStats(location=location,
                            confirmed=int(confirmed),
                            deaths=int(deaths),
                            recovered=int(recovered))


def covid_arg(text):
    '''Returns arguments associated with ".covid" bot command.

    Example:
    >>> covid_arg(".covid 234")
    234
    >>> covid_arg(".covid 12")
    12
    >>> covid_arg(".covid nothing")

    '''
    regex = re.compile(
        r"(?<=^\.covid )(25[0-7]|2[0-4][0-9]|"
        r"1[0-9][0-9]|[0-9][0-9]|[0-9])(?=)$")
    result = regex.findall(text)

    if len(result) == 0:
        return None

    return int(result[0])


def _build_country_location(country_id, latest_stats):
    '''Builds information about country with given country id from
    given API call.'''
    country_info = latest_stats['locations'][country_id]
    info_list = []

    country_name = country_info['country']
    info_list += [country_name] if country_name else []

    country_code = country_info['country_code']
    info_list += [country_code] if country_code else []

    province = country_info['province']
    info_list += [province] if province else []

    return ', '.join(info_list)


def _country_stats(country_id, latest_stats, field):
    '''Helper function for retrieving information from API call.'''
    return latest_stats['locations'][country_id]['latest'][field]
