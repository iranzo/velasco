# Velascobot: Manual

Some notes:

- Scriptorium version: Velasco v4.X (from the "Big Overhaul Update" on 27 Mar, 2019 until the 2nd Overhaul)
  - Recognizable because Readers are Scribes and stored in a big dictionary called the Scriptorium, among others
- Overhaul 2 version: starting with Velasco v5.0

# Updating to Overhaul 2

If you have a Velasco clone or fork from the Scriptorium version, you should follow these steps:

1. First of all, update all your chat files to CARD=v4 format. You can do this by making a script that imports the Archivist, and then loading and saving all files.
2. Then, pull the update.
3. To convert files to the new unescaped UTF-16 encoding (previously the default, escaped UTF-8, was used), edit the `get_reader(...)` function in the Archivist so it uses `load_reader_old(...)` instead of `load_reader(...)`.
4. Make a script that imports the Archivist and calls the `update(...)` function (it loads and saves all files).
5. Revert the `get_reader(...)` edit.

And voilà! You're up to date. Unless you want to switch to the `mongodb` branch (WIP).

# Mechanisms

## Markov chains

This bot uses Markov chains of 3 words for message generation. For each 3 consecutive words read, it will store the 3rd one as the word that follows the first 2 combined. This way, whenever it is generating a new sentence, it will always pick at random one of the stored words that follow the last 2 words of the message generated so far, combined.

## Storing

The actual messages aren't stored. After they're processed and all the words have been assigned to lists under combinations of 2 words, the message is discarded, and only the dictionary with the lists of "following words" is stored. The words said in a chat may be visible, but from a certain point onwards its impossible to recreate with accuracy the exact messages said in a chat.

The storing action is made sometimes when a configuration value is changed, and whenever the bot sends a message. If the bot crashes, all the words processed from the messages since the last one from Velascobot will be lost. For high `period` values, this could be a considerable amount, but for small ones this is negligible. Still, the bot is not expected to crash often.

## Speaker's Memory

The memory of a `Speaker` is a small cache of the `C` most recently modified `Readers` (where `C` is set through a flag; default is `20`). A modified `Reader` is one where the metadata was changed through a command, or a new message has been read. When a new `Reader`is modified that goes over the memory limit, the oldest modified `Reader` is pushed out and saved into its file.

## Reader's Short Term and Long Term Memory

When a message is read, it gets stored in a temporal cache. It will only be processed into the vocabulary `Generator` when the `Reader` is asked to generate a new message, or whenever the `Reader` gets saved into a file. This allows the bot to answer to other recent messages, and not just the last one, when the periodic message is a reply.

## File hierarchy

- `Generator` is the object class that holds a vocabulary dictionary and can generate new messages
- `Metadata` is the object class that holds one chat's configuration flags and other miscellaneous information.
  - Some times the file where the metadata is saved is called a `card`.
- `Reader`is an object class that holds a `Metadata`instance and a `Generator` instance, and is associated with a specific chat.
- `Archivist`is the object class that handles persistence: reading and loading from files.
- `Speaker` is the object class that handles all (or most of) the functions for the commands that Velasco has
  - Holds a limited set of `Readers` that it loads and saves through some `Archivist` functions (borrowed during `Speaker` initialization).
- `velasco.py` is the main file, in charge of starting up the telegram bot itself.

### TODO

After managing to get Velasco back to being somewhat usable, I've already stated in the [News channel](t.me/velascobotnews) that I will focus on rewriting the code into a different language. Thus, I will add no improvements to the Python version from that point onwards. If you're interested of picking this project up and continue development for Python, here's a few suggestions:

- The `speaker.py` is too big. It would be useful to separate it into 2 files, one that has surface command handling, and another one that does all the speech handling (doing checks for `restricted` and `silenced` flags, the `period`, the random chances, ...).
- For a while now, Telegram allows to download a full chat history in a compressed file. Being able to send the compressed file, making sure that it _is_ a Telegram chat history compressed file, and then unpacking and loading it into the chat's `Generator` would be cool.
- The most active chats have files that are too massive to keep in the process' memory. I will probably add a local database in MongoDB to solve that, but it will be a simple local one. Expanding it could be a good idea.
