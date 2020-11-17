#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import time
from sys import stderr
from memorylist import MemoryList
from reader import Reader, get_chat_title
from telegram.error import NetworkError


# Auxiliar print to stderr function (alongside logger messages)
def eprint(*args, **kwargs):
    print(*args, end=" ", file=stderr, **kwargs)


# Auxiliar message to send a text to a chat through a bot
def send(bot, cid, text, replying=None, formatting=None, logger=None, **kwargs):
    # Markdown or HTML formatting (both argument names are valid)
    kwargs["parse_mode"] = formatting or kwargs.get("parse_mode")
    # ID of the message it's replying to (both argument names are valid)
    kwargs["reply_to_message_id"] = replying or kwargs.get("reply_to_message_id")
    # Reminder that dict.get(key) defaults to None if the key isn't found

    if text.startswith(Reader.TAG_PREFIX):
        # We're sending a media file ID
        words = text.split(maxsplit=1)
        if logger:
            logger.info('Sending {} "{}" to {}'.format(words[0][4:-1], words[1], cid))
            # Logs something like 'Sending VIDEO "VIDEO_ID" to CHAT_ID'

        if words[0] == Reader.STICKER_TAG:
            return bot.send_sticker(cid, words[1], **kwargs)
        elif words[0] == Reader.ANIM_TAG:
            return bot.send_animation(cid, words[1], **kwargs)
        elif words[0] == Reader.VIDEO_TAG:
            return bot.send_video(cid, words[1], **kwargs)
    else:
        # It's text
        if logger:
            mtype = "reply" if (kwargs.get("reply_to_message_id")) else "message"
            logger.info("Sending a {} to {}: '{}'".format(mtype, cid, text))
            # eprint('.')
        return bot.send_message(cid, text, **kwargs)


