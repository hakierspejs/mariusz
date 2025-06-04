#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Entry point of Mariusz, a Telegram chatbot of Hakierspejs Łódź."""

import asyncio
import logging
import os
import random
import re
import signal
import sqlite3
import subprocess
import time
import traceback

import telegram
from telegram.error import NetworkError

import mariusz.coronavirus as coronavirus
import mariusz.gnujdb
import mariusz.meetup
import mariusz.mumble
import mariusz.wiki

LOGGER = logging.getLogger()

MUMBLE_SERVER = "hs-ldz.pl"

POLISH_TO_LATIN = {
    "ą": "a",
    "Ą": "A",
    "ć": "c",
    "Ć": "C",
    "ę": "e",
    "Ę": "E",
    "ł": "l",
    "Ł": "L",
    "ń": "n",
    "Ń": "N",
    "ó": "o",
    "Ó": "O",
    "ś": "s",
    "Ś": "S",
    "ź": "z",
    "Ź": "Z",
    "ż": "z",
    "Ż": "Z",
}

MAIN_CHAT_ID = int(os.environ["MAIN_CHAT_ID"])


def normalize_word(word):
    """Returns a version of the world with removed Polish diacritic
    characters."""
    output = ""
    for letter in word:
        output += POLISH_TO_LATIN.get(letter, letter)
    LOGGER.debug("normalize_word(%r)=%r", word, output)
    return output


def normalize(sequence_of_words):
    """Transforms a sequence of words into a set of words both with and without
    Polish diacritic characters."""
    output = set()
    for word in sequence_of_words:
        output.add(word)
        output.add(normalize_word(word))
    LOGGER.debug("normalize(%r)=%r", sequence_of_words, output)
    return output


def build_version_description():
    """Describes the current version of the bot."""
    try:
        with open("/tmp/commit-id") as fh:
            version = fh.read().strip()
        with open("/tmp/commit-no") as fh:
            numer = fh.read().strip()
        with open("/tmp/commit-date") as fh:
            date = fh.read().strip()
    except FileNotFoundError:
        version_b = subprocess.check_output(["git", "rev-parse", "HEAD"])
        version = version_b.decode()
        no_b = subprocess.check_output(["git", "log", "HEAD", "--oneline"])
        numer = len(no_b.split(b"\n"))
        date = (
            subprocess.check_output(
                ["git", "show", "-s", "--format=%ci", "HEAD"]
            )
            .decode()
            .strip()
        )
    return f"{version[:6]} (#{numer}, {date})"


class ChatDb:
    """Collects a list of chats that the bot ever spoke with."""

    def __init__(self, fname):
        self.db = sqlite3.connect(fname)
        self.load_schema()

    def load_schema(self):
        """Initializes the database by creating required entities."""
        self.db.execute("CREATE TABLE IF NOT EXISTS chat_ids (chat_id TEXT);")

    def insert(self, chat_id):
        """Inserts a chat into the set."""
        return
        if int(chat_id) in self.list():
            return
        sql = "INSERT INTO chat_ids(chat_id) VALUES (?)"
        cur = self.db.cursor()
        cur.execute(sql, (chat_id,))
        self.db.commit()

    def list(self):
        """Generated a sequence of chats that the bot ever spoke with."""
        for row in self.db.execute("SELECT DISTINCT chat_id FROM chat_ids"):
            yield int(row[0])


