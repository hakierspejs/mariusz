'''A module that prepares a message about our upcoming meetup's date and
location.'''

import datetime

import meetupscraper

DAY_NAMES = [
    'poniedziałek', 'wtorek', 'środa',
    'czwartek', 'piątek', 'sobota', 'niedziela'
]


MONTH_NAMES = [
    'stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca', 'lipca',
    'sierpnia', 'września', 'października', 'listopada', 'grudnia'
]


def describe_date(date):
    '''Describes the date, according to the Polish grammar.'''
    month = MONTH_NAMES[date.month-1]
    return (
        f'{DAY_NAMES[date.weekday()]}, {date.day} {month}'
        f' {date.year} o godz {date.hour}:{str(date.minute).zfill(2)}'
    )


def prepare_meetup_message():
    '''Prepares a message about the upcoming meetup.'''

    upcoming_events = sorted(
        [
            e for e in meetupscraper.get_upcoming_events('Hakierspejs-Łódź')
            if (e.date + datetime.timedelta(days=1)) > datetime.datetime.now()
        ], key=lambda e: e.date
    )
    if not upcoming_events:
        return ''
    next_meeting = upcoming_events[0]

    if next_meeting.venue.name.lower() == 'online event':
        place = '(telekonferencja)'
    else:
        place = f'w {next_meeting.venue.name} ({next_meeting.venue.street})'

    ret = (
        f'Nast. spotkanie: {describe_date(next_meeting.date)} {place}. '
        f'Więcej szczegółów: {next_meeting.url}'
    )

    time_left = (next_meeting.date - datetime.datetime.now()).total_seconds()
    if time_left < (60 * 60 * 3):
        ret = 'Za <3h n' + ret[1:]

    return ret


if __name__ == '__main__':
    print(prepare_meetup_message())