class Speaker(object):
    # Marks if the period is a fixed time when to send a new message
    ModeFixed = "FIXED_MODE"
    # Marks if the "periodic" messages have a weighted random chance to be sent, depending on the period
    ModeChance = "CHANCE_MODE"

    def __init__(
        self,
        username,
        archivist,
        logger,
        admin=0,
        nicknames=[],
        reply=0.1,
        repeat=0.05,
        wakeup=False,
        mode=ModeFixed,
        memory=20,
        mute_time=60,
        save_time=3600,
        bypass=False,
        cid_whitelist=None,
        max_len=50,
    ):
        # List of nicknames other than the username that the bot can be called as
        self.names = nicknames
        # Mute time for Telegram network errors
        self.mute_time = mute_time
        # Last mute timestamp
        self.mute_timer = None
        # The bot's username, "@" included
        self.username = username
        # The minimum and maximum chat period for this bot
        self.min_period = archivist.min_period
        self.max_period = archivist.max_period

        # The Archivist functions to load and save from and to files
        self.get_reader_file = archivist.get_reader
        self.store_file = archivist.store

        # Archivist function to crawl all stored Readers
        self.readers_pass = archivist.readers_pass

        # Legacy load logging emssages
        logger.info("----")
        logger.info("Finished loading.")
        logger.info("Loaded {} chats.".format(archivist.chat_count()))
        logger.info("----")

        # Wakeup flag that determines if it should send a wakeup message to stored groupchats
        self.wakeup = wakeup
        # The logger shared program-wide
        self.logger = logger
        # Chance of sending messages as replies
        self.reply = reply
        # Chance of sending 2 messages in a row
        self.repeat = repeat
        # If not empty, whitelist of chat IDs to only respond to
        self.cid_whitelist = cid_whitelist
        # Memory list/cache for the last accessed chats
        self.memory = MemoryList(memory)
        # Minimum time to wait between memory saves (triggered at the next message from any chat)
        self.save_time = save_time
        # Last save timestamp
        self.memory_timer = int(time.perf_counter())
        # Admin user ID
        self.admin = admin
        # For testing purposes
        self.bypass = bypass
        # Max word length for a message
        self.max_len = max_len

    # Sends an announcement to all chats that pass the check
    def announce(self, bot, announcement, check=(lambda _: True)):
        for reader in self.readers_pass():
            try:
                if check(reader):
                    send(bot, reader.cid(), announcement)
                    self.logger.info(
                        "Sending announcement to chat {}".format(reader.cid())
                    )
            except Exception:
                pass

    # If wakeup flag is set, sends a wake-up message as announcement to all chats that
    # are groups. Also, always sends a wakeup message to the 'bot admin'
    def wake(self, bot, wake):
        send(bot, self.admin, wake)

        if self.wakeup:

            def group_check(reader):
                return reader.check_type("group")

            self.announce(bot, wake, group_check)

    # Looks up a reader in the memory list
    def get_reader(self, cid):
        return self.memory.search(lambda r: r.cid() == cid, None)

    # Looks up and returns a reader if it's in memory, or loads up a reader from
    # file, adds it to memory, and returns it. Any other reader pushed out of
    # memory is saved to file
    def load_reader(self, chat):
        cid = str(chat.id)
        reader = self.get_reader(cid)
        if reader is not None:
            return reader

        reader = self.get_reader_file(cid)
        if not reader:
            reader = Reader.FromChat(
                chat, self.min_period, self.max_period, self.logger
            )

        old_reader = self.memory.add(reader)
        if old_reader is not None:
            old_reader.commit_memory()
            self.store(old_reader)

        return reader

    # Returns a reader if it's in memory, or loads it up from a file and returns
    # it otherwise. Does NOT add the Reader to memory
    # This is useful for command prompts that do not require the Reader to be cached
    def access_reader(self, cid):
        reader = self.get_reader(cid)
        if reader is None:
            return self.get_reader_file(cid)
        return reader

    # Returns True if the bot's username is called, or if one of the nicknames is
    # mentioned and they're not another user's username
    def mentioned(self, text):
        if self.username in text:
            return True
        for name in self.names:
            if name in text and "@{}".format(name) not in text:
                return True
        return False

    # Returns True if not enough time has passed since the last mute timestamp
    def is_mute(self):
        current_time = int(time.perf_counter())
        return (
            self.mute_timer is not None
            and (current_time - self.mute_timer) < self.mute_time
        )

    # Series of checks to determine if the bot should reply to a specific message, aside
    # from the usual periodic messages
    def should_reply(self, message, reader):
        if self.is_mute():
            # Not if mute time hasn't finished
            return False
        if not self.bypass and reader.is_restricted():
            # If we're not in testing mode and the chat is restricted
            user = message.chat.get_member(message.from_user.id)
            if not self.user_is_admin(user):
                # ...And the user has no permissions, should not reply
                return False

        # otherwise (testing mode, or the chat is unrestricted, or the user has permissions)
        replied = message.reply_to_message
        text = message.text.casefold() if message.text else ""
        # Only if it's a reply to a message of ours or the bot is mentioned in the message
        return (
            (replied is not None) and (replied.from_user.name == self.username)
        ) or (self.mentioned(text))

    def store(self, reader):
        if reader is None:
            raise ValueError("Tried to store a None Reader.")
        else:
            self.store_file(*reader.archive())

    # Check if enough time for saving memory has passed
    def should_save(self):
        current_time = int(time.perf_counter())
        elapsed = current_time - self.memory_timer
        self.logger.debug("Save check: {}".format(elapsed))
        return elapsed >= self.save_time

    # Save all Readers in memory to files if it's save time
    def save(self):
        if self.should_save():
            self.logger.info("Saving chats in memory...")
            for reader in self.memory:
                self.store(reader)
            self.memory_timer = time.perf_counter()
            self.logger.info("Chats saved.")

    # Reads a non-command message
    def read(self, update, context):
        # Check for save time
        self.save()

        # Ignore non-message updates
        if update.message is None:
            return

        chat = update.message.chat
        reader = self.load_reader(chat)
        reader.read(update.message)

        # Check if it's a "replyable" message & roll the chance to do so
        if self.should_reply(update.message, reader) and reader.is_answering():
            self.say(context.bot, reader, replying=update.message.message_id)
            return

        # Update the Reader's title if it has changed since the last message read
        title = get_chat_title(update.message.chat)
        if title != reader.title():
            reader.set_title(title)

        # Decrease the countdown for the chat, and send a message if it reached 0
        reader.countdown -= 1
        if reader.countdown < 0:
            reader.reset_countdown()
            # Random chance to reply to a recent message
            rid = reader.random_memory() if random.random() <= self.reply else None
            self.say(context.bot, reader, replying=rid)

    # Handles /speak command
    def speak(self, update, context):
        chat = update.message.chat
        reader = self.load_reader(chat)

        if not self.bypass and reader.is_restricted():
            user = update.message.chat.get_member(update.message.from_user.id)
            if not self.user_is_admin(user):
                # update.message.reply_text("You do not have permissions to do that.")
                return

        mid = str(update.message.message_id)
        replied = update.message.reply_to_message
        # Reply to the message that the command replies to, otherwise to the command itself
        rid = replied.message_id if replied else mid
        words = update.message.text.split()
        if len(words) > 1:
            reader.read(" ".join(words[1:]))
        self.say(context.bot, reader, replying=rid)

    # Checks user permissions. Bot admin is always considered as having full permissions
    def user_is_admin(self, member):
        self.logger.info(
            "user {} ({}) requesting a restricted action".format(
                str(member.user.id), member.user.name
            )
        )
        # eprint('!')
        # self.logger.info("Bot Creator ID is {}".format(str(self.admin)))
        return (
            (member.status == "creator")
            or (member.status == "administrator")
            or (member.user.id == self.admin)
        )

    # Generate speech (message)
    def speech(self, reader):
        return reader.generate_message(self.max_len)

    # Say a newly generated message
    def say(self, bot, reader, replying=None, **kwargs):
        cid = reader.cid()
        if self.cid_whitelist is not None and cid not in self.cid_whitelist:
            # Don't, if there's a whitelist and this chat is not in it
            return
        if self.is_mute():
            # Don't, if mute time isn't over
            return

        try:
            send(bot, cid, self.speech(reader), replying, logger=self.logger, **kwargs)
            if self.bypass:
                # Testing mode, force a reasonable period (to not have the bot spam one specific chat with a low period)
                minp = self.min_period
                maxp = self.max_period
                rangep = maxp - minp
                reader.set_period(random.randint(rangep // 4, rangep) + minp)
            if random.random() <= self.repeat:
                send(bot, cid, self.speech(reader), logger=self.logger, **kwargs)
        # Consider any Network Error as a Telegram temporary ban, as I couldn't find
        # out in the documentation how error 429 is handled by python-telegram-bot
        except NetworkError as e:
            self.logger.error("Sending a message caused network error:")
            self.logger.exception(e)
            self.logger.error("Going mute for {} seconds.".format(self.mute_time))
            self.mute_timer = int(time.perf_counter())
        except Exception as e:
            self.logger.error("Sending a message caused exception:")
            self.logger.exception(e)

    # Handling /count command
    def get_count(self, update, context):
        cid = str(update.message.chat.id)
        reader = self.load_reader(cid)

        num = str(reader.count()) if reader else "no"
        update.message.reply_text("I remember {} messages.".format(num))

    # Handling /get_chats command (exclusive for bot admin)
    def get_chats(self, update, context):
        lines = [
            "[{}]: {}".format(reader.cid(), reader.title())
            for reader in self.readers_pass()
        ]
        chat_list = "\n".join(lines)
        update.message.reply_text("I have the following chats:\n\n" + chat_list)

    # Handling /period command
    # Print the current period or set a new one if one is given
    def period(self, update, context):
        chat = update.message.chat
        reader = self.load_reader(str(chat.id))

        words = update.message.text.split()
        if len(words) <= 1:
            update.message.reply_text(
                "The current speech period is {}".format(reader.period())
            )
            return

        if reader.is_restricted():
            user = update.message.chat.get_member(update.message.from_user.id)
            if not self.user_is_admin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        try:
            period = int(words[1])
            period = reader.set_period(period)
            update.message.reply_text("Period of speaking set to {}.".format(period))
        except Exception:
            update.message.reply_text(
                "Format was confusing; period unchanged from {}.".format(
                    reader.period()
                )
            )

    # Handling /answer command
    # Print the current answer probability or set a new one if one is given
    def answer(self, update, context):
        chat = update.message.chat
        reader = self.load_reader(str(chat.id))

        words = update.message.text.split()
        if len(words) <= 1:
            update.message.reply_text(
                "The current answer probability is {}".format(reader.answer())
            )
            return

        if reader.is_restricted():
            user = update.message.chat.get_member(update.message.from_user.id)
            if not self.user_is_admin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        try:
            answer = float(words[1])
            answer = reader.set_answer(answer)
            update.message.reply_text("Answer probability set to {}.".format(answer))
        except Exception:
            update.message.reply_text(
                "Format was confusing; answer probability unchanged from {}.".format(
                    reader.answer()
                )
            )

    # Handling /restrict command
    # Toggle the restriction value if it's a group chat and the user has permissions to do so
    def restrict(self, update, context):
        if "group" not in update.message.chat.type:
            update.message.reply_text("That only works in groups.")
            return
        chat = update.message.chat
        user = chat.get_member(update.message.from_user.id)
        reader = self.load_reader(str(chat.id))

        if reader.is_restricted():
            if not self.user_is_admin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        reader.toggle_restrict()
        allowed = "let only admins" if reader.is_restricted() else "let everyone"
        update.message.reply_text("I will {} configure me now.".format(allowed))

    # Handling /silence command
    # Toggle the silence value if it's a group chat and the user has permissions to do so
    def silence(self, update, context):
        if "group" not in update.message.chat.type:
            update.message.reply_text("That only works in groups.")
            return
        chat = update.message.chat
        user = chat.get_member(update.message.from_user.id)
        reader = self.load_reader(str(chat.id))

        if reader.is_restricted():
            if not self.user_is_admin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        reader.toggle_silence()
        allowed = "avoid mentioning" if reader.is_silenced() else "mention"
        update.message.reply_text("I will {} people now.".format(allowed))

    # Handling /who command
    def who(self, update, context):
        msg = update.message
        usr = msg.from_user
        cht = msg.chat
        chtname = cht.title if cht.title else cht.first_name
        rdr = self.access_reader(str(cht.id))

        answer = (
            "You're **{name}**, with username `{username}`, and "
            "id `{uid}`.\nYou're messaging in the chat named __{cname}__,"
            " of type {ctype}, with id `{cid}`, and timestamp `{tstamp}`."
        ).format(
            name=usr.full_name,
            username=usr.username,
            uid=usr.id,
            cname=chtname,
            cid=cht.id,
            ctype=rdr.ctype(),
            tstamp=str(msg.date),
        )

        msg.reply_markdown(answer)

    # Handling /where command
    def where(self, update, context):
        msg = update.message
        chat = msg.chat
        reader = self.access_reader(str(chat.id))
        if reader.is_restricted() and reader.is_silenced():
            permissions = "restricted and silenced"
        elif reader.is_restricted():
            permissions = "restricted but not silenced"
        elif reader.is_silenced():
            permissions = "not restricted but silenced"
        else:
            permissions = "neither restricted nor silenced"

        answer = (
            "You're messaging in the chat of saved title __{cname}__,"
            " with id `{cid}`, message count {c}, period {p}, and answer "
            "probability {a}.\n\nThis chat is {perm}."
        ).format(
            cname=reader.title(),
            cid=reader.cid(),
            c=reader.count(),
            p=reader.period(),
            a=reader.answer(),
            perm=permissions,
        )

        msg.reply_markdown(answer)
