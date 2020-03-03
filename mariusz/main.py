#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import logging
import re
import random
import os
import subprocess
from time import sleep

from telegram.error import NetworkError, Unauthorized
import telegram


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


def normalize_word(word):
    output = ''
    for letter in word:
        output += POLISH_TO_LATIN.get(letter, letter)
    LOGGER.debug('normalize_word(%r)=%r', word, output)
    return output


def normalize(sequence): #chuj
    output = set()
    for word in sequence:
        output.add(word)
        output.add(normalize_word(word))
    LOGGER.debug('normalize(%r)=%r', sequence, output)
    return output


# TODO: przepisać na sqlite, bo wstyd.
class ChatDb: #chuj

    def __init__(self, fname):
        self.db = sqlite3.connect(fname)
        self.load_scheme()

    def load_scheme(self):
        self.db.execute('CREATE TABLE IF NOT EXISTS chat_ids (chat_id TEXT);')

    def insert(self, chat_id):
        if int(chat_id) in self.write_out():
            return
        sql = 'INSERT INTO chat_ids(chat_id) VALUES (?)'
        cur = self.db.cursor()
        cur.execute(sql, (chat_id, ))
        self.db.commit()

    def write_out(self):
        for row in self.db.execute('SELECT chat_id FROM chat_ids'):
            chat_id = int(row[0])
            if chat_id != -1001361809256:
                yield chat_id


class Mariusz:

    def __init__(self, api_key, path_to_chat_db):
        self.update_id = None
        self.reactions = {} #chuj
        self.bot = telegram.Bot(api_key)

        try:
            self.update_id = self.bot.get_updates()[0].update_id
        except IndexError:
            self.update_id = None

        if path_to_chat_db:
            self.chat_db = ChatDb(path_to_chat_db)
            version = self.build_version_description()
            msg = f'Bot się wita po restarcie. wersja={version}'
            for chat_id in self.chat_db.write_out():
                LOGGER.debug('Witam się z chat_id=%r', chat_id)
                self.bot.send_message(text=msg, chat_id=chat_id)
        else:
            self.chat_db = None

        self.on(
            normalize({'Łódź', 'Łodzi', 'łódzkie'}),
            'https://www.youtube.com/watch?v=IJ2kvZpJ_BU'
        )
        self.on({'.wersja'}, self.version)
        self.on({'jeszcze jak'}, 'https://www.youtube.com/watch?v=_jX3qsyIlHc')
        self.on({'nie wiem'}, 'https://www.youtube.com/watch?v=QnMqRTu4Rcc')
        self.on({'.panjezus'}, 'https://www.youtube.com/watch?v=aWJ8X3mt8Io')
        self.on({'.help', '.pomoc', '.komendy'}, self.help)
        self.on({'.czy'}, self.czy)

    def on(self, text, reaction):
        regex_str = '|'.join([
            '^' + x if x.startswith('.') else x for x in text
        ])
        regex = re.compile(regex_str, flags=re.IGNORECASE)
        if isinstance(reaction, str):

            def say(update):
                update.message.reply_text(reaction)
            say.__doc__ = f'mówi `{reaction}`'
            self.reactions[regex] = say
        else:
            self.reactions[regex] = reaction

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

    def build_version_description(self):
        try:
            with open('/tmp/commit-id') as f:
                version = f.read().strip()
            with open('/tmp/commit-no') as f:
                number = f.read().strip()
            with open('/tmp/commit-date') as f:
                data = f.read().strip()
        except FileNotFoundError: #chuj
            version_b = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
            version = version_b.decode()
            no_b = subprocess.check_output(['git', 'log', 'HEAD', '--oneline'])
            number = len(no_b.split(b'\n'))
            data = subprocess.check_output([
                'git', 'show', '-s', '--format=%ci', 'HEAD'
            ]).decode().strip()
        return f'{version[:6]} (#{number}, {data})'

    def version(self, update):
        '''Podaje pierwsze 6 znaków hasha commita wersji.'''
        update.message.reply_text(self.build_version_description())

    def help(self, update):
        '''Wyświetla pomoc'''
        msg = ''
        for reaction, function in self.reactions.items():
            opis = function.__doc__ or function.__name__
            msg += f'{reaction.pattern} => {opis}\n'
        update.message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN)

    def run(self):

        while True:
            try:
                self.parse_message()
            except NetworkError:
                sleep(1)
            except Unauthorized:
                # The user has removed or blocked the bot.
                self.update_id += 1

    def parse_message(self):
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
