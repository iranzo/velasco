# Velascobot: Manual

**OUTDATED: REVISION PENDING**

## Markov chains

This bot uses Markov chains of 3 words for message generation. For each 3 consecutive words read, it will store the 3rd one as the word that follows the first 2 combined. This way, whenever it is generating a new sentence, it will always pick at random one of the stored words that follow the last 2 words of the message generated so far, combined.

## Storing

The actual messages aren't stored. After they're processed and all the words have been assigned to lists under combinations of 2 words, the message is discarded, and only the dictionary with the lists of "following words" is stored. The words said in a chat may be visible, but from a certain point onwards its impossible to recreate with accuracy the exact messages said in a chat.

The storing action is made sometimes when a configuration value is changed, and whenever the bot sends a message. If the bot crashes, all the words processed from the messages since the last one from Velascobot will be lost. For high `period` values, this could be a considerable amount, but for small ones this is negligible. Still, the bot is not expected to crash often.

## File hierarchy

For those who are interested in cloning or forking:

- `velasco.py` is the file in charge of starting up the telegram bot itself
- `speaker.py` is the file with all the functions for the commands that Velasco has
- A *Speaker* is then the entity that receives the messages, and has 1 *Parrot* and 1 *Scriptorium*
- The *Scriptorium* is a collection of *Scribes*. Each *Scribe* contains the metadata of a chat (title, ID number, the `period`, etc) and the Markov dictionary associated to it
- *Scribes* are defined in `scribe.py`
- A *Parrot* is an entity that contains a Markov dictionary, and the *Speaker's Parrot* corresponds to the last chat that prompted a Velasco message. Whenever that happens, the *Parrot* for that chat is loaded, the corresponding *Scribe* teaches the *Parrot* the latest messages, and then the *Scribe* is stored along with the updated dictionary
- A Markov dictionary is defined in `markov.py`
- The *Archivist* (defined in `archivist.py`) is in charge of doing all file saves and loads

**Warning:** This hierarchy is pending an overhaul.