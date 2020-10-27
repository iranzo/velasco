#!/usr/bin/env python3

import random
import time
from sys import stderr
from memorylist import MemoryList
from reader import Reader, get_chat_title
from telegram.error import NetworkError


def eprint(*args, **kwargs):
    print(*args, end=' ', file=stderr, **kwargs)


def send(bot, cid, text, replying=None, formatting=None, logger=None, **kwargs):
    kwargs["parse_mode"] = formatting
    kwargs["reply_to_message_id"] = replying

    if text.startswith(Reader.TAG_PREFIX):
        words = text.split(maxsplit=1)
        if logger:
            logger.info('Sending {} "{}" to {}'.format(words[0][4:-1], words[1], cid))
            # eprint('[]')
            # Logs something like 'Sending VIDEO "VIDEO_ID" to CHAT_ID'

        if words[0] == Reader.STICKER_TAG:
            return bot.send_sticker(cid, words[1], **kwargs)
        elif words[0] == Reader.ANIM_TAG:
            return bot.send_animation(cid, words[1], **kwargs)
        elif words[0] == Reader.VIDEO_TAG:
            return bot.send_video(cid, words[1], **kwargs)
    else:
        text
        if logger:
            mtype = "reply" if replying else "message"
            logger.info("Sending a {} to {}: '{}'".format(mtype, cid, text))
            # eprint('.')
        return bot.send_message(cid, text, **kwargs)


