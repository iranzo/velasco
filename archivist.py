
import os, errno, random, pickle
from scribe import Scribe
from markov import Markov

class Archivist(object):

    def __init__(self, logger, chatdir=None, chatext=None, admin=0,
            freqIncrement=5, saveCount=15, maxFreq=100000, maxLen=50,
            readOnly=False, filterCids=None, bypass=False
        ):
        if chatdir is None or len(chatdir) == 0:
            raise ValueError("Chatlog directory name is empty")
        elif chatext is None: # Can be len(chatext) == 0
            raise ValueError("Chatlog file extension is invalid")
        self.logger = logger
        self.chatdir = chatdir
        self.chatext = chatext
        self.admin = admin
        self.freqIncrement = freqIncrement
        self.saveCount = saveCount
        self.maxFreq = maxFreq
        self.maxLen = maxLen
        self.readOnly = readOnly
        self.filterCids = filterCids
        self.bypass = bypass
        self.scribeFolder = chatdir + "chat_{tag}"
        self.scribePath = chatdir + "chat_{tag}/{file}{ext}"

    def store(self, tag, log, gen):
        scribefolder = self.scribeFolder.format(tag=tag)
        cardfile = self.scribePath.format(tag=tag, file="card", ext=".txt")
        if self.readOnly:
            return
        try:
            if not os.path.exists(scribefolder):
                os.makedirs(scribefolder, exist_ok=True)
                self.logger.info("Storing a new chat. Folder {} created.".format(scribefolder))
        except:
            self.logger.error("Failed creating {} folder.".format(scribefolder))
            return
        file = open(cardfile, 'w')
        file.write(log)
        file.close()
        if gen is not None:
            recordfile = self.scribePath.format(tag=tag, file="record", ext=self.chatext)
            file = open(recordfile, 'w')
            file.write(gen)
            file.close()

    def recall(self, filename):
        #print("Loading chat: " + path)
        file = open(self.chatdir + filename, 'rb')
        scribe = None
        try:
            scribe = Scribe.Recall(pickle.load(file), self)
            self.logger.info("Unpickled {}{}".format(self.chatdir, filename))
        except pickle.UnpicklingError:
            file.close()
            file = open(self.chatdir + filename, 'r')
            try:
                scribe = Scribe.Recall(file.read(), self)
                self.logger.info("Read {}{} text file".format(self.chatdir, filename))
            except Exception as e:
                self.logger.error("Failed reading {}{}".format(self.chatdir, filename))
                self.logger.exception(e)
                raise e
        file.close()
        return scribe

    def wakeScribe(self, filepath):
        file = open(filepath.format(filename="card", ext=".txt"), 'r')
        card = file.read()
        file.close()
        return Scribe.FromFile(card, self)

    def wakeParrot(self, tag):
        filepath = self.scribePath.format(tag=tag, file="record", ext=self.chatext)
        try:
            file = open(filepath, 'r')
            #print("\nOPening " + filepath + "\n")
            record = file.read()
            file.close()
            return Markov.loads(record)
        except:
            self.logger.error("Parrot file {} not found.".format(filepath))
            return None

    def wakeScriptorium(self):
        scriptorium = {}

        directory = os.fsencode(self.chatdir)
        for subdir in os.scandir(directory):
            dirname = subdir.name.decode("utf-8")
            if dirname.startswith("chat_"):
                cid = dirname[5:]
                try:
                    filepath = self.chatdir + dirname + "/{filename}{ext}"
                    scriptorium[cid] = self.wakeScribe(filepath)
                    self.logger.info("Chat {} contents:\n".format(cid) + scriptorium[cid].chat.dumps())
                    if self.bypass:
                        scriptorium[cid].setFreq(random.randint(self.maxFreq//2, self.maxFreq))
                    elif scriptorium[cid].freq() > self.maxFreq:
                        scriptorium[cid].setFreq(self.maxFreq)
                except Exception as e:
                    self.logger.error("Failed reading {}".format(dirname))
                    self.logger.exception(e)
                    raise e
        return scriptorium

    """
    def wake_old(self):
        scriptorium = {}

        directory = os.fsencode(self.chatdir)
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if filename.endswith(self.chatext):
                cid = filename[:-(len(self.chatext))]
                if self.filterCids is not None:
                    #self.logger.info("CID " + cid)
                    if not cid in self.filterCids:
                        continue
                scriptorium[cid] = self.recall(filename)
                scribe = scriptorium[cid]
                if scribe is not None:
                    if self.bypass:
                        scribe.setFreq(random.randint(self.maxFreq//2, self.maxFreq))
                    elif scribe.freq() > self.maxFreq:
                        scribe.setFreq(self.maxFreq)
                    self.logger.info("Loaded chat " + scribe.title() + " [" + scribe.cid() + "]"
                                     "\n" + "\n".join(scribe.chat.dumps()))
            else:
                continue
        return scriptorium
    """

    def update(self, oldext=None):
        failed = []
        remove = False
        if not oldext:
            oldext = self.chatext
            remove = True

        directory = os.fsencode(self.chatdir)
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if filename.endswith(oldext):
                try:
                    self.logger.info("Updating chat " + filename)
                    scribe = self.recall(filename)
                    if scribe is not None:
                        scribe.store(scribe.parrot.dumps())
                        self.wakeParrot(scribe.cid())
                        self.logger.info("--- Update done: " + scribe.title())
                        if remove:
                            os.remove(filename)
                except Exception as e:
                    failed.append(filename)
                    self.logger.error("Found the following error when trying to update:")
                    self.logger.exception(e)
            else:
                continue
        return failed
