#!/usr/bin/env python3

import random
from metadata import Metadata, parse_card_line
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


class Reader(object):
    # This is a chat Reader object, in charge of managing the parsing of messages
    # for a specific chat, and holding said chat's metadata

    TAG_PREFIX = "^IS_"
    STICKER_TAG = "^IS_STICKER^"
    ANIM_TAG = "^IS_ANIMATION^"
    VIDEO_TAG = "^IS_VIDEO^"

    def __init__(self, metadata, vocab, max_period, logger):
        self.meta = metadata
        self.vocab = vocab
        self.max_period = max_period
        self.short_term_mem = []
        self.countdown = self.meta.period
        self.logger = logger

    def FromChat(chat, max_period, logger):
        # Create a new Reader from a Chat object
        meta = Metadata(chat.id, chat.type, get_chat_title(chat))
        vocab = Generator()
        return Reader(meta, vocab, max_period, logger)

    def FromHistory(history, vocab, max_period, logger):
        # Create a new Reader from a whole Chat history (WIP)
        return None

    def FromCard(meta, vocab, max_period, logger):
        # Create a new Reader from a meta's file dump
        metadata = Metadata.loads(meta)
        return Reader(metadata, vocab, max_period, logger)

    def FromFile(text, max_period, logger, vocab=None):
        # Load a Reader from a file's text string (obsolete)
        lines = text.splitlines()
        version = parse_card_line(lines[0]).strip()
        version = version if len(version.strip()) > 1 else lines[4]
        logger.info("Dictionary version: {} ({} lines)".format(version, len(lines)))
        if version == "v4" or version == "v5":
            return Reader.FromCard(text, vocab, max_period, logger)
            # I stopped saving the chat metadata and the cache together
        elif version == "v3":
            meta = Metadata.loadl(lines[0:8])
            cache = '\n'.join(lines[9:])
            vocab = Generator.loads(cache)
        elif version == "v2":
            meta = Metadata.loadl(lines[0:7])
            cache = '\n'.join(lines[8:])
            vocab = Generator.loads(cache)
        elif version == "dict:":
            meta = Metadata.loadl(lines[0:6])
            cache = '\n'.join(lines[6:])
            vocab = Generator.loads(cache)
        else:
            meta = Metadata.loadl(lines[0:4])
            cache = lines[4:]
            vocab = Generator(load=cache, mode=Generator.MODE_LIST)
            # raise SyntaxError("Reader: Metadata format unrecognized.")
        r = Reader(meta, vocab, max_period, logger)
        return r

    def archive(self):
        # Returns a nice lice little tuple package for the archivist to save to file.
        # Also commits to long term memory any pending short term memories
        self.commit_memory()
        return (self.meta.id, self.meta.dumps(), self.vocab.dump)

    def check_type(self, t):
        # Checks type. Returns "True" for "group" even if it's supergroup
        return t in self.meta.type

    def exactly_type(self, t):
        # Hard check
        return t == self.meta.type

    def set_title(self, title):
        self.meta.title = title

    def set_period(self, period):
        if period < self.countdown:
            self.countdown = max(period, 1)
        return self.meta.set_period(min(period, self.max_period))

    def set_answer(self, prob):
        return self.meta.set_answer(prob)

    def cid(self):
        return str(self.meta.id)

    def count(self):
        return self.meta.count

    def period(self):
        return self.meta.period

    def title(self):
        return self.meta.title

    def answer(self):
        return self.meta.answer

    def ctype(self):
        return self.meta.type

    def is_restricted(self):
        return self.meta.restricted

    def toggle_restrict(self):
        self.meta.restricted = (not self.meta.restricted)

    def is_silenced(self):
        return self.meta.silenced

    def toggle_silence(self):
        self.meta.silenced = (not self.meta.silenced)

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
        if len(self.short_term_mem) == 0:
            return None
        mem = random.choice(self.short_term_mem)
        return mem.id

    def reset_countdown(self):
        self.countdown = self.meta.period

    def read(self, message):
        mid = str(message.message_id)

        if message.text is not None:
            self.learn(mid, message.text)
        elif message.sticker is not None:
            self.learn_drawing(mid, Reader.STICKER_TAG, message.sticker.file_id)
        elif message.animation is not None:
            self.learn_drawing(mid, Reader.ANIM_TAG, message.animation.file_id)
        elif message.video is not None:
            self.learn_drawing(mid, Reader.VIDEO_TAG, message.video.file_id)
        self.meta.count += 1

    def learn_drawing(self, mid, tag, drawing):
        self.learn(mid, tag + " " + drawing)

    def learn(self, mid, text):
        if "velasco" in text.casefold() and len(text.split()) <= 3:
            return
        self.add_memory(mid, text)

    def commit_memory(self):
        for mem in self.short_term_mem:
            self.vocab.add(mem.content)
        self.short_term_mem = []

    def generate_message(self, max_len):
        return self.vocab.generate(size=max_len, silence=self.is_silenced())
