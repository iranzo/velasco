#!/usr/bin/env python3

import random
import json

def getkey(w1, w2):
    key = (w1.strip().casefold(), w2.strip().casefold())
    return str(key)

def getwords(key):
    words = key.strip('()').split(', ')
    for i in range(len(words)):
        words[i].strip('\'')
    return words

def triples(wordlist):
    # Generates triples from the given data string. So if our string were
    # "What a lovely day", we'd generate (What, a, lovely) and then
    # (a, lovely, day).
    if len(wordlist) < 3:
        return

    for i in range(len(wordlist) - 2):
        yield (wordlist[i], wordlist[i+1], wordlist[i+2])

class Markov(object):
    ModeJson = "MODE_JSON"
    ModeList = "MODE_LIST"
    ModeChatData = "MODE_CHAT_DATA"

    Head = "\n^MESSAGE_SEPARATOR^"
    Tail = "^MESSAGE_SEPARATOR^"

    def __init__(self, load=None, mode=None):
        if mode is not None:
            if mode == Markov.ModeJson:
                self.cache = json.loads(load)
            elif mode == Markov.ModeList:
                self.cache = {}
                self.loadList(load)
        else:
            self.cache = {}

    def loadList(self, lines):
        for line in lines:
            words = [Markov.Head]
            words.extend(line.split())
            self.learn_words(words)

    def dumps(self):
        return json.dumps(self.cache)

    def loads(dump):
        if len(dump) == 0:
            return Markov()
        return Markov(load=dump, mode=Markov.ModeJson)

    def learn_words(self, words):
        self.database(words)

    def database(self, wordlist):
        for w1, w2, w3 in triples(wordlist):
            if w1 == Markov.Head:
                if w1 in self.cache:
                    self.cache[Markov.Head].append(w2)
                else:
                    self.cache[Markov.Head] = [w2]
            key = getkey(w1, w2)
            if key in self.cache:
                self.cache[key].append(w3)
            else:
                self.cache[key] = [w3]

    def generate_markov_text(self, size=50, silence=False):
        if len(self.cache) == 0:
            return ""
        w1 = random.choice(self.cache[Markov.Head])
        w2 = random.choice(self.cache[getkey(Markov.Head, w1)])
        gen_words = []
        for i in range(size):
            if silence and w1.startswith("@") and len(w1) > 1:
                gen_words.append(w1.replace("@", "(@)"))
            else:
                gen_words.append(w1)
            if w2 == Markov.Tail or not getkey(w1, w2) in self.cache:
                # print("Generated text")
                break
            else:
                w1, w2 = w2, random.choice(self.cache[getkey(w1, w2)])
        return ' '.join(gen_words)

    def cross(self, gen):
        for key in gen.cache:
            if key in self.cache:
                self.cache[key].extend(d[key])
            else:
                self.cache[key] = list(d[key])

    def new_count(self):
        count = 0
        for key in self.cache:
            for word in self.cache[key]:
                if word == Markov.Tail:
                    count += 1
        return count
