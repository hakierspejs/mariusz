#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import logging
import re
import random
import os
import subprocess
import datetime
import time
import dateutil.parser
import traceback

import lxml.etree
import lxml.html
import requests
from telegram.error import NetworkError, Unauthorized
import telegram
import meetupscraper

import mariusz.coronavirus as coronavirus

LOGGER = logging.getLogger()

POLISH_TO_LATIN = {
    'ą': 'a', 'Ą': 'A',
    'ć': 'c', 'Ć': 'C',
    'ę': 'e', 'Ę': 'E',
    'ł': 'l', 'Ł': 'L',
    'ń': 'n', 'Ń': 'N',
    'ó': 'o', 'Ó': 'O',
    'ś': 's', 'Ś': 'S',
    'ź': 'z', 'Ź': 'Z',
    'ż': 'z', 'Ż': 'Z',
}

DAY_NAMES = [
    'poniedziałek', 'wtorek', 'środa',
    'czwartek', 'piątek', 'sobota', 'niedziela'
]


MONTH_NAMES = [
    'stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca', 'lipca',
    'sierpnia', 'września', 'października', 'listopada', 'grudnia'
]


def describe_date(date):
    month = MONTH_NAMES[date.month-1]
    return (
        f'{DAY_NAMES[date.weekday()]}, {date.day} {month}'
        f' {date.year} o godz {date.hour}:{str(date.minute).zfill(2)}'
    )

def normalize_word(word):
    output = ''
    for letter in word:
        output += POLISH_TO_LATIN.get(letter, letter)
    LOGGER.debug('normalize_word(%r)=%r', word, output)
    return output


def normalize(sequence):
    output = set()
    for word in sequence:
        output.add(word)
        output.add(normalize_word(word))
    LOGGER.debug('normalize(%r)=%r', sequence, output)
    return output


def prepare_meetup_message():

    upcoming_events = sorted(
        [
            e for e in meetupscraper.get_upcoming_events('Hakierspejs-Łódź')
            if (e.date + datetime.timedelta(days=1)) > datetime.datetime.now()
        ], key=lambda e: e.date
    )
    if not upcoming_events:
        return
    next_meeting = upcoming_events[0]

    return (
        f'Nast. spotkanie: {describe_date(next_meeting.date)}'
        f' w {next_meeting.venue.name} ({next_meeting.venue.street}). '
        f'Więcej szczegółów: {next_meeting.url}'
    )


def build_version_description():
    try:
        with open('/tmp/commit-id') as f:
            version = f.read().strip()
        with open('/tmp/commit-no') as f:
            numer = f.read().strip()
        with open('/tmp/commit-date') as f:
            date = f.read().strip()
    except FileNotFoundError:
        version_b = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
        version = version_b.decode()
        no_b = subprocess.check_output(['git', 'log', 'HEAD', '--oneline'])
        numer = len(no_b.split(b'\n'))
        date = subprocess.check_output([
            'git', 'show', '-s', '--format=%ci', 'HEAD'
        ]).decode().strip()
    return f'{version[:6]} (#{numer}, {date})'


class ChatDb:

    def __init__(self, fname):
        self.db = sqlite3.connect(fname)
        self.load_schema()

    def load_schema(self):
        self.db.execute('CREATE TABLE IF NOT EXISTS chat_ids (chat_id TEXT);')

    def insert(self, chat_id):
        if int(chat_id) in self.list():
            return
        sql = 'INSERT INTO chat_ids(chat_id) VALUES (?)'
        cur = self.db.cursor()
        cur.execute(sql, (chat_id, ))
        self.db.commit()

    def list(self):
        for row in self.db.execute('SELECT DISTINCT chat_id FROM chat_ids'):
            yield int(row[0])


