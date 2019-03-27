#!/usr/bin/env python3

import random
from chatlog import *
from markov import Markov

def getTitle(chat):
    if chat.title is not None:
        return chat.title
    elif chat.first_name is not None:
        if chat.last_name is not None:
            return chat.first_name + " " + chat.last_name
        else:
            return chat.first_name
    else:
        return ""

def rewrite(text):
    words = text.replace('\n', '\n ').split(' ')
    i = 0
    while i < len(words):
        w = words[i].strip(' \t')
        if len(w) > 0:
            words[i] = w
        else:
            del words[i]
            i -= 1
        i += 1
    return words

class Page(object):
    def __init__(self, mid, content):
        self.id = mid
        self.content = content

class Scribe(object):
    TagPrefix = "^IS_"
    StickerTag = "^IS_STICKER^"
    AnimTag = "^IS_ANIMATION^"
    VideoTag = "^IS_VIDEO^"

    def __init__(self, chatlog, archivist):
        self.chat = chatlog
        self.archivist = archivist
        self.pages = []
        self.countdown = self.chat.freq
        self.logger = self.archivist.logger

    def FromChat(chat, archivist):
        chatlog = Chatlog(chat.id, chat.type, getTitle(chat))
        return Scribe(chatlog, archivist)

    def FromData(data, archivist):
        return None

    def FromFile(log, archivist):
        chatlog = Chatlog.loads(log)
        return Scribe(chatlog, archivist)

    def Recall(text, archivist):
        lines = text.splitlines()
        version = parse(lines[0]).strip()
        version = version if len(version.strip()) > 1 else lines[4]
        archivist.logger.info( "Dictionary version: {} ({} lines)".format(version, len(lines)) )
        if version == "v4":
            chatlog = Chatlog.loadl(lines[0:9])
            cache = '\n'.join(lines[10:])
            parrot = Markov.loads(cache)
        elif version == "v3":
            chatlog = Chatlog.loadl(lines[0:8])
            cache = '\n'.join(lines[9:])
            parrot = Markov.loads(cache)
        elif version == "v2":
            chatlog = Chatlog.loadl(lines[0:7])
            cache = '\n'.join(lines[8:])
            parrot = Markov.loads(cache)
        elif version == "dict:":
            chatlog = Chatlog.loadl(lines[0:6])
            cache = '\n'.join(lines[6:])
            parrot = Markov.loads(cache)
        else:
            chatlog = Chatlog.loadl(lines[0:4])
            cache = lines[4:]
            parrot = Markov(load=cache, mode=Markov.ModeList)
            #raise SyntaxError("Scribe: Chatlog format unrecognized.")
        s = Scribe(chatlog, archivist)
        s.parrot = parrot
        return s

    def store(self, parrot):
        self.archivist.store(self.chat.id, self.chat.dumps(), parrot)

    def checkType(self, t):
        return t in self.chat.type

    def compareType(self, t):
        return t == self.chat.type

    def setTitle(self, title):
        self.chat.title = title

    def setFreq(self, freq):
        if freq < self.countdown:
            self.countdown = max(freq, 1)
        return self.chat.set_freq(min(freq, self.archivist.maxFreq))

    def setAnswer(self, afreq):
        return self.chat.set_answer(afreq)

    def cid(self):
        return str(self.chat.id)

    def count(self):
        return self.chat.count

    def freq(self):
        return self.chat.freq

    def title(self):
        return self.chat.title

    def answer(self):
        return self.chat.answer

    def type(self):
        return self.chat.type

    def isRestricted(self):
        return self.chat.restricted

    def restrict(self):
        self.chat.restricted = (not self.chat.restricted)

    def isSilenced(self):
        return self.chat.silenced

    def silence(self):
        self.chat.silenced = (not self.chat.silenced)

    def isAnswering(self):
        rand = random.random()
        chance = self.answer()
        if chance == 1:
            return True
        elif chance == 0:
            return False
        return rand <= chance

    def addPage(self, mid, content):
        page = Page(mid, content)
        self.pages.append(page)

    def getReference(self):
        page = random.choice(self.pages)
        return page.id

    def resetCountdown(self):
        self.countdown = self.chat.freq

    def learn(self, message):
        mid = str(message.message_id)

        if message.text is not None:
            self.read(mid, message.text)
        elif message.sticker is not None:
            self.learnDrawing(mid, Scribe.StickerTag, message.sticker.file_id)
        elif message.animation is not None:
            self.learnDrawing(mid, Scribe.AnimTag, message.animation.file_id)
        elif message.video is not None:
            self.learnDrawing(mid, Scribe.VideoTag, message.video.file_id)
        self.chat.count += 1

    def learnDrawing(self, mid, tag, drawing):
        self.read(mid, tag + " " + drawing)

    def read(self, mid, text):
        if "velasco" in text.casefold() and len(text.split()) <= 3:
            return
        words = [Markov.Head]
        text = text + " " + Markov.Tail
        words.extend(rewrite(text))
        self.addPage(mid, words)

    def teachParrot(self, parrot):
        for page in self.pages:
            parrot.learn_words(page.content)
        self.pages = []

"""
    def learnFrom(self, scribe):
        self.chat.count += scribe.chat.count
        self.parrot.cross(scribe.parrot)
"""
