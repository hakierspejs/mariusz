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

import lxml.etree
import lxml.html
import requests

from telegram.error import NetworkError, Unauthorized
import telegram


LOGGER = logging.getLogger()

POLSKI_NA_LACINSKI = {
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


NAZWY_DNI = [
    'poniedziałek', 'wtorek', 'środa',
    'czwartek', 'piątek', 'sobota', 'niedziela'
]


NAZWY_MIESIECY = [
    'stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca', 'lipca',
    'sierpnia', 'września', 'października', 'listopada', 'grudnia'
]


def opisz_date(data):
    miesiac = NAZWY_MIESIECY[data.month-1]
    return (
        f'{NAZWY_DNI[data.weekday()]}, {data.day} {miesiac}'
        f' {data.year} o godz {data.hour}:{str(data.minute).zfill(2)}'
    )


def normalizuj_slowo(slowo):
    ret = ''
    for litera in slowo:
        ret += POLSKI_NA_LACINSKI.get(litera, litera)
    LOGGER.debug('normalizuj_slowo(%r)=%r', slowo, ret)
    return ret


def normalizuj(zbior):
    ret = set()
    for slowo in zbior:
        ret.add(slowo)
        ret.add(normalizuj_slowo(slowo))
    LOGGER.debug('normalizuj(%r)=%r', zbior, ret)
    return ret


def sformuluj_powiadomienie_meetupowe():

    prefix = 'https://www.meetup.com/Hakierspejs-%C5%81od%C5%BA/'
    s = requests.get(prefix + '/events/rss/').text
    rss = lxml.etree.fromstring(s.encode())

    timestamps = []
    for item in rss.xpath('//item'):
        for description in item.xpath('.//description/text()'):
            h = lxml.html.fromstring(description.encode())
            p = h.xpath('//p/text()')
            timestamps.append(dateutil.parser.parse(p[-3]))

    jutro = datetime.datetime.now() + datetime.timedelta(days=1)
    daty_spotkan = [t for t in timestamps if t > jutro]
    if not daty_spotkan:
        return
    najblizszy = min(daty_spotkan)

    return (
        f'Nast. spotkanie: {opisz_date(najblizszy)}. Więcej szczegółów: '
        + prefix + '/events/calendar/'
    )


def zbuduj_opis_wersji():
    try:
        with open('/tmp/commit-id') as f:
            wersja = f.read().strip()
        with open('/tmp/commit-no') as f:
            numer = f.read().strip()
        with open('/tmp/commit-date') as f:
            data = f.read().strip()
    except FileNotFoundError:
        wersja_b = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
        wersja = wersja_b.decode()
        no_b = subprocess.check_output(['git', 'log', 'HEAD', '--oneline'])
        numer = len(no_b.split(b'\n'))
        data = subprocess.check_output([
            'git', 'show', '-s', '--format=%ci', 'HEAD'
        ]).decode().strip()
    return f'{wersja[:6]} (#{numer}, {data})'


class BazaChatow:

    def __init__(self, fname):
        self.db = sqlite3.connect(fname)
        self.zaladuj_scheme()

    def zaladuj_scheme(self):
        self.db.execute('CREATE TABLE IF NOT EXISTS chat_ids (chat_id TEXT);')

    def dopisz(self, chat_id):
        if int(chat_id) in self.listuj():
            return
        sql = 'INSERT INTO chat_ids(chat_id) VALUES (?)'
        cur = self.db.cursor()
        cur.execute(sql, (chat_id, ))
        self.db.commit()

    def listuj(self):
        for row in self.db.execute('SELECT DISTINCT chat_id FROM chat_ids'):
            yield int(row[0])


class Mariusz:

    def __init__(self, api_key, sciezka_do_bazy_chatow):
        self.update_id = None
        self.reakcje = {}
        self.ostatnie_sprawdzenie_meetupa = 0
        self.bot = telegram.Bot(api_key)

        try:
            self.update_id = self.bot.get_updates()[0].update_id
        except IndexError:
            self.update_id = None

        if sciezka_do_bazy_chatow:
            self.baza_chatow = BazaChatow(sciezka_do_bazy_chatow)
            wersja = zbuduj_opis_wersji()
            msg = f'Bot się wita po restarcie. wersja={wersja}'
            for chat_id in self.baza_chatow.listuj():
                if chat_id == -1001361809256:
                    continue
                LOGGER.debug('Witam się z chat_id=%r', chat_id)
                self.bot.send_message(text=msg, chat_id=chat_id)
        else:
            self.baza_chatow = None

        self.on(
            normalizuj({'Łódź', 'Łodzi', 'łódzkie'}),
            'https://www.youtube.com/watch?v=IJ2kvZpJ_BU'
        )
        self.on({'.wersja'}, self.wersja)
        self.on({'jeszcze jak'}, 'https://www.youtube.com/watch?v=_jX3qsyIlHc')
        self.on({'nie wiem'}, 'https://www.youtube.com/watch?v=QnMqRTu4Rcc')
        self.on({'.panjezus'}, 'https://www.youtube.com/watch?v=aWJ8X3mt8Io')
        self.on({'.help', '.pomoc', '.komendy'}, self.help)
        self.on({'.czy'}, self.czy)

    def on(self, slowa, reakcja):
        regex_str = '|'.join([
            '^' + x if x.startswith('.') else x for x in slowa
        ])
        regex = re.compile(regex_str, flags=re.IGNORECASE)
        if isinstance(reakcja, str):

            def powiedz_cos(update):
                update.message.reply_text(reakcja)
            powiedz_cos.__doc__ = f'mówi `{reakcja}`'
            self.reakcje[regex] = powiedz_cos
        else:
            self.reakcje[regex] = reakcja

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

    def wersja(self, update):
        '''Podaje pierwsze 6 znaków hasha commita wersji.'''
        update.message.reply_text(zbuduj_opis_wersji())

    def help(self, update):
        '''Wyświetla pomoc'''
        msg = ''
        for reakcja, funkcja in self.reakcje.items():
            opis = funkcja.__doc__ or funkcja.__name__
            msg += f'{reakcja.pattern} => {opis}\n'
        update.message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN)

    def obsluz_meetup(self):
        if self.ostatnie_sprawdzenie_meetupa + 600 > time.time():
            return
        wiadomosc = sformuluj_powiadomienie_meetupowe()
        if not wiadomosc:
            return
        self.ostatnie_sprawdzenie_meetupa = time.time()
        if self.baza_chatow is None:
            LOGGER.debug('obsluz_meetup(): self.baza_chatow is None')
            return
        for chat_id in self.baza_chatow.listuj():
            if chat_id > 0:  # jeśli to priv a nie chat grupowy, pomiń
                continue
            chat = self.bot.get_chat(chat_id=chat_id)
            if chat.pinned_message and chat.pinned_message.text == wiadomosc:
                continue
            msg = self.bot.send_message(text=wiadomosc, chat_id=chat_id)
            self.bot.pin_chat_message(
                message_id=msg.message_id, chat_id=msg.chat_id
            )

    def run(self):

        while True:
            try:
                self.obsluz_meetup()
                self.obsluz_wiadomosci()
            except NetworkError:
                time.sleep(1)
            except Unauthorized:
                # The user has removed or blocked the bot.
                self.update_id += 1

    def obsluz_wiadomosci(self):
        for update in self.bot.get_updates(offset=self.update_id, timeout=10):
            self.update_id = update.update_id + 1
            if update.message is None or update.message.text is None:
                continue
            if self.baza_chatow:
                self.baza_chatow.dopisz(update.message.chat_id)
            for reakcja, funkcja in self.reakcje.items():
                if reakcja.match(update.message.text):
                    funkcja(update)


def main():
    logfmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=logfmt, level='DEBUG')
    api_key = os.environ['API_KEY']
    sciezka_do_bazy_chatow = os.environ.get('SCIEZKA_DO_BAZY_CHATOW')
    Mariusz(api_key, sciezka_do_bazy_chatow).run()


if __name__ == '__main__':
    main()