class Mariusz:
    """Main class of the bot. Handles all the commands."""

    def __init__(self, api_key, path_to_chat_db, group_regex):
        self.update_id = None
        self.reactions = {}
        self.last_meetup_check = 0
        self.bot = telegram.Bot(api_key)
        self.group_regex = group_regex
        self.meetup_exception_counter = 0
        self.mumble_state = mariusz.mumble.get_mumble_user_count(MUMBLE_SERVER)
        self.mumble_last_update = time.time()
        self.mumble_last_check = time.time()
        self.wiki_last_update = time.time()
        self.wiki_last_check = time.time()
        self.wiki_msg = mariusz.wiki.build_wiki_message()

        if path_to_chat_db:
            self.chat_db = ChatDb(path_to_chat_db)
        else:
            self.chat_db = None

        self.build_version = build_version_description()

        self.on(
            normalize({"Łódź", "Łodzi", "łódzkie"}),
            "https://www.youtube.com/watch?v=IJ2kvZpJ_BU",
        )
        self.on({"\\.wersja"}, self.version)
        self.on({"jeszcze jak"}, "https://www.youtube.com/watch?v=_jX3qsyIlHc")
        self.on(mariusz.gnujdb.TRIGGERS, self.czymamy)
        # self.on({'nie wiem'}, 'https://www.youtube.com/watch?v=QnMqRTu4Rcc')
        self.on({"\\.panjezus"}, "https://www.youtube.com/watch?v=aWJ8X3mt8Io")
        self.on({"\\.corobic"}, "https://www.youtube.com/watch?v=6NR-Lq-hhSw")
        self.on({"\\.co"}, "https://www.youtube.com/watch?v=YeIGdcSM5NY")
        self.on({"\\.help", "\\.pomoc", "\\.komendy"}, self.help)
        self.on({"\\.czy"}, self.czy)
        self.on({"\\.covid", "\\.coronavirus"}, "Komenda wyłączona.")

    async def send_to_all_chats(self, msg):
        """Sends a message to all the chats other than the main one."""
        if self.chat_db is None:
            return
        for chat_id in self.chat_db.list():
            if chat_id == MAIN_CHAT_ID:
                continue
            await self.try_send_message(text=msg, chat_id=chat_id)

    async def try_send_message(self, *args, **kwargs):
        """A wrapper for send_message that silences Unauthorized exception."""
        try:
            ret = await self.bot.send_message(*args, **kwargs)
            LOGGER.debug("try_send_message(%r, %r)=%r", args, kwargs, ret)
            return ret
        except telegram.error.BadRequest as e:
            LOGGER.exception(e)
            return None

    def on(self, text, reaction):
        """Registers a reaction to a given text message."""
        regex_str = "|".join(
            ["^" + x if x.startswith("\\.") else x for x in text]
        )
        regex = re.compile(regex_str, flags=re.IGNORECASE)
        if isinstance(reaction, str):

            async def say(update):
                await update.message.reply_text(reaction)

            say.__doc__ = f"mówi `{reaction}`"
            self.reactions[regex] = say
        else:
            self.reactions[regex] = reaction

    async def covid(self, update):
        """Statystyki związane z SARS-CoV-2"""
        arg = coronavirus.covid_arg(update.message.text)
        if arg is None:
            await update.message.reply_text(str(coronavirus.world()))
            return

        await update.message.reply_text(str(coronavirus.country(arg)))

    # pozyczone od kolegi: https://github.com/yojo2/BillyMays/
    async def czy(self, update):
        """Taki magic 8-ball, tyle że nie"""
        responses_yes = [
            "tak",
            "tak",
            "na pewno",
            "jeszcze się pytasz?",
            "tak (no homo)",
            "zaiste",
            "teraz już tak",
            "a czy papież sra w lesie?",
            "jak najbardziej",
            "jeszcze jak",
            "jest możliwe",
            "owszem",
            "czemu nie",
            "no w sumie...",
            "nom",
            "w rzeczy samej",
            "na bank",
            "skoro tak mówisz, to nie będę zaprzeczał",
        ]
        responses_no = [
            "nie",
            "nie",
            "to mało prawdopodobne",
            "nie sądzę",
            "tak (żartuję, hehe)",
            "no chyba cię pambuk opuścił",
            "raczej nie",
            "jeszcze nie",
            "gówno prawda",
            "otóż nie",
            "niep",
            "akurat",
            "nawet o tym nie myśl",
            "bynajmniej",
            "co ty gadasz",
            "chyba ty",
        ]
        responses_dunno = [
            "nie wiem",
            "być może",
            "hehe))))))))))))))))))",
            "może kiedyś",
            "jeszcze nie wiem",
            "daj mi chwilę to się zastanowię",
            "tego nawet najstarsi górale nie wiedzą",
            "a jebnąć ci ciupaską?",
            "a co ja jestem, informacja turystyczna?",
        ]

        if random.random() < 0.45:
            response = random.choice(responses_yes)
        elif random.random() < (9 / 11):
            response = random.choice(responses_no)
        else:
            response = random.choice(responses_dunno)
        await update.message.reply_text(response)

    async def version(self, update):
        """Podaje pierwsze 6 znaków hasha commita wersji."""
        await update.message.reply_text(build_version_description())

    async def czymamy(self, update):
        # Czy jest w spejse pickit 2?
        url = mariusz.gnujdb.czymamy(update.message.text)
        if url:
            await update.message.reply_text(url)

    async def help(self, update):
        """Wyświetla pomoc"""
        msg = ""
        for reaction, function in self.reactions.items():
            description = function.__doc__ or function.__name__
            msg += f"{reaction.pattern} => {description}\n"
        await update.message.reply_text(
            msg, parse_mode=telegram.constants.ParseMode.MARKDOWN
        )

    def prepare_meetup_message(self):
        try:
            message = mariusz.meetup.prepare_meetup_message(self.group_regex)
            self.meetup_exception_counter = 0
        except Exception:
            self.meetup_exception_counter += 1
            if self.meetup_exception_counter > 10:
                raise
            time.sleep(10.0)
            return None
        return message

    async def maybe_update_meetup_message(self):
        """Determines whether current pinned meetup message should be replaced
        and updates it if necessary."""
        if self.last_meetup_check + (3600 * 1) > time.time():
            LOGGER.debug(
                "maybe_update_meetup_message: "
                "self.last_meetup_check + (3600 * 1) > time.time()"
            )
            return

        message = self.prepare_meetup_message()

        if not message:
            LOGGER.debug("maybe_update_meetup_message(): not message")
            return
        self.last_meetup_check = time.time()
        if self.chat_db is None:
            LOGGER.debug("maybe_update_meetup_message(): self.chat_db is None")
            return
        for chat_id in self.chat_db.list():
            if chat_id > 0:  # skip if it's a private chat instead of a group
                LOGGER.debug("maybe_update_meetup_message(): chat_id > 0")
                continue
            chat = await self.bot.get_chat(chat_id=chat_id)
            if chat.pinned_message and chat.pinned_message.text == message:
                LOGGER.debug("maybe_update_meetup_message(): nihil novi")
                continue
            msg = await self.try_send_message(text=message, chat_id=chat_id)
            if not msg:
                LOGGER.debug("maybe_update_meetup_message(): not msg")
                continue
            LOGGER.debug("maybe_update_meetup_message(): updating...")
            try:
                await self.bot.unpin_chat_message(chat_id=msg.chat_id)
            except telegram.error.BadRequest:
                pass  # nothing to unpin, dismiss
            await self.bot.pin_chat_message(
                message_id=msg.message_id, chat_id=msg.chat_id
            )

    def maybe_update_wiki(self):
        """Check if anybody wrote anything on our wiki."""
        now = time.time()
        if now - self.wiki_last_check < 60:
            return
        msg = mariusz.wiki.build_wiki_message()
        differs = self.wiki_msg != msg
        late_enough = abs(now - self.wiki_last_update) > 60
        no_error = msg and self.wiki_msg
        if differs and late_enough and no_error:
            for chat_id in self.chat_db.list():
                if chat_id == MAIN_CHAT_ID:
                    continue  # don't spam our main group
                self.try_send_message(text=msg, chat_id=chat_id)
                self.wiki_msg = msg
                self.wiki_last_update = now

    def maybe_update_mumble(self):
        """Check if Mumble state changed: we either transitioned from 0 to
        nonzero or the other way around."""
        return
        now = time.time()
        if now - self.mumble_last_check < 60:
            return
        cnt = max(mariusz.mumble.get_mumble_user_count(MUMBLE_SERVER) - 1, 0)
        state_changed = cnt != self.mumble_state
        if state_changed and abs(now - self.mumble_last_update) > 60:
            if cnt > self.mumble_state:
                msg = "Ktoś się pojawił na Mumble. Liczba userów: " + str(cnt)
            else:
                msg = "Ktoś opuścił Mumble. Liczba userów: " + str(cnt)
            for chat_id in self.chat_db.list():
                if chat_id > 0:
                    continue  # skip if it's a private chat instead of a group
                self.try_send_message(text=msg, chat_id=chat_id)
                self.mumble_state = cnt
                self.mumble_last_update = now

    async def run(self):
        """Bot's main loop."""

        msg = f"Bot się wita po restarcie. wersja={self.build_version}"
        await self.send_to_all_chats(msg)

        try:
            updates = await self.bot.get_updates()
            self.update_id = updates[0].update_id
        except IndexError:
            self.update_id = None

        while True:
            try:
                await self.maybe_update_meetup_message()
                self.maybe_update_mumble()
                self.maybe_update_wiki()
                await self.handle_messages()
            except NetworkError:
                await asyncio.sleep(1)
            except Exception:
                formatted_traceback = traceback.format_exc()
                message = f"Bot umar. Traceback:\n\n{formatted_traceback}"
                await self.send_to_all_chats(message)
                await asyncio.sleep(600)
                raise

    async def handle_messages(self):
        """For each unread message, determines whether and how to react."""
        signal.alarm(20)
        updates = await self.bot.get_updates(offset=self.update_id, timeout=10)
        signal.alarm(0)
        for update in updates:
            if update.update_id:
                self.update_id = update.update_id + 1
            if update.message is None or update.message.text is None:
                continue
            if self.chat_db:
                self.chat_db.insert(update.message.chat_id)
            for reaction, funtion in self.reactions.items():
                if reaction.match(update.message.text):
                    await funtion(update)


async def main():
    """Program's entry point. Defined so that we don't polute the global
    namespace with extra variables."""
    logfmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(format=logfmt, level="DEBUG")
    api_key = os.environ["API_KEY"]
    path_to_chat_db = os.environ.get("SCIEZKA_DO_BAZY_CHATOW")
    group_regex = os.environ.get("GROUP_REGEX")
    m = Mariusz(api_key, path_to_chat_db, group_regex)
    await m.run()


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
