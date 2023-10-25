#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# This reads a line in the format 'VARIABLE=value' and gives me the value.
# See Metadata.loadl(...) for more details
def parse_card_line(line):
    s = line.split("=", 1)
    if len(s) < 2:
        return ""
    else:
        return s[1]


# This is a chat's Metadata, holding different configuration values for
# Velasco and other miscellaneous information about the chat
class Metadata(object):
    def __init__(
        self,
        cid,
        ctype,
        title,
        count=0,
        period=None,
        answer=0.5,
        restricted=False,
        silenced=False,
    ):
        # The Telegram chat's ID
        self.id = str(cid)
        # The type of chat
        self.type = ctype
        # The title of the chat
        self.title = title
        if period is None:
            if "group" in ctype:
                # Default period for groups and supergroups
                period = 10
            else:
                # Default period for private or channel chats
                period = 2
        # The number of messages read in a chat
        self.count = count
        # This chat's configured period
        self.period = period
        # This chat's configured answer probability
        self.answer = answer
        # Wether some interactions are restricted to admins only
        self.restricted = restricted
        # Wether messages should silence user mentions
        self.silenced = silenced

    # Sets the period for a chat
    # It has to be higher than 1
    # Returns the new value
    def set_period(self, period):
        if period < 1:
            raise ValueError("Tried to set period a value less than 1.")
        else:
            self.period = period
        return self.period

    # Sets the answer probability
    # It's a percentage represented as a decimal between 0 and 1
    # Returns the new value
    def set_answer(self, prob):
        if prob > 1:
            raise ValueError("Tried to set answer probability higher than 1.")
        elif prob < 0:
            raise ValueError("Tried to set answer probability lower than 0.")
        else:
            self.answer = prob
        return self.answer

    # Dumps the metadata into a list of lines, then joined together in a string,
    # ready to be written into a file
    def dumps(self):
        lines = ["CARD=v5"]
        lines.append("CHAT_ID=" + self.id)
        lines.append("CHAT_TYPE=" + self.type)
        lines.append("CHAT_NAME=" + self.title)
        lines.append("WORD_COUNT=" + str(self.count))
        lines.append("MESSAGE_PERIOD=" + str(self.period))
        lines.append("ANSWER_PROB=" + str(self.answer))
        lines.append("RESTRICTED=" + str(self.restricted))
        lines.append("SILENCED=" + str(self.silenced))
        # lines.append("WORD_DICT=")
        return ("\n".join(lines)) + "\n"

    # Creates a Metadata object from a previous text dump
    def loads(text):
        lines = text.splitlines()
        return Metadata.loadl(lines)

    # Creates a Metadata object from a list of metadata lines
    def loadl(lines):
        # In a perfect world, I would get both the variable name and its corresponding value
        # from each side of the lines, but I know the order in which the lines are writen in
        # the file, I hardcoded it. So I can afford also hardcoding reading it back in the
        # same order, and nobody can stop me
        version = parse_card_line(lines[0]).strip()
        version = (
            version
            if len(version.strip()) > 1
            else (lines[4] if len(lines) > 4 else "LOG_ZERO")
        )
        if version == "v4" or version == "v5":
            return Metadata(
                cid=parse_card_line(lines[1]),
                ctype=parse_card_line(lines[2]),
                title=parse_card_line(lines[3]),
                count=int(parse_card_line(lines[4])),
                period=int(parse_card_line(lines[5])),
                answer=float(parse_card_line(lines[6])),
                restricted=(parse_card_line(lines[7]) == "True"),
                silenced=(parse_card_line(lines[8]) == "True"),
            )
        elif version == "v3":
            # Deprecated: this elif block will be removed in a new version
            print(
                "Warning! This Card format ({}) is deprecated. Update all".format(
                    version
                ),
                "your files in case that there are still some left in old formats before",
                "downloading the next update.",
            )

            # This is kept for retrocompatibility purposes, in case someone did a fork
            # of this repo and still has some chat files that haven't been updated in
            # a long while -- but I already converted all my files to v5
            return Metadata(
                cid=parse_card_line(lines[1]),
                ctype=parse_card_line(lines[2]),
                title=parse_card_line(lines[3]),
                count=int(parse_card_line(lines[7])),
                period=int(parse_card_line(lines[4])),
                answer=float(parse_card_line(lines[5])),
                restricted=(parse_card_line(lines[6]) == "True"),
            )
        elif version == "v2":
            # Deprecated: this elif block will be removed in a new version
            print(
                "Warning! This Card format ({}) is deprecated. Update all".format(
                    version
                ),
                "your files in case that there are still some left in old formats before",
                "downloading the next update.",
            )

            # Also kept for retrocompatibility purposes
            return Metadata(
                cid=parse_card_line(lines[1]),
                ctype=parse_card_line(lines[2]),
                title=parse_card_line(lines[3]),
                count=int(parse_card_line(lines[6])),
                period=int(parse_card_line(lines[4])),
                answer=float(parse_card_line(lines[5])),
            )
        elif version == "dict:":
            # Deprecated: this elif block will be removed in a new version
            print(
                "Warning! This Card format ('dict') is deprecated. Update all",
                "your files in case that there are still some left in old formats before",
                "downloading the next update.",
            )

            # Also kept for retrocompatibility purposes
            # At some point I decided to number the versions of each dictionary format,
            # but this was not always the case. This is what you get if you try to read
            # whatever there is in very old files where the version should be
            return Metadata(
                cid=lines[0],
                ctype=lines[1],
                title=lines[2],
                count=int(lines[5]),
                period=int(lines[3]),
            )
        else:
            # Deprecated: this elif block will be removed in a new version
            print(
                "Warning! This ancient Card format is deprecated. Update all",
                "your files in case that there are still some left in old formats before",
                "downloading the next update.",
            )

            # Also kept for retrocompatibility purposes
            # This is for the oldest of file formats
            return Metadata(
                cid=lines[0], ctype=lines[1], title=lines[2], period=int(lines[3])
            )
