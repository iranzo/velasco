# Velascobot

This is yet another Markov chain-based chatbot, based on the Twitterbot fad consisting of creating a bot account that would try to generate new random tweets, using your own as a template. However, instead of reading the messages from a Twitter account, this bot is made to read the messages in a group chat, and try to blend in by generating new messages that fit the patterns seen in that specific group chat. At the beginning that will mean a lot of parroting, but eventually the bot starts coming up with sentences of itself.

This bot also works on private chats between a user and itself, but of course the training is much lower and it will feel like talking to a parrot for a longer time, unless you feed it a lot of messages quickly.

## Markov chains

This bot uses Markov chains of 3 words for message generation. For each 3 consecutive words read, it will store the 3rd one as the word that follows the first 2 combined. This way, whenever it is generating a new sentence, it will always pick at random one of the stored words that follow the last 2 words of the message generated so far, combined.

## Storing

The actual messages aren't stored. After they're processed and all the words have been assigned to lists under combinations of 2 words, the message is discarded, and only the dictionary with the lists of "following words" is stored. The words said in a chat may be visible, but from a certain point onwards its impossible to recreate with accuracy the exact messages said in a chat.

The storing action is made sometimes when a configuration value is changed, and whenever the bot sends a message. If the bot crashes, all the words processed from the messages since the last one from Velascobot will be lost. For high `freq` values, this could be a considerable amount, but for small ones this is negligible. Still, the bot is not expected to crash often.

## Configuration commands

### Count

This is the amount of messages that the bot remembers, this is, the amount of messages processed. The messages themselves aren't stored but there is a counter that increases each time a message is processed.

### Freq

It comes from "frequency", and at the beginning it was, but now it's actually the opposite, the "period". This is the amount of messages that the bot waits for before sending a message of its own. Increase it to make it talk less often, and decrease it to make it talk more often.

Sending the command on its own tells you the current value. Sending a positive number with the command will set that as the new value.

### Answer

This value is the chance of the bot to answer to a message that is in turn a reply to one of its own messages, or (to be implemented:) to a message that mentions it. The default value is 0.5 (50% chance). The maximum is 1 (100% chance) and to disable it you must set it to 0 (0% chance).

Sending the command on its own tells you the current value. Sending a positive decimal number between 0 and 1 inclusive will set it as the new value.