#!/usr/bin/env python3

import random
from chatcard import ChatCard, parse_card_line
from generator import Generator


def get_chat_title(chat):
    # This gives me the chat title, or the first and maybe last
    # name of the user as fallback if it's a private chat
    if chat.title is not None:
        return chat.title
    elif chat.first_name is not None:
        if chat.last_name is not None:
            return chat.first_name + " " + chat.last_name
        else:
            return chat.first_name
    else:
        return ""


class Memory(object):
    def __init__(self, mid, content):
        self.id = mid
        self.content = content


class ChatReader(object):
    TAG_PREFIX = "^IS_"
    STICKER_TAG = "^IS_STICKER^"
    ANIM_TAG = "^IS_ANIMATION^"
    VIDEO_TAG = "^IS_VIDEO^"

    def __init__(self, chatcard, max_period, logger):
        self.card = chatcard
        self.max_period = max_period
        self.short_term_mem = []
        self.countdown = self.card.period
        self.logger = logger

    def FromChat(chat, max_period, logger, newchat=False):
        # Create a new ChatReader from a Chat object
        card = ChatCard(chat.id, chat.type, get_chat_title(chat))
        return ChatReader(card, max_period, logger)

    def FromData(data, max_period, logger):
        # Create a new ChatReader from a whole Chat history (WIP)
        return None

    def FromCard(card, max_period, logger):
        # Create a new ChatReader from a card's file dump
        chatcard = ChatCard.loads(card)
        return ChatReader(chatcard, max_period, logger)

    def FromFile(text, max_period, logger):
        # Load a ChatReader from a file's text string
        lines = text.splitlines()
        version = parse_card_line(lines[0]).strip()
        version = version if len(version.strip()) > 1 else lines[4]
        logger.info("Dictionary version: {} ({} lines)".format(version, len(lines)))
        vocab = None
        if version == "v4" or version == "v5":
            return ChatReader.FromCard(text, max_period, logger)
            # I stopped saving the chat metadata and the cache together
        elif version == "v3":
            card = ChatCard.loadl(lines[0:8])
            cache = '\n'.join(lines[9:])
            vocab = Generator.loads(cache)
        elif version == "v2":
            card = ChatCard.loadl(lines[0:7])
            cache = '\n'.join(lines[8:])
            vocab = Generator.loads(cache)
        elif version == "dict:":
            card = ChatCard.loadl(lines[0:6])
            cache = '\n'.join(lines[6:])
            vocab = Generator.loads(cache)
        else:
            card = ChatCard.loadl(lines[0:4])
            cache = lines[4:]
            vocab = Generator(load=cache, mode=Generator.MODE_LIST)
            # raise SyntaxError("ChatReader: ChatCard format unrecognized.")
        s = ChatReader(card, max_period, logger)
        return (s, vocab)

    def archive(self, vocab):
        # Returns a nice lice little tuple package for the archivist to save to file.
        # Also commits to long term memory any pending short term memories
        self.commit_long_term(vocab)
        return (self.card.id, self.card.dumps(), vocab)

    def check_type(self, t):
        # Checks type. Returns "True" for "group" even if it's supergroup
        return t in self.card.type

    def exactly_type(self, t):
        # Hard check
        return t == self.card.type

    def set_title(self, title):
        self.card.title = title

    def set_period(self, period):
        if period < self.countdown:
            self.countdown = max(period, 1)
        return self.card.set_period(min(period, self.max_period))

    def set_answer(self, prob):
        return self.card.set_answer(prob)

    def cid(self):
        return str(self.card.id)

    def count(self):
        return self.card.count

    def period(self):
        return self.card.period

    def title(self):
        return self.card.title

    def answer(self):
        return self.card.answer

    def ctype(self):
        return self.card.type

    def is_restricted(self):
        return self.card.restricted

    def toggle_restrict(self):
        self.card.restricted = (not self.card.restricted)

    def is_silenced(self):
        return self.card.silenced

    def toggle_silence(self):
        self.card.silenced = (not self.card.silenced)

    def is_answering(self):
        rand = random.random()
        chance = self.answer()
        if chance == 1:
            return True
        elif chance == 0:
            return False
        return rand <= chance

    def add_memory(self, mid, content):
        mem = Memory(mid, content)
        self.short_term_mem.append(mem)

    def random_memory(self):
        mem = random.choice(self.short_term_mem)
        return mem.id

    def reset_countdown(self):
        self.countdown = self.card.period

    def read(self, message):
        mid = str(message.message_id)

        if message.text is not None:
            self.read(mid, message.text)
        elif message.sticker is not None:
            self.learn_drawing(mid, ChatReader.STICKER_TAG, message.sticker.file_id)
        elif message.animation is not None:
            self.learn_drawing(mid, ChatReader.ANIM_TAG, message.animation.file_id)
        elif message.video is not None:
            self.learn_drawing(mid, ChatReader.VIDEO_TAG, message.video.file_id)
        self.card.count += 1

    def learn_drawing(self, mid, tag, drawing):
        self.learn(mid, tag + " " + drawing)

    def learn(self, mid, text):
        if "velasco" in text.casefold() and len(text.split()) <= 3:
            return
        self.add_memory(mid, text)

    def commit_long_term(self, vocab):
        for mem in self.short_term_mem:
            vocab.add(mem.content)
        self.short_term_mem = []

    """
    def learnFrom(self, scribe):
        self.card.count += scribe.chat.count
        self.vocab.cross(scribe.vocab)
    """
