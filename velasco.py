#!/usr/bin/env python3

import sys, os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from chatlog import *
import logging
import argparse

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

chatlogs = {}
disabled = {}

GUILLERMO_ID = 8379173

def wake(bot):
    directory = os.fsencode("chatlogs/")

    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith(".txt"):
            chat = loadchat("chatlogs/" + filename)
            chatlogs[chat.id] = chat
            print("loaded chat " + chat.id)
            continue
        else:
            continue
"""
    for c in chatlogs:
        try:
            bot.sendMessage(chatlogs[c].id, "Good morning. I just woke up")
        except:
            pass
            #del chatlogs[c]
"""

def start(bot, update):
    update.message.reply_text('cowabunga')

def savechat(chatlog):
    open_file = open('chatlogs/' + chatlog.id + '.txt', 'w')
    open_file.write(chatlog.to_txt())
    open_file.close()

def loadchat(path):
    open_file = open(path, 'r')
    chat = Chatlog.from_txt(open_file.read())
    open_file.close()
    return chat

def help(bot, update):
    update.message.reply_text("""I answer to the following commands:

/start - I say hi.
/about - What I'm about.
/help - I send this message.
/count - I tell you how many messages from this chat I remember.
/freq - Change the frequency of both my messages and the times I save my learned vocabulary. (Maximum of 100000)
/speak - Forces me to speak.
    """)

def about(bot, update):
    update.message.reply_text('I am yet another Markov Bot experiment. I read everything you type to me and then spit back nonsensical messages that look like yours')

def echo(bot, update):
    update.message.reply_text(update.message.text)

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def get_chatname(chat):
    if chat.title is not None:
        return chat.title
    elif chat.first_name is not None:
        if chat.last_name is not None:
            return chat.first_name + " " + chat.last_name
        else:
            return chat.first_name
    else:
        return ""

def read(bot, update):
    global chatlogs
    chat = update.message.chat
    ident = str(chat.id)
    if not ident in chatlogs:
        title = get_chatname(chat)
        chatlog = Chatlog(chat.id, chat.type, title)
    else:
        chatlog = chatlogs[ident]
    chatlog.add_msg(update.message.text)
    if chatlog.get_count()%chatlog.freq == 0:
        msg = chatlog.speak()
        # TO DO: añadir % de que haga reply en vez de send
        try:
            bot.sendMessage(chatlog.id, msg)
        except TelegramError:
            chatlog.set_freq(chatlog.freq + 20)
        if get_chatname(chat) != chatlog.title:
            chatlog.set_title(get_chatname(chat))
        savechat(chatlog)

    chatlogs[chatlog.id] = chatlog

def speak(bot, update):
    global chatlogs
    ident = str(update.message.chat.id)
    if not ident in chatlogs:
        chat = update.message.chat
        title = get_chatname(chat)
        chatlog = Chatlog(chat.id, chat.type, title)
    else:
        chatlog = chatlogs[ident]
    text = update.message.text.split()
    if len(text) > 1:
        chatlog.add_msg(' '.join(text[1:]))
    msg = chatlog.speak()
    update.message.reply_text(msg)
    savechat(chatlog)

    chatlogs[chatlog.id] = chatlog

def get_chatlogs(bot, update):
    global GUILLERMO_ID
    if update.message.chat.id is GUILLERMO_ID:
        m = "I have these chatlogs:"
        for c in chatlogs:
            m += "\n" + chatlogs[c].id + " " + chatlogs[c].title
        bot.sendMessage(GUILLERMO_ID, m)

def get_count(bot, update):
    ident = str(update.message.chat.id)
    reply = "I remember "
    if ident in chatlogs:
        reply += str(chatlogs[ident].get_count())
    else:
        reply += "no"
    reply += " messages."
    update.message.reply_text(reply)

def set_freq(bot, update):
    ident = str(update.message.chat.id)
    if not ident in chatlogs:
        chat = update.message.chat
        title = get_chatname(chat)
        chatlog = Chatlog(chat.id, chat.type, title)
        chatlogs[chatlog.id] = chatlog
    if not len(update.message.text.split()) > 1:
        reply = "Current frequency is " + str(chatlogs[ident].freq)
    else:
        try:
            value = update.message.text.split()[1]
            value = int(value)
            value = chatlogs[ident].set_freq(value)
            reply = "Frequency of speaking set to " + str(value)
        except:
            reply = "Format was confusing; frequency not changed from " + str(chatlogs[ident].freq)
    update.message.reply_text(reply)

def stop(bot, update):
    chatlog = chatlogs[update.message.chat.id]
    del chatlogs[chatlog.id]
    os.remove("chatlogs/" + chatlog.id + ".txt")
    print("I got blocked. Removed user " + chatlog.id)

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
    dp.add_handler(CommandHandler("count", get_count))
    dp.add_handler(CommandHandler("freq", set_freq))
    dp.add_handler(CommandHandler("list", get_chatlogs))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("speak", speak))

    # on noncommand i.e message - echo the message on Telegram
    # dp.add_handler(MessageHandler(Filters.text, echo))
    dp.add_handler(MessageHandler(Filters.text, read))

    # chatlog all errors
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
