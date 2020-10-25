#!/usr/bin/env python3

import random
import json


def rewrite(text):
    # This splits strings into lists of words delimited by space.
    # Other whitespaces are appended space characters so they are included
    # as their own Markov chain element, so as not to pollude with
    # "different" words that would only differ in having a whitespace
    # attached or not
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


def getkey(w1, w2):
    # This gives a dictionary key from 2 words, ignoring case
    key = (w1.strip().casefold(), w2.strip().casefold())
    return str(key)


def getwords(key):
    # This turns a dictionary key back into 2 separate words
    words = key.strip('()').split(', ')
    for i in range(len(words)):
        words[i].strip('\'')
    return words


def triplets(wordlist):
    # Generates triplets of words from the given data string. So if our string
    # were "What a lovely day", we'd generate (What, a, lovely) and then
    # (a, lovely, day).
    if len(wordlist) < 3:
        return

    for i in range(len(wordlist) - 2):
        yield (wordlist[i], wordlist[i+1], wordlist[i+2])


class Generator(object):
    MODE_JSON = "MODE_JSON"
    # This is to mark when we want to create a Generator object from a given JSON

    MODE_LIST = "MODE_LIST"
    # This is to mark when we want to create a Generator object from a given list of words

    MODE_CHAT_DATA = "MODE_CHAT_DATA"
    # This is to mark when we want to create a Generator object from Chat data (WIP)

    HEAD = "\n^MESSAGE_SEPARATOR^"
    TAIL = " ^MESSAGE_SEPARATOR^"

    def __init__(self, load=None, mode=None):
        if mode is not None:
            # We ain't creating a new Generator from scratch
            if mode == Generator.MODE_JSON:
                self.cache = json.loads(load)
            elif mode == Generator.MODE_LIST:
                self.cache = {}
                self.load_list(load)
        else:
            self.cache = {}
            # The cache is where we store our words

    def load_list(self, many):
        # Takes a list of strings and adds them to the cache one by one
        for one in many:
            self.add(one)

    def dumps(self):
        # Dumps the cache dictionary into a JSON-formatted string
        return json.dumps(self.cache)

    def loads(dump):
        # Loads the cache dictionary from a JSON-formatted string
        if len(dump) == 0:
            # faulty dump gives default Generator
            return Generator()
        # otherwise
        return Generator(load=dump, mode=Generator.MODE_JSON)

    def add(self, text):
        # This takes a string and stores it in the cache, preceding it
        # with the HEAD that marks the beginning of a new message and
        # following it with the TAIL that marks the end
        words = [Generator.HEAD]
        text = rewrite(text + Generator.TAIL)
        words.extend(text)
        self.database(words)

    def database(self, words):
        # This takes a list of words and stores it in the cache, adding
        # a special entry for the first word (the HEAD marker)
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

    def generate(self, size=50, silence=False):
        # This generates the Markov text/word chain
        # silence tells if mentions should be silenced
        if len(self.cache) == 0:
            # If there is nothing in the cache we cannot generate anything
            return ""

        w1 = random.choice(self.cache[Generator.HEAD])
        w2 = random.choice(self.cache[getkey(Generator.HEAD, w1)])
        # Start with a message HEAD and a random message starting word
        gen_words = []
        for i in range(size):
            # As long as we don't go over the size value (max. message length)...
            if silence and w1.startswith("@") and len(w1) > 1:
                gen_words.append(w1.replace("@", "(@)"))
                # ...append the first word, silencing any possible username mention
            else:
                gen_words.append(w1)
                # ..append the first word
            if w2 == Generator.TAIL or not getkey(w1, w2) in self.cache:
                # When there's no key from the last 2 words to follow the chain,
                # or we reached a separation between messages, stop
                break
            else:
                w1, w2 = w2, random.choice(self.cache[getkey(w1, w2)])
                # Make the second word to be the new first word, and
                # make a new random word that follows the chain to be
                # the new second word
        return ' '.join(gen_words)

    def cross(self, gen):
        # cross 2 Generators into this one
        for key in gen.cache:
            if key in self.cache:
                self.cache[key].extend(gen.cache[key])
            else:
                self.cache[key] = list(gen.cache[key])

    def new_count(self):
        # Count again the number of messages if the current number is unreliable
        count = 0
        for key in self.cache:
            for word in self.cache[key]:
                if word == Generator.TAIL:
                    count += 1
                    # by just counting message separators
        return count
