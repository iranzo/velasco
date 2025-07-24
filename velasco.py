#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

# from telegram.error import *
from archivist import Archivist
from speaker import Speaker

coloredlogsError = None
try:
    import coloredlogs
except ImportError as e:
    coloredlogsError = e

username = "velascobot"
speakerbot = None

logger = logging.getLogger(__name__)

# Enable logging
log_format = "[{}][%(asctime)s]%(name)s::%(levelname)s: %(message)s".format(
    username.upper()
)

if coloredlogsError:
    logging.basicConfig(format=log_format, level=logging.INFO)
    logger.warning("Unable to load coloredlogs:")
    logger.warning(coloredlogsError)
else:
    coloredlogs.install(level=logging.INFO, fmt=log_format)

start_msg = (
    "Hello there! Ask me for /help to see an overview of the available commands."
)

wake_msg = "Good morning. I just woke up"

help_msg = """I answer to the following commands:

/start - I say hi.
/about - What I'm about.
/explain - I explain how I work.
/help - I send this message.
/count - I tell you how many messages from this chat I remember.
/period - Change the period of my messages. (Maximum of 100000)
/speak - Forces me to speak.
/answer - Change the probability to answer to a reply. (Decimal between 0 and 1).
/restrict - Toggle restriction of configuration commands to admins only.
/silence - Toggle restriction on mentions by the bot.
/who - Tell general information about you and your message. For debugging purposes.
/where - Tell my configuration for this chat.
"""

about_msg = "I am yet another Markov Bot experiment. I read everything you type to me and then spit back nonsensical messages that look like yours.\n\nYou can send /explain if you want further explanation."

explanation = "I decompose every message I read in groups of 3 consecutive words, so for each consecutive pair I save the word that can follow them. I then use this to make my own messages. At first I will only repeat your messages because for each 2 words I will have very few possible following words.\n\nI also separate my vocabulary by chats, so anything I learn in one chat I will only say in that chat. For privacy, you know. Also, I save my vocabulary in the form of a json dictionary, so no logs are kept.\n\nMy default period in private chats is one message of mine from each 2 messages received, and in group chats it's 10 messages I read for each message I send."


def static_reply(text, format=None):
    async def reply(update, context):
        await update.message.reply_text(text, parse_mode=format)

    return reply


def error(update, context):
    logger.warning(
        'The following update:\n"{}"\n\nCaused the following error:\n'.format(update)
    )
    logger.exception(context.error)
    # raise error


def stop(update, context):
    reader = speakerbot.get_reader(str(update.message.chat.id))
    # del chatlogs[chatlog.id]
    # os.remove(LOG_DIR + chatlog.id + LOG_EXT)
    logger.warning("I got blocked by user {} [{}]".format(reader.title(), reader.cid()))


def main():
    global speakerbot
    parser = argparse.ArgumentParser(description="A Telegram markov bot.")
    parser.add_argument(
        "token", metavar="TOKEN", help="The Bot Token to work with the Telegram Bot API"
    )
    parser.add_argument(
        "admin_id",
        metavar="ADMIN_ID",
        type=int,
        default=0,
        help="The ID of the Telegram user that manages this bot",
    )
    parser.add_argument(
        "-w",
        "--wakeup",
        action="store_true",
        help="Flag that makes the bot send a first message to all chats during wake up.",
    )
    parser.add_argument(
        "-f",
        "--filter",
        nargs="*",
        default=None,
        metavar="cid",
        help="Zero or more chat IDs to add in a filter whitelist (default is empty, all chats allowed)",
    )
    parser.add_argument(
        "-n",
        "--nicknames",
        nargs="*",
        default=[],
        metavar="name",
        help="Any possible nicknames that the bot could answer to.",
    )
    parser.add_argument(
        "-d",
        "--directory",
        metavar="CHATLOG_DIR",
        default="./chatlogs",
        help='The chat logs directory path (default: "./chatlogs").',
    )
    parser.add_argument(
        "-c",
        "--capacity",
        metavar="C",
        type=int,
        default=20,
        help="The memory capacity for the last C updated chats. (default: 20).",
    )
    parser.add_argument(
        "-m",
        "--mute_time",
        metavar="T",
        type=int,
        default=60,
        help="The time (in s) for the muting period when Telegram limits the bot. (default: 60).",
    )
    parser.add_argument(
        "-s",
        "--save_time",
        metavar="T",
        type=int,
        default=3600,
        help="The time (in s) for periodic saves. (default: 3600)",
    )
    parser.add_argument(
        "-p",
        "--min_period",
        metavar="MIN_P",
        type=int,
        default=1,
        help="The minimum value for a chat's period. (default: 1)",
    )
    parser.add_argument(
        "-P",
        "--max_period",
        metavar="MAX_P",
        type=int,
        default=100000,
        help="The maximum value for a chat's period. (default: 100000)",
    )

    args = parser.parse_args()

    assert args.max_period >= args.min_period

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(args.token).build()

    filter_cids = args.filter
    if filter_cids:
        filter_cids.append(str(args.admin_id))

    archivist = Archivist(
        logger,
        chatdir=args.directory,
        chatext=".vls",
        min_period=args.min_period,
        max_period=args.max_period,
        read_only=False,
    )

    # We'll get the username after the application starts
    # For now, use a placeholder that will be updated
    username = "velascobot"
    speakerbot = Speaker(
        "@" + username,
        archivist,
        logger,
        admin=args.admin_id,
        cid_whitelist=filter_cids,
        nicknames=args.nicknames,
        wakeup=args.wakeup,
        memory=args.capacity,
        mute_time=args.mute_time,
        save_time=args.save_time,
    )

    # Define a post-init callback to send wake message after bot starts
    async def post_init(app):
        await speakerbot.wake(app.bot, wake_msg)

    # Set the post_init callback on the application
    application.post_init = post_init

    # Add handlers to the application
    application.add_handler(CommandHandler("start", static_reply(start_msg)))
    application.add_handler(CommandHandler("about", static_reply(about_msg)))
    application.add_handler(CommandHandler("explain", static_reply(explanation)))
    application.add_handler(CommandHandler("help", static_reply(help_msg)))
    application.add_handler(CommandHandler("count", speakerbot.get_count))
    application.add_handler(CommandHandler("period", speakerbot.period))
    application.add_handler(
        CommandHandler(
            "list", speakerbot.get_chats, filters=filters.Chat(chat_id=speakerbot.admin)
        )
    )
    # application.add_handler(CommandHandler("user", get_name, filters.Chat(chat_id=archivist.admin)))
    # application.add_handler(CommandHandler("id", get_id))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("speak", speakerbot.speak))
    application.add_handler(CommandHandler("answer", speakerbot.answer))
    application.add_handler(CommandHandler("restrict", speakerbot.restrict))
    application.add_handler(CommandHandler("silence", speakerbot.silence))
    application.add_handler(CommandHandler("who", speakerbot.who))
    application.add_handler(CommandHandler("where", speakerbot.where))

    # on noncommand i.e message - echo the message on Telegram
    # application.add_handler(MessageHandler(filters.TEXT, echo))
    application.add_handler(
        MessageHandler(
            (filters.TEXT | filters.Sticker.ALL | filters.ANIMATION), speakerbot.read
        )
    )

    # log all errors
    application.add_error_handler(error)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
