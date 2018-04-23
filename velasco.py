#!/usr/bin/env python3

import sys, os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import *
from chatlog import *
import logging
import argparse
import random

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - velascobot',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

chatlogs = {}

ADMIN_ID = 0
CHAT_INC = 5
CHAT_SAVE = 15
LOG_DIR = "chatlogs/"
LOG_EXT = ".txt"
REPL_CHANCE = 10/100
REPT_CHANCE = 5/100

def wake(bot):
    directory = os.fsencode(LOG_DIR)

    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith(LOG_EXT):
            chat = loadchat(LOG_DIR + filename)
            if chat is not None:
                chatlogs[chat.id] = chat
                print("loaded chat " + chat.title + " [" + chat.id + "]")
            continue
        else:
            continue
"""
    for c in chatlogs:
        try:
            send_message(bot, update, "Good morning. I just woke up", False)
        except:
            pass
            #del chatlogs[c]
"""

def start(bot, update):
    update.message.reply_text()

def savechat(chatlog):
    open_file = open(LOG_DIR + chatlog.id + LOG_EXT, 'w')
    open_file.write(chatlog.to_txt())
    open_file.close()

def loadchat(path):
    #print("Loading chat: " + path)
    open_file = open(path, 'r')
    chat = None
    try:
        chat = Chatlog.from_txt(open_file.read())
    except:
        pass
    open_file.close()
    return chat

def help(bot, update):
    update.message.reply_text("""I answer to the following commands:

/start - I say hi.
/about - What I'm about.
/explain - I explain how I work.
/help - I send this message.
/count - I tell you how many messages from this chat I remember.
/freq - Change the frequency of my messages. (Maximum of 100000)
/speak - Forces me to speak.
/answer - Change the probability to answer to a reply. (Decimal between 0 and 1)
    """)

def about(bot, update):
    update.message.reply_text('I am yet another Markov Bot experiment. I read everything you type to me and then spit back nonsensical messages that look like yours\n\nYou can send /explain if you want further explanation')

def explain(bot, update):
    update.message.reply_text('I decompose every message I read in groups of 3 consecutive words, so for each consecutive pair I save the word that can follow them. I then use this to make my own messages. At first I will only repeat your messages because for each 2 words I will have very few possible following words.\n\nI also separate my vocabulary by chats, so anything I learn in one chat I will only say in that chat. For privacy, you know. Also, I save my vocabulary in the form of a json dictionary, so no logs are kept.\n\nMy default frequency in private chats is one message of mine from each 2 messages received, and in group chats it\'s 10 messages I read for each message I send.')

def echo(bot, update):
    text = update.message.text.split(None, maxsplit=1)
    if len(text) > 1:
        text = text[1]
        chatlog.add_msg(text)
        update.message.reply_text(text)

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

    if update.message.text is not None:
        chatlog.add_msg(update.message.text)
    elif update.message.sticker is not None:
        chatlog.add_sticker(update.message.sticker.file_id)

    replied = update.message.reply_to_message
    if (replied is not None) and (replied.from_user.name == "@velascobot") and chatlog.answering(random.random()):
        print("They're talking to me, I'm answering back")
        msg = chatlog.speak()
        send_message(bot, update, msg, True)
        if random.random() <= REPT_CHANCE:
            msg = chatlog.speak()
            send_message(bot, update, msg, False)
    elif chatlog.get_count()%chatlog.freq == 0:
        msg = chatlog.speak()
        try:
            if random.random() <= REPL_CHANCE:
                print("I made a reply")
                send_message(bot, update, msg, True)
            else:
                print("I sent a message")
                send_message(bot, update, msg, False)
            if random.random() <= REPT_CHANCE:
                print("And a followup")
                msg = chatlog.speak()
                send_message(bot, update, msg, False)
        except TimedOut:
            chatlog.set_freq(chatlog.freq + CHAT_INC)
            print("Increased freq for chat " + chatlog.title + " [" + chatlog.id + "]")
        if get_chatname(chat) != chatlog.title:
            chatlog.set_title(get_chatname(chat))
        savechat(chatlog)
    elif chatlog.freq > CHAT_SAVE and chatlog.get_count()%CHAT_SAVE == 0:
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
    send_message(bot, update, msg, True)
    savechat(chatlog)
    chatlogs[chatlog.id] = chatlog

def send_message(bot, update, msg, is_reply):
    words = msg.split()
    if words[0] == STICKER_TAG:
        if is_reply:
            update.message.reply_sticker(words[1])
        else:
            bot.sendSticker(update.message.chat_id, words[1])
    elif is_reply:
        update.message.reply_text(msg)
    else:
        bot.sendMessage(update.message.chat.id, msg)

def get_chatlogs(bot, update):
    m = "I have these chatlogs:"
    for c in chatlogs:
        m += "\n" + chatlogs[c].id + " " + chatlogs[c].title
    send_message(bot, update, msg, True)

def get_id(bot, update):
    update.message.reply_text("This chat's id is: " + str(update.message.chat.id))

def get_name(bot, update):
    update.message.reply_text("Your name is: " + update.message.from_user.name)

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
            savechat(chatlogs[ident])
        except:
            reply = "Format was confusing; frequency not changed from " + str(chatlogs[ident].freq)
    update.message.reply_text(reply)

def set_answer_freq(bot, update):
    ident = str(update.message.chat.id)
    if not ident in chatlogs:
        chat = update.message.chat
        title = get_chatname(chat)
        chatlog = Chatlog(chat.id, chat.type, title)
        chatlogs[chatlog.id] = chatlog
    if not len(update.message.text.split()) > 1:
        reply = "Current answer probability is " + str(chatlogs[ident].answer)
    else:
        try:
            value = update.message.text.split()[1]
            value = float(value)
            value = chatlogs[ident].set_answer_freq(value)
            reply = "Probability of answering set to " + str(value)
            savechat(chatlogs[ident])
        except:
            reply = "Format was confusing; answer probability not changed from " + str(chatlogs[ident].answer)
    update.message.reply_text(reply)

def stop(bot, update):
    global ADMIN_ID
    chatlog = chatlogs[update.message.chat.id]
    #del chatlogs[chatlog.id]
    #os.remove(LOG_DIR + chatlog.id + LOG_EXT)
    print("I got blocked by user " + chatlog.id)

def main():
    parser = argparse.ArgumentParser(description='A Telegram markov bot.')
    parser.add_argument('token', metavar='TOKEN', help='The Bot Token to work with the Telegram Bot API')
    parser.add_argument('admin_id', metavar='ADMIN_ID', type=int, help='The ID of the Telegram user that manages this bot')

    args = parser.parse_args()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(args.token)
    ADMIN_ID = args.admin_id

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("about", about))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("count", get_count))
    dp.add_handler(CommandHandler("freq", set_freq))
    dp.add_handler(CommandHandler("list", get_chatlogs, Filters.chat(args.admin_id)))
    dp.add_handler(CommandHandler("user", get_name, Filters.chat(args.admin_id)))
    dp.add_handler(CommandHandler("id", get_id))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("speak", speak))
    dp.add_handler(CommandHandler("answer", set_answer_freq))

    # on noncommand i.e message - echo the message on Telegram
    # dp.add_handler(MessageHandler(Filters.text, echo))
    dp.add_handler(MessageHandler((Filters.text | Filters.sticker), read))

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
