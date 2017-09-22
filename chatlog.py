#!/usr/bin/env python3

from markov import *

class Chatlog(object):
    def __init__(self, ident, chattype, title, text=None, freq=None):
        self.id = str(ident)
        self.type = chattype
        self.title = title
        if freq is None:
            if "group" in chattype:
                freq = 10
            #elif chattype is "private":
            else:
                freq = 2
        self.freq = freq
        if text is not None:
            self.count = len(text)
        else:
            self.count = 0
        self.gen = Markov(text)

    def set_title(self, title):
        self.title = title

    def set_freq(self, freq):
        if not freq > 0:
            raise ValueError('Tried to set 0 or negative freq value.')
        elif freq > 100000:
            freq = 100000
        self.freq = freq
        return self.freq

    def add_msg(self, message):
        self.gen.add_text(message + " !kvl")
        self.count += 1

    def speak(self):
        return self.gen.generate_markov_text()

    def get_count(self):
        return self.count

    def to_txt(self):
        lines = [self.id]
        lines.append(self.type)
        lines.append(self.title)
        lines.append(str(self.freq))
        lines.append("dict:")
        lines.append(str(self.count))
        txt = '\n'.join(lines)
        return txt + '\n' + self.gen.to_json()

    def from_txt(text):
        lines = text.splitlines()
        if(lines[4] == "dict:"):
            new_log = Chatlog(lines[0], lines[1], lines[2], None, int(lines[3]))
            new_log.count = int(lines[5])
            cache = '\n'.join(lines[6:])
            new_log.gen = Markov.from_json(cache)
            if new_log.count < 0:
                new_log.count = new_log.gen.new_count()
            return new_log
        else:
            return Chatlog(lines[0], lines[1], lines[2], lines[4:], int(lines[3]))

    def fuse_with(chatlog):
        self.count += chatlog.count
        self.gen.fuse_with(chatlog.gen)
