# Velascobot

This is yet another Markov chain-based chatbot, based on the Twitterbot fad consisting of creating a bot account that would try to generate new random tweets (usually having `_ebooks` or `.txt` in their names to indicate that an account was one of such, or just a plain `bot` suffix), using your own as a template. However, instead of reading the messages from a Twitter account, this bot is made to read the messages in a group chat, and try to blend in by generating new messages that fit the patterns seen in that specific group chat. At the beginning that will mean a lot of parroting, but eventually the bot starts coming up with sentences of itself.

This bot also works on private chats between a user and itself, but of course the training is much lower and it will feel like talking to a parrot for a longer time, unless you feed it a lot of messages quickly.

## How to use it

You have to add the bot to a chat group, or speak to it privately, letting it read and send messages. Maybe set some configuration commands too.

If you want to clone or fork this repo and host your own instance of Velasco, see [MANUAL.md](MANUAL.md).

## Commands & ussage

### Help, About and Explain

The `/help` command lists the most useful available commands for the bot. The `/about` command has a short explanation on the purpose of this bot, and the `/explain` command goes a little further in detail.

### Speak

This will make the bot send a message, aside from the periodic messages. If the command message is a reply to a different message M, the bot's message will be a reply to M as well; otherwise, the bot will reply to the message with the command.

### Summon

This isn't a command per se, but mentioning the username (in this case, '@velascobot') or any of the configured nicknames (like 'velasco') will prompt a chance for the bot to answer.

A summon of 3 or less words will not be processed, so you can call Velasco's name to your heart's content without having to worry for the bot learning to repeat a lot of short 'Velasco!' messages.

### Count

This tells you the amount of messages that the bot has read so far. The messages themselves aren't stored, but there is a counter that increases each time a message is processed.

### Period

This is the amount of messages that the bot waits for before sending a message of its own. Increase it to make it talk less often, and decrease it to make it talk more often.

Sending the command on its own (e.g. `/period`) tells you the current value. Sending a positive number with the command (e.g. `/period 85`) will set that as the new value.

### Answer

This value is the chance of the bot to answer to a message that is in turn a reply to one of its own messages, or to a message that mentions the bot (see above: [Summon](#summon)). The default value is `0.5` (50% chance). The maximum is `1` (100% chance) and to disable it you must set it to 0 (0% chance).

Sending the command on its own (e.g. `/answer`) tells you the current value. Sending a positive decimal number between `0` and `1` inclusive (e.g. `/answer 0.95`) will set it as the new value.

### Restricted

This toggles the chat's _restriction_ (off by default). Having the chat _restricted_ means that only the administrators of a chat can send configuration commands, like `/period n` or `/answer n`, only they can force the bot to speak with the `/speak` command, and only they can summon the bot. The bot will still read all users' messages and will still send periodic messages for all to enjoy.

### Silenced

This toggles the chat's _silence_ (off by default). Having the chat _silenced_ means that possible user mentions that may appear in randomly generated messages, will be disabled by enveloping the '@' between parentheses. This will avoid Telegram mention notifications, specially useful for those who have the group chat muted.

## When does the bot send a message?

The bot will send a message, guaranteed:

- If someone sends the `/speak` command, and have permissions to do so.
- If `period` messages have been read by the bot since the last time it sent a message.

In addition, the bot will have a random chance to:

- Reply to a message that mentions it (be it the username, like "@velascobot", or a name from a list of given nicknames, like "Velasco").
  - The chance of this is the answer probability configured with the `/answer` command.
  - This does not affect the `period` countdown.
- Send a guaranteed message as a reply to a random recent read message (see [below](#readers-short-term-and-long-term-memory)) instead of sending it normally.
  - The chance of this is the `reply` variable in `Speaker`, and the default is `1`.
- Send a second message just after sending one (never a third one).
  - The chance of this is the `repeat` variable in `Speaker`, and the default is `0.05`.
