#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random

from telegram.error import *

from markov import Markov
from scribe import Scribe


def send(bot, cid, text, replying=None, format=None, logger=None, **kwargs):
    kwargs["parse_mode"] = format
    kwargs["reply_to_message_id"] = replying

    if text.startswith(Scribe.TagPrefix):
        words = text.split(maxsplit=1)
        if logger:
            logger.info('Sending {} "{}" to {}'.format(words[0][4:-1], words[1], cid))

        if words[0] == Scribe.StickerTag:
            return bot.send_sticker(cid, words[1], **kwargs)
        elif words[0] == Scribe.AnimTag:
            return bot.send_animation(cid, words[1], **kwargs)
        elif words[0] == Scribe.VideoTag:
            return bot.send_video(cid, words[1], **kwargs)
    else:
        text
        if logger:
            mtype = "reply" if replying else "message"
            logger.info("Sending a {} to {}: '{}'".format(mtype, cid, text))
        return bot.send_message(cid, text, **kwargs)


def getTitle(chat):
    if chat.title:
        return chat.title
    else:
        last = chat.last_name if chat.last_name else ""
        first = chat.first_name if chat.first_name else ""
        name = " ".join([first, last]).strip()
        if len(name) == 0:
            return "Unknown"
        else:
            return name


class Speaker(object):
    ModeFixed = "FIXED_MODE"
    ModeChance = "MODE_CHANCE"

    def __init__(
        self,
        name,
        username,
        archivist,
        logger,
        reply=0.1,
        repeat=0.05,
        wakeup=False,
        mode=ModeFixed,
    ):
        self.name = name
        self.username = username
        self.archivist = archivist
        self.scriptorium = archivist.wakeScriptorium()
        logger.info("----")
        logger.info("Finished loading.")
        logger.info("Loaded {} chats.".format(len(self.scriptorium)))
        logger.info("----")
        self.wakeup = wakeup
        self.logger = logger
        self.reply = reply
        self.repeat = repeat
        self.filterCids = archivist.filterCids
        self.bypass = archivist.bypass

    def announce(self, announcement, check=(lambda _: True)):
        for scribe in self.scriptorium:
            try:
                if check(scribe):
                    send(bot, scribe.cid(), announcement)
                    logger.info("Waking up on chat {}".format(scribe.cid()))
            except:
                pass

    def wake(self, bot, wake):
        if self.wakeup:

            def check(scribe):
                return scribe.checkType("group")

            self.announce(wake, check)

    def getScribe(self, chat):
        cid = str(chat.id)
        if cid not in self.scriptorium:
            scribe = Scribe.FromChat(chat, self.archivist, newchat=True)
            self.scriptorium[cid] = scribe
            return scribe
        else:
            return self.scriptorium[cid]

    def shouldReply(self, message, scribe):
        if not self.bypass and scribe.isRestricted():
            user = message.chat.get_member(message.from_user.id)
            if not self.userIsAdmin(user):
                # update.message.reply_text("You do not have permissions to do that.")
                return False
        replied = message.reply_to_message
        text = message.text.casefold() if message.text else ""
        return (
            ((replied is not None) and (replied.from_user.name == self.username))
            or (self.username in text)
            or (self.name in text and "@{}".format(self.name) not in text)
        )

    def store(self, scribe):
        if self.parrot is None:
            raise ValueError("Tried to store a Parrot that is None.")
        else:
            scribe.store(self.parrot.dumps())

    def loadParrot(self, scribe):
        newParrot = False
        self.parrot = self.archivist.wakeParrot(scribe.cid())
        if self.parrot is None:
            newParrot = True
            self.parrot = Markov()
        scribe.teachParrot(self.parrot)
        self.store(scribe)
        return newParrot

    def read(self, bot, update):
        chat = update.message.chat
        scribe = self.getScribe(chat)
        scribe.learn(update.message)

        if self.shouldReply(update.message, scribe) and scribe.isAnswering():
            self.say(bot, scribe, replying=update.message.message_id)
            return

        title = getTitle(update.message.chat)
        if title != scribe.title():
            scribe.setTitle(title)

        scribe.countdown -= 1
        if scribe.countdown < 0:
            scribe.resetCountdown()
            rid = scribe.getReference() if random.random() <= self.reply else None
            self.say(bot, scribe, replying=rid)
        elif (scribe.freq() - scribe.countdown) % self.archivist.saveCount == 0:
            self.loadParrot(scribe)

    def speak(self, bot, update):
        chat = update.message.chat
        scribe = self.getScribe(chat)

        if not self.bypass and scribe.isRestricted():
            user = update.message.chat.get_member(update.message.from_user.id)
            if not self.userIsAdmin(user):
                # update.message.reply_text("You do not have permissions to do that.")
                return

        mid = str(update.message.message_id)
        replied = update.message.reply_to_message
        rid = replied.message_id if replied else mid
        words = update.message.text.split()
        if len(words) > 1:
            scribe.learn(" ".join(words[1:]))
        self.say(bot, scribe, replying=rid)

    def userIsAdmin(self, member):
        self.logger.info(
            "user {} ({}) requesting a restricted action".format(
                str(member.user.id), member.user.name
            )
        )
        # self.logger.info("Bot Creator ID is {}".format(str(self.archivist.admin)))
        return (
            (member.status == "creator")
            or (member.status == "administrator")
            or (member.user.id == self.archivist.admin)
        )

    def speech(self, scribe):
        return self.parrot.generate_markov_text(
            size=self.archivist.maxLen, silence=scribe.isSilenced()
        )

    def say(self, bot, scribe, replying=None, **kwargs):
        if self.filterCids is not None and not scribe.cid() in self.filterCids:
            return

        self.loadParrot(scribe)
        try:
            send(
                bot,
                scribe.cid(),
                self.speech(scribe),
                replying,
                logger=self.logger,
                **kwargs
            )
            if self.bypass:
                maxFreq = self.archivist.maxFreq
                scribe.setFreq(random.randint(maxFreq // 4, maxFreq))
            if random.random() <= self.repeat:
                send(
                    bot, scribe.cid(), self.speech(scribe), logger=self.logger, **kwargs
                )
        except TimedOut:
            scribe.setFreq(scribe.freq() + self.archivist.freqIncrement)
            self.logger.warning(
                "Increased period for chat {} [{}]".format(scribe.title(), scribe.cid())
            )
        except Exception as e:
            self.logger.error("Sending a message caused error:")
            self.logger.error(e)

    def getCount(self, bot, update):
        cid = str(update.message.chat.id)
        scribe = self.scriptorium[cid]
        num = str(scribe.count()) if self.scriptorium[cid] else "no"
        update.message.reply_text("I remember {} messages.".format(num))

    def getChats(self, bot, update):
        lines = [
            "[{}]: {}".format(cid, self.scriptorium[cid].title())
            for cid in self.scriptorium
        ]
        list = "\n".join(lines)
        update.message.reply_text("\n\n".join(["I have the following chats:", list]))

    def freq(self, bot, update):
        chat = update.message.chat
        scribe = self.getScribe(chat)

        words = update.message.text.split()
        if len(words) <= 1:
            update.message.reply_text(
                "The current speech period is {}".format(scribe.freq())
            )
            return

        if scribe.isRestricted():
            user = update.message.chat.get_member(update.message.from_user.id)
            if not self.userIsAdmin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        try:
            freq = int(words[1])
            freq = scribe.setFreq(freq)
            update.message.reply_text("Period of speaking set to {}.".format(freq))
            scribe.store(None)
        except:
            update.message.reply_text(
                "Format was confusing; period unchanged from {}.".format(scribe.freq())
            )

    def answer(self, bot, update):
        chat = update.message.chat
        scribe = self.getScribe(chat)

        words = update.message.text.split()
        if len(words) <= 1:
            update.message.reply_text(
                "The current answer probability is {}".format(scribe.answer())
            )
            return

        if scribe.isRestricted():
            user = update.message.chat.get_member(update.message.from_user.id)
            if not self.userIsAdmin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        try:
            answ = float(words[1])
            answ = scribe.setAnswer(answ)
            update.message.reply_text("Answer probability set to {}.".format(answ))
            scribe.store(None)
        except:
            update.message.reply_text(
                "Format was confusing; answer probability unchanged from {}.".format(
                    scribe.answer()
                )
            )

    def restrict(self, bot, update):
        if "group" not in update.message.chat.type:
            update.message.reply_text("That only works in groups.")
            return
        chat = update.message.chat
        user = chat.get_member(update.message.from_user.id)
        scribe = self.getScribe(chat)
        if scribe.isRestricted():
            if not self.userIsAdmin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        scribe.restrict()
        allowed = "let only admins" if scribe.isRestricted() else "let everyone"
        update.message.reply_text("I will {} configure me now.".format(allowed))

    def silence(self, bot, update):
        if "group" not in update.message.chat.type:
            update.message.reply_text("That only works in groups.")
            return
        chat = update.message.chat
        user = chat.get_member(update.message.from_user.id)
        scribe = self.getScribe(chat)
        if scribe.isRestricted():
            if not self.userIsAdmin(user):
                update.message.reply_text("You do not have permissions to do that.")
                return
        scribe.silence()
        allowed = "avoid mentioning" if scribe.isSilenced() else "mention"
        update.message.reply_text("I will {} people now.".format(allowed))

    def who(self, bot, update):
        msg = update.message
        usr = msg.from_user
        cht = msg.chat
        chtname = cht.title if cht.title else cht.first_name

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
            ctype=scribe.type(),
            tstamp=str(msg.date),
        )

        msg.reply_markdown(answer)

    def where(self, bot, update):
        print("THEY'RE ASKING WHERE")
        msg = update.message
        chat = msg.chat
        scribe = self.getScribe(chat)
        if scribe.isRestricted() and scribe.isSilenced():
            permissions = "restricted and silenced"
        elif scribe.isRestricted():
            permissions = "restricted but not silenced"
        elif scribe.isSilenced():
            permissions = "not restricted but silenced"
        else:
            permissions = "neither restricted nor silenced"

        answer = (
            "You're messaging in the chat of saved title __{cname}__,"
            " with id `{cid}`, message count {c}, period {p}, and answer "
            "probability {a}.\n\nThis chat is {perm}."
        ).format(
            cname=scribe.title(),
            cid=scribe.cid(),
            c=scribe.count(),
            p=scribe.freq(),
            a=scribe.answer(),
            perm=permissions,
        )

        msg.reply_markdown(answer)
