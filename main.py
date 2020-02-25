#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import telegram
import os
from telegram.error import NetworkError, Unauthorized
from time import sleep

API_KEY = os.environ['API_KEY']

update_id = None

LODZ = [
    'Łódź',
    'Łodzi',
    'Łódzkie',
]

def main():
    """Run the bot."""
    global update_id
    bot = telegram.Bot(API_KEY)

    try:
        update_id = bot.get_updates()[0].update_id
    except IndexError:
        update_id = None

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.info('Dzialam. Chyba.')

    while True:
        try:
            lodz(bot)
        except NetworkError:
            sleep(1)
        except Unauthorized:
            # The user has removed or blocked the bot.
            update_id += 1


def lodz(bot):
    global update_id
    for update in bot.get_updates(offset=update_id, timeout=10):
        update_id = update.update_id + 1
        if update.message is None or update.message.text is None:
            continue
        for word in LODZ:
            if update.message.text.startswith('.wersja'):
                with open('/tmp/commit-id') as f:
                    update.message.reply_text(f.read())
            if word in update.message.text:
                update.message.reply_text('https://www.youtube.com/watch?v=IJ2kvZpJ_BU ^^')


if __name__ == '__main__':
    main()