class Mariusz:

    def __init__(self, api_key, path_to_chat_db):
        self.update_id = None
        self.reactions = {}
        self.last_meetup_check = 0
        self.bot = telegram.Bot(api_key)

        try:
            self.update_id = self.bot.get_updates()[0].update_id
        except IndexError:
            self.update_id = None

        if path_to_chat_db:
            self.chat_db = ChatDb(path_to_chat_db)
        else:
            self.chat_db = None

        version = build_version_description()
        msg = f'Bot się wita po restarcie. wersja={version}'
        self.send_to_all_chats(msg)

        self.on(
            normalize({'Łódź', 'Łodzi', 'łódzkie'}),
            'https://www.youtube.com/watch?v=IJ2kvZpJ_BU'
        )
        self.on({'\\.wersja'}, self.version)
        self.on({'jeszcze jak'}, 'https://www.youtube.com/watch?v=_jX3qsyIlHc')
        self.on({'nie wiem'}, 'https://www.youtube.com/watch?v=QnMqRTu4Rcc')
        self.on({'\\.panjezus'}, 'https://www.youtube.com/watch?v=aWJ8X3mt8Io')
        self.on({'\\.corobic'}, 'https://www.youtube.com/watch?v=6NR-Lq-hhSw')
        self.on({'\\.help', '\\.pomoc', '\\.komendy'}, self.help)
        self.on({'\\.czy'}, self.czy)
        self.on({'\\.covid', '\\.coronavirus'}, self.covid)

    def send_to_all_chats(self, msg):
        if self.chat_db is None:
            return
        for chat_id in self.chat_db.list():
            if chat_id == -1001361809256:
                continue
            self.bot.send_message(text=msg, chat_id=chat_id)

    def on(self, text, reaction):
        regex_str = '|'.join([
            '^' + x if x.startswith('\\.') else x for x in text
        ])
        regex = re.compile(regex_str, flags=re.IGNORECASE)
        if isinstance(reaction, str):

            def say(update):
                update.message.reply_text(reaction)
            say.__doc__ = f'mówi `{reaction}`'
            self.reactions[regex] = say
        else:
            self.reactions[regex] = reaction

    def covid(self, update):
        '''Statystyki związane z SARS-CoV-2'''
        arg = coronavirus.covid_arg(update.message.text)
        if arg is None:
            update.message.reply_text(str(coronavirus.world()))
            return

        update.message.reply_text(str(coronavirus.country(arg)))

    # pozyczone od kolegi: https://github.com/yojo2/BillyMays/
    def czy(self, update):
        '''Taki magic 8-ball, tyle że nie'''
        responses_yes = [
            "tak", "tak", "na pewno", "jeszcze się pytasz?", "tak (no homo)",
            "zaiste", "teraz już tak", "a czy papież sra w lesie?",
            "jak najbardziej", "jeszcze jak", "jest możliwe", "owszem",
            "czemu nie", "no w sumie...", "nom", "w rzeczy samej", "na bank",
            "skoro tak mówisz, to nie będę zaprzeczał"
        ]
        responses_no = [
            "nie", "nie", "to mało prawdopodobne", "nie sądzę",
            "tak (żartuję, hehe)", "no chyba cię pambuk opuścił",
            "raczej nie", "jeszcze nie", "gówno prawda", "otóż nie", "niep",
            "akurat", "nawet o tym nie myśl", "bynajmniej", "co ty gadasz",
            "chyba ty"
        ]
        responses_dunno = [
            "nie wiem", "być może", "hehe))))))))))))))))))", "może kiedyś",
            "jeszcze nie wiem", "daj mi chwilę to się zastanowię",
            "tego nawet najstarsi górale nie wiedzą", "a jebnąć ci ciupaską?",
            "a co ja jestem, informacja turystyczna?"
        ]

        if random.random() < 0.45:
            response = random.choice(responses_yes)
        elif random.random() < (9/11):
            response = random.choice(responses_no)
        else:
            response = random.choice(responses_dunno)
        update.message.reply_text(response)


    def version(self, update):
        '''Podaje pierwsze 6 znaków hasha commita wersji.'''
        update.message.reply_text(build_version_description())

    def help(self, update):
        '''Wyświetla pomoc'''
        msg = ''
        for reaction, function in self.reactions.items():
            description = function.__doc__ or function.__name__
            msg += f'{reaction.pattern} => {description}\n'
        update.message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN)

    def handle_meetup(self):
        if self.last_meetup_check + 600 > time.time():
            return
        message = prepare_meetup_message()
        if not message:
            return
        self.last_meetup_check = time.time()
        if self.chat_db is None:
            LOGGER.debug('handle_meetup(): self.chat_db is None')
            return
        for chat_id in self.chat_db.list():
            if chat_id > 0:  # skip if it's a private chat instead of a group
                continue
            chat = self.bot.get_chat(chat_id=chat_id)
            if chat.pinned_message and chat.pinned_message.text == message:
                continue
            msg = self.bot.send_message(text=message, chat_id=chat_id)
            self.bot.pin_chat_message(
                message_id=msg.message_id, chat_id=msg.chat_id
            )

    def run(self):

        while True:
            try:
                self.handle_meetup()
                self.handle_messages()
            except NetworkError:
                time.sleep(1)
            except Unauthorized:
                # The user has removed or blocked the bot.
                self.update_id += 1
            except Exception:
                formatted_traceback = traceback.format_exc()
                message = f'Bot umar. Traceback:\n\n{formatted_traceback}'
                self.send_to_all_chats(message)
                raise

    def handle_messages(self):
        for update in self.bot.get_updates(offset=self.update_id, timeout=10):
            self.update_id = update.update_id + 1
            if update.message is None or update.message.text is None:
                continue
            if self.chat_db:
                self.chat_db.insert(update.message.chat_id)
            for reaction, funtion in self.reactions.items():
                if reaction.match(update.message.text):
                    funtion(update)


def main():
    logfmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=logfmt, level='DEBUG')
    api_key = os.environ['API_KEY']
    path_to_chat_db = os.environ.get('SCIEZKA_DO_BAZY_CHATOW')
    Mariusz(api_key, path_to_chat_db).run()


if __name__ == '__main__':
    main()
