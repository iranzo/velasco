#!/usr/bin/env python3

import random
import time
from reader import Reader, get_chat_title
from telegram.error import TimedOut, NetworkError


def send(bot, cid, text, replying=None, formatting=None, logger=None, **kwargs):
    kwargs["parse_mode"] = formatting
    kwargs["reply_to_message_id"] = replying

    if text.startswith(Reader.TAG_PREFIX):
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
        text
        if logger:
            mtype = "reply" if replying else "message"
            logger.info("Sending a {} to {}: '{}'".format(mtype, cid, text))
        return bot.send_message(cid, text, **kwargs)


class Speaker(object):
    ModeFixed = "FIXED_MODE"
    ModeChance = "MODE_CHANCE"

    def __init__(self, username, archivist, logger, nicknames=[], mute_time=60,
                 reply=0.1, repeat=0.05, wakeup=False, mode=ModeFixed
                 ):
        self.names = nicknames
        self.mute_time = mute_time
        self.username = username
        self.archivist = archivist
        logger.info("----")
        logger.info("Finished loading.")
        logger.info("Loaded {} chats.".format(archivist.chat_count()))
        logger.info("----")
        self.wakeup = wakeup
        self.logger = logger
        self.reply = reply
        self.repeat = repeat
        self.filter_cids = archivist.filter_cids
        self.bypass = archivist.bypass
        self.current_reader = None
        self.time_counter = None

    def announce(self, bot, announcement, check=(lambda _: True)):
        # Sends an announcement to all chats that pass the check
        for reader in self.archivist.readers_pass():
            try:
                if check(reader):
                    send(bot, reader.cid(), announcement)
                    self.logger.info("Sending announcement to chat {}".format(reader.cid()))
            except Exception:
                pass

    def wake(self, bot, wake):
        # If wakeup flag is set, sends a wake-up message as announcement to all chats that
        # are groups. Also, always sends a wakeup message to the 'bot admin'
        send(bot, self.archivist.admin, wake)

        if self.wakeup:
            def group_check(reader):
                return reader.check_type("group")
            self.announce(bot, wake, group_check)

    def load_reader(self, chat):
        cid = str(chat.id)
        if self.current_reader is not None and cid == self.current_reader.cid():
            return

        if self.current_reader is not None:
            self.current_reader.commit_memory()
            self.save()

        reader = self.archivist.get_reader(cid)
        if not reader:
            reader = Reader.FromChat(chat, self.archivist.max_period, self.logger)
        self.current_reader = reader

    def get_reader(self, cid):
        if self.current_reader is None or cid != self.current_reader.cid():
            return self.archivist.get_reader(cid)

        return self.current_reader

    def mentioned(self, text):
        if self.username in text:
            return True
        for name in self.names:
            if name in text and "@{}".format(name) not in text:
                return True
        return False

    def should_reply(self, message):
        current_time = int(time.perf_counter())
        if self.time_counter is not None and (current_time - self.time_counter) < self.mute_time:
            return False
        if not self.bypass and self.current_reader.is_restricted():
            user = message.chat.get_member(message.from_user.id)
            if not self.user_is_admin(user):
                # update.message.reply_text("You do not have permissions to do that.")
                return False
        replied = message.reply_to_message
        text = message.text.casefold() if message.text else ""
        return (((replied is not None) and (replied.from_user.name == self.username))
                or (self.mentioned(text)))

    def save(self):
        if self.current_reader is None:
            raise ValueError("Tried to store a None Reader.")
        else:
            self.archivist.store(*self.current_reader.archive())

    def read(self, update, context):
        if update.message is None:
            return
        chat = update.message.chat
        self.load_reader(chat)
        self.current_reader.read(update.message)

        if self.should_reply(update.message) and self.current_reader.is_answering():
            self.say(context.bot, replying=update.message.message_id)
            return

        title = get_chat_title(update.message.chat)
        if title != self.current_reader.title():
            self.current_reader.set_title(title)

        self.current_reader.countdown -= 1
        if self.current_reader.countdown < 0:
            self.current_reader.reset_countdown()
            rid = self.current_reader.random_memory() if random.random() <= self.reply else None
            self.say(context.bot, replying=rid)
        elif (self.current_reader.period() - self.current_reader.countdown) % self.archivist.save_count == 0:
            self.save()

    def speak(self, update, context):
        chat = (update.message.chat)
        self.load_reader(chat)

        if not self.bypass and self.current_reader.is_restricted():
            user = update.message.chat.get_member(update.message.from_user.id)
            if not self.user_is_admin(user):
                # update.message.reply_text("You do not have permissions to do that.")
                return

        mid = str(update.message.message_id)
        replied = update.message.reply_to_message
        rid = replied.message_id if replied else mid
        words = update.message.text.split()
        if len(words) > 1:
            self.current_reader.read(' '.join(words[1:]))
        self.say(context.bot, replying=rid)

    def user_is_admin(self, member):
        self.logger.info("user {} ({}) requesting a restricted action".format(str(member.user.id), member.user.name))
        # self.logger.info("Bot Creator ID is {}".format(str(self.archivist.admin)))
        return ((member.status == 'creator')
                or (member.status == 'administrator')
                or (member.user.id == self.archivist.admin))

    def speech(self):
        return self.current_reader.generate_message(self.archivist.max_len)

    def say(self, bot, replying=None, **kwargs):
        cid = self.current_reader.cid()
        if self.filter_cids is not None and cid not in self.filter_cids:
            return

        try:
            send(bot, cid, self.speech(), replying, logger=self.logger, **kwargs)
            if self.bypass:
                max_period = self.archivist.max_period
                self.current_reader.set_period(random.randint(max_period // 4, max_period))
            if random.random() <= self.repeat:
                send(bot, cid, self.speech(), logger=self.logger, **kwargs)
        except TimedOut as e:
            self.logger.error("Telegram timed out.")
            self.logger.exception(e)
        except NetworkError as e:
            if '429' in e.message:
                self.logger.error("Error: TooManyRequests. Going mute for {} seconds.".format(self.mute_time))
                self.time_counter = int(time.perf_counter())
            else:
                self.logger.error("Sending a message caused network error:")
                self.logger.exception(e)
        except Exception as e:
            self.logger.error("Sending a message caused exception:")
            self.logger.exception(e)

    def get_count(self, update, context):
        cid = str(update.message.chat.id)
        reader = self.get_reader(cid)

        num = str(reader.count()) if reader else "no"
        update.message.reply_text("I remember {} messages.".format(num))

    def get_chats(self, update, context):
        lines = ["[{}]: {}".format(reader.cid(), reader.title()) for reader in self.archivist.readers_pass]
        chat_list = "\n".join(lines)
        update.message.reply_text("I have the following chats:\n\n" + chat_list)

    def period(self, update, context):
        chat = update.message.chat
        reader = self.get_reader(str(chat.id))

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
            self.archivist.store(*reader.archive())
        except Exception:
            update.message.reply_text("Format was confusing; period unchanged from {}.".format(reader.period()))

    def answer(self, update, context):
        chat = update.message.chat
        reader = self.get_reader(str(chat.id))

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
            self.archivist.store(*reader.archive())
        except Exception:
            update.message.reply_text("Format was confusing; answer probability unchanged from {}.".format(reader.answer()))

    def restrict(self, update, context):
        if "group" not in update.message.chat.type:
            update.message.reply_text("That only works in groups.")
            return
        chat = update.message.chat
        user = chat.get_member(update.message.from_user.id)
        reader = self.get_reader(str(chat.id))

        if reader.is_restricted():
            if not self.user_is_admin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        reader.toggle_restrict()
        allowed = "let only admins" if reader.is_restricted() else "let everyone"
        update.message.reply_text("I will {} configure me now.".format(allowed))
        self.archivist.store(*reader.archive())

    def silence(self, update, context):
        if "group" not in update.message.chat.type:
            update.message.reply_text("That only works in groups.")
            return
        chat = update.message.chat
        user = chat.get_member(update.message.from_user.id)
        reader = self.get_reader(str(chat.id))

        if reader.is_restricted():
            if not self.user_is_admin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        reader.toggle_silence()
        allowed = "avoid mentioning" if reader.is_silenced() else "mention"
        update.message.reply_text("I will {} people now.".format(allowed))
        self.archivist.store(*reader.archive())

    def who(self, update, context):
        msg = update.message
        usr = msg.from_user
        cht = msg.chat
        chtname = cht.title if cht.title else cht.first_name
        rdr = self.get_reader(str(cht.id))

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
        reader = self.get_reader(str(chat.id))
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
