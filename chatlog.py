#!/usr/bin/env python3

from markov import *

class Chatlog(object):
    def __init__(self, ident, chattype, title, msgs=None, freq=None):
        if msgs is not None:
            self.msgs = msgs
        else:
            self.msgs = []
        self.id = str(ident)
        self.type = chattype
        self.title = title
        if freq is None:
            if "group" in chattype:
                freq = 20
            #elif chattype is "private":
            else:
                freq = 5
        self.freq = freq

    def add_msg(self, message):
        msg = message.split()
        msg.append("!kvl")
        self.msgs.append(msg)

    def get_markov_gen(self):
        msgs = []
        for m in self.msgs:
            msgs.append(' '.join(m))
        text = ' '.join(msgs)
        self.gen = Markov(text)

    def speak(self):
        self.get_markov_gen()
        return self.gen.generate_markov_text()

    def get_count(self):
        return len(self.msgs)

    def set_freq(self, freq):
        self.freq = freq

    def to_txt(self):
        lines = [self.id]
        lines.append(self.type)
        lines.append(self.title)
        lines.append(str(self.freq))
        for m in self.msgs:
            lines.append(' '.join(m))
        return '\n'.join(lines)

    def from_txt(text):
        lines = text.splitlines()
        msgs = []
        for m in lines[4:]:
            msgs.append(m.split())
        return Chatlog(lines[0], lines[1], lines[2], msgs, int(lines[3]))
