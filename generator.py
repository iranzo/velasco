#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import random


# This splits strings into lists of words delimited by space.
# Other whitespaces are appended space characters so they are included
# as their own Markov chain element, so as not to pollude with
# "different" words that would only differ in having a whitespace
# attached or not
def rewrite(text):
    words = text.replace("\n", "\n ").split(" ")
    i = 0
    while i < len(words):
        w = words[i].strip(" \t")
        if len(w) > 0:
            words[i] = w
        else:
            del words[i]
            i -= 1
        i += 1
    return words


# This gives a dictionary key from 2 words, ignoring case
def getkey(w1, w2):
    key = (w1.strip().casefold(), w2.strip().casefold())
    return str(key)


# This turns a dictionary key back into 2 separate words
def getwords(key):
    words = key.strip("()").split(", ")
    for i in range(len(words)):
        words[i].strip("'")
    return words


# Generates triplets of words from the given data string. So if our string
# were "What a lovely day", we'd generate (What, a, lovely) and then
# (a, lovely, day).
def triplets(wordlist):
    if len(wordlist) < 3:
        return

    for i in range(len(wordlist) - 2):
        yield (wordlist[i], wordlist[i + 1], wordlist[i + 2])


class Generator(object):
    # Marks when we want to create a Generator object from a given JSON
    MODE_JSON = "MODE_JSON"

    # Marks when we want to create a Generator object from a given list of words
    MODE_LIST = "MODE_LIST"

    # Marks when we want to create a Generator object from a given dictionary
    MODE_DICT = "MODE_DICT"

    # Marks when we want to create a Generator object from a whole Chat history (WIP)
    MODE_HIST = "MODE_HIST"

    # Marks the beginning of a message
    HEAD = "\n^MESSAGE_SEPARATOR^"
    # Marks the end of a message
    TAIL = " ^MESSAGE_SEPARATOR^"

    def __init__(self, load=None, mode=None):
        if mode is not None:
            if mode == Generator.MODE_JSON:
                self.cache = json.loads(load)
            elif mode == Generator.MODE_LIST:
                self.cache = {}
                self.load_list(load)
            elif mode == Generator.MODE_DICT:
                self.cache = load
            # TODO: Chat History mode
        else:
            self.cache = {}

    # Loads a text divided into a list of lines
    def load_list(self, many):
        for one in many:
            self.add(one)

    # Dumps the cache dictionary into a JSON-formatted string
    def dumps(self):
        return json.dumps(self.cache, ensure_ascii=False)

    # Dumps the cache dictionary into a file, formatted as JSON
    def dump(self, f):
        json.dump(self.cache, f, ensure_ascii=False)

    # Loads the cache dictionary from a JSON-formatted string
    def loads(dump):
        if len(dump) == 0:
            # faulty dump gives default Generator
            return Generator()
        # otherwise
        return Generator(load=dump, mode=Generator.MODE_JSON)

    # Loads the cache dictionary from a file, formatted as JSON
    def load(f):
        return Generator(load=json.load(f), mode=Generator.MODE_DICT)

    def add(self, text):
        words = [Generator.HEAD]
        text = rewrite(text + Generator.TAIL)
        words.extend(text)
        self.database(words)

    # This takes a list of words and stores it in the cache, adding
    # a special entry for the first word (the HEAD marker)
    def database(self, words):
        for w1, w2, w3 in triplets(words):
            if w1 == Generator.HEAD:
                if w1 in self.cache:
                    self.cache[Generator.HEAD].append(w2)
                else:
                    self.cache[Generator.HEAD] = [w2]
            key = getkey(w1, w2)
            if key in self.cache:
                # if the key exists, add the new word to the end of the chain
                self.cache[key].append(w3)
            else:
                # otherwise, create a new entry for the new key starting with
                # the new end of chain
                self.cache[key] = [w3]

    # This generates the Markov text/word chain
    # silence=True disables Telegram user mentions
    def generate(self, size=50, silence=False):
        if len(self.cache) == 0:
            # If there is nothing in the cache we cannot generate anything
            return ""

        # Start with a message HEAD and a random message starting word
        w1 = random.choice(self.cache[Generator.HEAD])
        w2 = random.choice(self.cache[getkey(Generator.HEAD, w1)])
        gen_words = []
        # As long as we don't go over the max. message length (in n. of words)...
        for i in range(size):
            if silence and w1.startswith("@") and len(w1) > 1:
                # ...append word 1, disabling any possible Telegram mention
                gen_words.append(w1.replace("@", "(@)"))
            else:
                # ..append word 1
                gen_words.append(w1)
            if w2 == Generator.TAIL or not getkey(w1, w2) in self.cache:
                # When there's no key from the last 2 words to follow the chain,
                # or we reached a separation between messages, stop
                break
            else:
                # Get a random third word that follows the chain of words 1
                # and 2, then make words 2 and 3 to be the new words 1 and 2
                w1, w2 = w2, random.choice(self.cache[getkey(w1, w2)])
        return " ".join(gen_words)

    # Cross a second Generator into this one
    def cross(self, gen):
        for key in gen.cache:
            if key in self.cache:
                self.cache[key].extend(gen.cache[key])
            else:
                self.cache[key] = list(gen.cache[key])

    # Count again the number of messages
    # (for whenever the count number is unreliable)
    def new_count(self):
        count = 0
        for key in self.cache:
            for word in self.cache[key]:
                if word == Generator.TAIL:
                    # ...by just counting message separators
                    count += 1
        return count
