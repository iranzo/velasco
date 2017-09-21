#!/usr/bin/env python3

import random
import json

HEAD = "\n!kvl"
TAIL = "!kvl"

def trim_and_split(text):
    words = text.split(' ')
    for i in range(len(words)):
        words[i] = words[i].strip(' \t')
    return words

def getkey(w1, w2):
    key = (w1.strip().casefold(), w2.strip().casefold())
    return str(key)

def triples(wordlist):
    """ Generates triples from the given data string. So if our string were
            "What a lovely day", we'd generate (What, a, lovely) and then
            (a, lovely, day).
    """

    if len(wordlist) < 3:
        return

    for i in range(len(wordlist) - 2):
        yield (wordlist[i], wordlist[i+1], wordlist[i+2])

class Markov(object):
    def __init__(self, text=None, from_json=False):
        self.cache = {}
        if not from_json:
            if text is not None:
                for line in text:
                    self.add_text(line)
        else:
            self.cache = json.loads(text)

    def to_json(self):
        return json.dumps(self.cache)

    def from_json(string):
        return Markov(string, True)

    def add_text(self, text):
        words = trim_and_split(HEAD + " " + text)
        self.database(words)

    def database(self, wordlist):
        for w1, w2, w3 in triples(wordlist):
            if w1 == HEAD:
                if w1 in self.cache:
                    self.cache[HEAD].append(w2)
                else:
                    self.cache[HEAD] = [w2]
            key = getkey(w1, w2)
            if key in self.cache:
                self.cache[key].append(w3)
            else:
                self.cache[key] = [w3]

    def generate_markov_text(self, size=50):
        w1 = random.choice(self.cache[HEAD])
        w2 = random.choice(self.cache[getkey(HEAD, w1)])
        gen_words = []
        for i in range(size):
            gen_words.append(w1)
            if w2 == TAIL or not getkey(w1, w2) in self.cache:
                print("Generated text")
                break
            else:
                w1, w2 = w2, random.choice(self.cache[getkey(w1, w2)])
        return ' '.join(gen_words)

    def fuse_with(self, gen):
        d = gen.cache
        for key in gen.cache:
            if key in self.cache:
                self.cache[key].extend(d[key])
            else:
                self.cache[key] = list(d[key])
