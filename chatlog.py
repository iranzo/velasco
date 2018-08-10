#!/usr/bin/env python3

import random
from markov import *

def parse_line(l):
    s = l.split('=')
    if len(s) < 2:
        return ""
    else:
        return s[1]

class Chatlog(object):
    def __init__(self, ident, chattype, title, text=None, freq=None, answer=0.5):
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
        self.replyables = []
        self.answer = answer
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

    def set_answer_freq(self, freq):
        if freq > 1:
            self.answer = 1
        elif freq < 0:
            self.answer = 0
        else:
            self.answer = freq
        return self.answer

    def add_msg(self, message):
        self.gen.add_text(message + ' ' + TAIL)
        self.count += 1

    def add_sticker(self, file_id):
        self.gen.add_text(STICKER_TAG + ' ' + file_id + ' ' + TAIL)
        self.count += 1

    def speak(self):
        return self.gen.generate_markov_text()

    def get_count(self):
        return self.count

    def answering(self, rand):
        if self.answer == 1:
            return True
        elif self.answer == 0:
            return False
        return rand <= self.answer

    def add_replyable(self, msg_id):
        self.replyables.append(msg_id)

    def restart_replyables(self, msg_id):
        if msg_id is not None:
            self.replyables = [msg_id]
        else:
            self.replyables = []

    def get_replyable(self):
        random.choice(self.replyables)

    def to_txt(self):
        lines = ["DICT=v2"]
        lines.append("CHAT_ID=" + self.id)
        lines.append("CHAT_TYPE=" + self.type)
        lines.append("CHAT_NAME=" + self.title)
        lines.append("MESSAGE_FREQ=" + str(self.freq))
        lines.append("ANSWER_FREQ=" + str(self.answer))
        lines.append("WORD_COUNT=" + str(self.count))
        lines.append("WORD_DICT=")
        txt = '\n'.join(lines)
        return txt + '\n' + self.gen.to_json()

    def from_txt(text):
        lines = text.splitlines()
        #print("Line 4=" + lines[4])
        print("Line 0=" + parse_line(lines[0]))
        if(parse_line(lines[0]) == "v2"):
            new_log = Chatlog(parse_line(lines[1]), parse_line(lines[2]), parse_line(lines[3]), None, int(parse_line(lines[4])), float(parse_line(lines[5])))
            new_log.count = int(parse_line(lines[6]))
            cache = '\n'.join(lines[8:])
            new_log.gen = Markov.from_json(cache)
            if new_log.count < 0:
                new_log.count = new_log.gen.new_count()
            return new_log
        elif(lines[4] == "dict:"):
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