class Speaker(object):
    ModeFixed = "FIXED_MODE"
    ModeChance = "CHANCE_MODE"

    def __init__(self, username, archivist, logger, admin=0, nicknames=[],
                 reply=0.1, repeat=0.05, wakeup=False, mode=ModeFixed,
                 memory=20, mute_time=60, save_time=3600, bypass=False,
                 filter_cids=[], max_len=50
                 ):
        self.names = nicknames
        self.mute_time = mute_time
        self.mute_timer = None
        self.username = username

        self.max_period = archivist.max_period
        self.get_reader_file = archivist.get_reader
        self.store_file = archivist.store
        self.readers_pass = archivist.readers_pass

        logger.info("----")
        logger.info("Finished loading.")
        logger.info("Loaded {} chats.".format(archivist.chat_count()))
        logger.info("----")

        self.wakeup = wakeup
        self.logger = logger
        self.reply = reply
        self.repeat = repeat
        self.filter_cids = filter_cids
        self.memory = MemoryList(memory)
        self.save_time = save_time
        self.memory_timer = int(time.perf_counter())
        self.admin = admin
        self.bypass = bypass
        self.max_len = max_len

    def announce(self, bot, announcement, check=(lambda _: True)):
        # Sends an announcement to all chats that pass the check
        for reader in self.readers_pass():
            try:
                if check(reader):
                    send(bot, reader.cid(), announcement)
                    self.logger.info("Sending announcement to chat {}".format(reader.cid()))
            except Exception:
                pass

    def wake(self, bot, wake):
        # If wakeup flag is set, sends a wake-up message as announcement to all chats that
        # are groups. Also, always sends a wakeup message to the 'bot admin'
        send(bot, self.admin, wake)

        if self.wakeup:
            def group_check(reader):
                return reader.check_type("group")
            self.announce(bot, wake, group_check)

    def get_reader(self, cid):
        return self.memory.get_next(lambda r: r.cid() == cid)

    def load_reader(self, chat):
        cid = str(chat.id)
        reader = self.get_reader(cid)
        if reader is not None:
            return reader

        reader = self.get_reader_file(cid)
        if not reader:
            reader = Reader.FromChat(chat, self.max_period, self.logger)

        old_reader = self.memory.append(reader)
        if old_reader is not None:
            old_reader.commit_memory()
            self.store(old_reader)

        return reader

    def access_reader(self, cid):
        reader = self.get_reader(cid)
        if reader is None:
            return self.get_reader_file(cid)
        return reader

    def mentioned(self, text):
        if self.username in text:
            return True
        for name in self.names:
            if name in text and "@{}".format(name) not in text:
                return True
        return False

    def is_mute(self):
        current_time = int(time.perf_counter())
        return self.mute_timer is not None and (current_time - self.mute_timer) < self.mute_time

    def should_reply(self, message, reader):
        if self.is_mute():
            return False
        if not self.bypass and reader.is_restricted():
            user = message.chat.get_member(message.from_user.id)
            if not self.user_is_admin(user):
                # update.message.reply_text("You do not have permissions to do that.")
                return False
        replied = message.reply_to_message
        text = message.text.casefold() if message.text else ""
        return (((replied is not None) and (replied.from_user.name == self.username))
                or (self.mentioned(text)))

    def store(self, reader):
        if reader is None:
            raise ValueError("Tried to store a None Reader.")
        else:
            self.store_file(*reader.archive())

    def should_save(self):
        current_time = int(time.perf_counter())
        elapsed = (current_time - self.memory_timer)
        self.logger.debug("Save check: {}".format(elapsed))
        return elapsed >= self.save_time

    def save(self):
        if self.should_save():
            self.logger.info("Saving chats in memory...")
            for reader in self.memory:
                self.store(reader)
            self.memory_timer = time.perf_counter()
            self.logger.info("Chats saved.")

    def read(self, update, context):
        self.save()

        if update.message is None:
            return
        chat = update.message.chat
        reader = self.load_reader(chat)
        reader.read(update.message)

        if self.should_reply(update.message, reader) and reader.is_answering():
            self.say(context.bot, reader, replying=update.message.message_id)
            return

        title = get_chat_title(update.message.chat)
        if title != reader.title():
            reader.set_title(title)

        reader.countdown -= 1
        if reader.countdown < 0:
            reader.reset_countdown()
            rid = reader.random_memory() if random.random() <= self.reply else None
            self.say(context.bot, reader, replying=rid)

    def speak(self, update, context):
        chat = (update.message.chat)
        reader = self.load_reader(chat)

        if not self.bypass and reader.is_restricted():
            user = update.message.chat.get_member(update.message.from_user.id)
            if not self.user_is_admin(user):
                # update.message.reply_text("You do not have permissions to do that.")
                return

        mid = str(update.message.message_id)
        replied = update.message.reply_to_message
        rid = replied.message_id if replied else mid
        words = update.message.text.split()
        if len(words) > 1:
            reader.read(' '.join(words[1:]))
        self.say(context.bot, reader, replying=rid)

    def user_is_admin(self, member):
        self.logger.info("user {} ({}) requesting a restricted action".format(str(member.user.id), member.user.name))
        # eprint('!')
        # self.logger.info("Bot Creator ID is {}".format(str(self.admin)))
        return ((member.status == 'creator')
                or (member.status == 'administrator')
                or (member.user.id == self.admin))

    def speech(self, reader):
        return reader.generate_message(self.max_len)

    def say(self, bot, reader, replying=None, **kwargs):
        cid = reader.cid()
        if cid not in self.filter_cids:
            return
        if self.is_mute():
            return

        try:
            send(bot, cid, self.speech(reader), replying, logger=self.logger, **kwargs)
            if self.bypass:
                max_period = self.max_period
                reader.set_period(random.randint(max_period // 4, max_period))
            if random.random() <= self.repeat:
                send(bot, cid, self.speech(reader), logger=self.logger, **kwargs)
        except NetworkError as e:
            if '429' in e.message:
                self.logger.error("Error: TooManyRequests. Going mute for {} seconds.".format(self.mute_time))
                self.mute_timer = int(time.perf_counter())
            else:
                self.logger.error("Sending a message caused network error:")
                self.logger.exception(e)
        except Exception as e:
            self.logger.error("Sending a message caused exception:")
            self.logger.exception(e)

    def get_count(self, update, context):
        cid = str(update.message.chat.id)
        reader = self.access_reader(cid)

        num = str(reader.count()) if reader else "no"
        update.message.reply_text("I remember {} messages.".format(num))

    def get_chats(self, update, context):
        lines = ["[{}]: {}".format(reader.cid(), reader.title()) for reader in self.readers_pass()]
        chat_list = "\n".join(lines)
        update.message.reply_text("I have the following chats:\n\n" + chat_list)

    def period(self, update, context):
        chat = update.message.chat
        reader = self.access_reader(str(chat.id))

        words = update.message.text.split()
        if len(words) <= 1:
            update.message.reply_text("The current speech period is {}".format(reader.period()))
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
            self.store_file(*reader.archive())
        except Exception:
            update.message.reply_text("Format was confusing; period unchanged from {}.".format(reader.period()))

    def answer(self, update, context):
        chat = update.message.chat
        reader = self.access_reader(str(chat.id))

        words = update.message.text.split()
        if len(words) <= 1:
            update.message.reply_text("The current answer probability is {}".format(reader.answer()))
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
            self.store_file(*reader.archive())
        except Exception:
            update.message.reply_text("Format was confusing; answer probability unchanged from {}.".format(reader.answer()))

    def restrict(self, update, context):
        if "group" not in update.message.chat.type:
            update.message.reply_text("That only works in groups.")
            return
        chat = update.message.chat
        user = chat.get_member(update.message.from_user.id)
        reader = self.access_reader(str(chat.id))

        if reader.is_restricted():
            if not self.user_is_admin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        reader.toggle_restrict()
        allowed = "let only admins" if reader.is_restricted() else "let everyone"
        update.message.reply_text("I will {} configure me now.".format(allowed))
        self.store_file(*reader.archive())

    def silence(self, update, context):
        if "group" not in update.message.chat.type:
            update.message.reply_text("That only works in groups.")
            return
        chat = update.message.chat
        user = chat.get_member(update.message.from_user.id)
        reader = self.access_reader(str(chat.id))

        if reader.is_restricted():
            if not self.user_is_admin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        reader.toggle_silence()
        allowed = "avoid mentioning" if reader.is_silenced() else "mention"
        update.message.reply_text("I will {} people now.".format(allowed))
        self.store_file(*reader.archive())

    def who(self, update, context):
        msg = update.message
        usr = msg.from_user
        cht = msg.chat
        chtname = cht.title if cht.title else cht.first_name
        rdr = self.access_reader(str(cht.id))

        answer = ("You're **{name}**, with username `{username}`, and "
                  "id `{uid}`.\nYou're messaging in the chat named __{cname}__,"
                  " of type {ctype}, with id `{cid}`, and timestamp `{tstamp}`."
                  ).format(name=usr.full_name, username=usr.username,
                           uid=usr.id, cname=chtname, cid=cht.id,
                           ctype=rdr.ctype(), tstamp=str(msg.date))

        msg.reply_markdown(answer)

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

        answer = ("You're messaging in the chat of saved title __{cname}__,"
                  " with id `{cid}`, message count {c}, period {p}, and answer "
                  "probability {a}.\n\nThis chat is {perm}."
                  ).format(cname=reader.title(), cid=reader.cid(),
                           c=reader.count(), p=reader.period(),
                           a=reader.answer(), perm=permissions)

        msg.reply_markdown(answer)
