#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def parse(l):
    s = l.split("=", 1)
    if len(s) < 2:
        return ""
    else:
        return s[1]


class Chatlog(object):
    def __init__(
        self,
        cid,
        ctype,
        title,
        count=0,
        freq=None,
        answer=0.5,
        restricted=False,
        silenced=False,
    ):
        self.id = str(cid)
        self.type = ctype
        self.title = title
        if freq is None:
            if "group" in ctype:
                freq = 10
            # elif ctype is "private":
            else:
                freq = 2
        self.count = count
        self.freq = freq
        self.answer = answer
        self.restricted = restricted
        self.silenced = silenced

    def add_msg(self, message):
        self.gen.add_text(message)
        self.count += 1

    def set_freq(self, freq):
        if freq < 1:
            raise ValueError("Tried to set freq a value less than 1.")
        else:
            self.freq = freq
        return self.freq

    def set_answer(self, afreq):
        if afreq > 1:
            raise ValueError("Tried to set answer probability higher than 1.")
        elif afreq < 0:
            raise ValueError("Tried to set answer probability lower than 0.")
        else:
            self.answer = afreq
        return self.answer

    def dumps(self):
        lines = ["LOG=v4"]
        lines.append("CHAT_ID=" + self.id)
        lines.append("CHAT_TYPE=" + self.type)
        lines.append("CHAT_NAME=" + self.title)
        lines.append("WORD_COUNT=" + str(self.count))
        lines.append("MESSAGE_FREQ=" + str(self.freq))
        lines.append("ANSWER_FREQ=" + str(self.answer))
        lines.append("RESTRICTED=" + str(self.restricted))
        lines.append("SILENCED=" + str(self.silenced))
        # lines.append("WORD_DICT=")
        return "\n".join(lines)

    def loads(text):
        lines = text.splitlines()
        return Chatlog.loadl(lines)

    def loadl(lines):
        version = parse(lines[0]).strip()
        version = (
            version
            if len(version.strip()) > 1
            else (lines[4] if len(lines) > 4 else "LOG_ZERO")
        )
        if version == "v4":
            return Chatlog(
                cid=parse(lines[1]),
                ctype=parse(lines[2]),
                title=parse(lines[3]),
                count=int(parse(lines[4])),
                freq=int(parse(lines[5])),
                answer=float(parse(lines[6])),
                restricted=(parse(lines[7]) == "True"),
                silenced=(parse(lines[8]) == "True"),
            )
        elif version == "v3":
            return Chatlog(
                cid=parse(lines[1]),
                ctype=parse(lines[2]),
                title=parse(lines[3]),
                count=int(parse(lines[7])),
                freq=int(parse(lines[4])),
                answer=float(parse(lines[5])),
                restricted=(parse(lines[6]) == "True"),
            )
        elif version == "v2":
            return Chatlog(
                cid=parse(lines[1]),
                ctype=parse(lines[2]),
                title=parse(lines[3]),
                count=int(parse(lines[6])),
                freq=int(parse(lines[4])),
                answer=float(parse(lines[5])),
            )
        elif version == "dict:":
            return Chatlog(
                cid=lines[0],
                ctype=lines[1],
                title=lines[2],
                count=int(lines[5]),
                freq=int(lines[3]),
            )
        else:
            return Chatlog(
                cid=lines[0], ctype=lines[1], title=lines[2], freq=int(lines[3])
            )
