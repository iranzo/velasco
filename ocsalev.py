#!/usr/bin/env python3

# FAILED ATTEMPT TO MAKE BOT THAT USES VELASCO MEMORY IN ALL GROUPS SIMULTANEOUSLY

import sys, os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import *
from markov import *
from velasco import GUILLERMO_ID, LOG_DIR, LOG_EXT
import logging
import argparse

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

generator = Markov()
chatfreqs = {}

DEFAULT_FREQ = 10

def parse_file(text):
    lines = text.splitlines()
    if lines[1] != "private":
        ident = lines[0]
        freq = int(lines[3])
        chatfreqs[ident] = (freq, 0)
        if lines[4] == "dict:":
            cache = '\n'.join(lines[5:])
            gen = Markov.from_json(cache)
            return gen
        else:
            return Markov(lines[4:])
    else:
        return Markov()

def load_gen(path):
    open_file = open(path, 'r')
    gen = parse_file(open_file.read())
    open_file.close()
    return gen

def wake(bot):
    global generator
    directory = os.fsencode(LOG_DIR)

    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith(LOG_EXT):
            gen = load_gen(LOG_DIR + filename)
            generator.fuse_with(gen)

def start(bot, update):
    update.message.reply_text('WHADDUP NERD')

def help(bot, update):
    update.message.reply_text("""I ANSWER TO

/start - HELLO
/about - MY BIOGRAPHY
/help - THIS
/freq - HOW LONG I WAIT TO SPEAK
/speak - I SPEAK
    """)

def about(bot, update):
    update.message.reply_text('I AM LIKE @velascobot BUT STRONGER. THE TRUE SELF')

def echo(bot, update):
    text = update.message.text.split(None, 2)
    if len(text) > 1:
        text = text[1]
        update.message.reply_text(text)

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def read(bot, update):
    global generator
    if not "group" in update.message.chat.type:
        update.message.reply_text("I ONLY TALK IN GROUPS")
        return
    generator.add_text(update.message.text + TAIL)
    chat = update.message.chat
    ident = str(chat.id)
    if not ident in chatfreqs:
        chatfreqs[ident] = (DEFAULT_FREQ, 0)
    freq, count = chatfreqs[ident]
    if count%freq == 0:
        msg = generator.generate_markov_text()
        try:
            bot.sendMessage(ident, msg)
            count = 0
        except TimedOut:
            chatfreqs[ident] = (freq + CHAT_INC, count)
            print("Increased freq for chat " + chat.title + " [" + ident + "]")
    chatfreqs[ident] = (freq, count+1)

def speak(bot, update):
    global generator
    if not "group" in update.message.chat.type:
        update.message.reply_text("I ONLY TALK IN GROUPS")
        return
    chat = update.message.chat
    ident = str(chat.id)
    if not ident in chatfreqs:
        chatfreqs[ident] = (DEFAULT_FREQ, 0)
    msg = generator.generate_markov_text()
    update.message.reply_text(msg)

def get_chatlogs(bot, update):
    if str(update.message.chat.id) == GUILLERMO_ID:
        bot.sendMessage(GUILLERMO_ID, "HECK YOU")

def set_freq(bot, update):
    ident = str(update.message.chat.id)
    if not ident in chatfreqs:
        chatfreqs[ident] = (DEFAULT_FREQ, 0)
    freq, count = chatfreqs[ident]
    if not len(update.message.text.split()) > 1:
        reply = "I WAIT FOR " + str(freq) + " MESSAGES"
    else:
        try:
            value = update.message.text.split()[1]
            value = int(value)
            chatfreqs[ident] = (value, count)
            reply = "I NOW WAIT FOR " + str(value) + " MESSAGES"
            if value > freq:
                reply += "\nYOU WILL NOT SILENCE ME"
        except:
            reply = "WHAT THE HECK. IMMA STILL WAIT FOR " + str(freq) + " MESSAGES"
    update.message.reply_text(reply)

def stop(bot, update):
    chat = update.message.chat
    ident = str(chat.id)
    del chatfreqs[ident]

def main():
    parser = argparse.ArgumentParser(description='A Telegram markovbot.')
    parser.add_argument('token', metavar='TOKEN', help='The Bot Token to work with the Telegram Bot API')

    args = parser.parse_args()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(args.token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("about", about))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("freq", set_freq))
    dp.add_handler(CommandHandler("list", get_chatlogs))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("speak", speak))

    # on noncommand i.e message - echo the message on Telegram
    # dp.add_handler(MessageHandler(Filters.text, echo))
    dp.add_handler(MessageHandler(Filters.text, read))

    # log all errors
    dp.add_error_handler(error)

    wake(updater.bot)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
