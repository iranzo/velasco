
import os, errno, random, pickle
from chatreader import ChatReader as Reader
from generator import Generator


class Archivist(object):

    def __init__(self, logger, chatdir=None, chatext=None, admin=0,
                 freq_increment=5, save_count=15, max_period=100000, max_len=50,
                 read_only=False, filter_cids=None, bypass=False
                 ):
        if chatdir is None or len(chatdir) == 0:
            raise ValueError("Chatlog directory name is empty")
        elif chatext is None: # Can be len(chatext) == 0
            raise ValueError("Chatlog file extension is invalid")
        self.logger = logger
        self.chatdir = chatdir
        self.chatext = chatext
        self.admin = admin
        self.freq_increment = freq_increment
        self.save_count = save_count
        self.max_period = max_period
        self.max_len = max_len
        self.read_only = read_only
        self.filter_cids = filter_cids
        self.bypass = bypass
    
    def chat_folder(self, *formatting, **key_format):
        return (self.chatdir + "chat_{tag}").format(*formatting, **key_format)

    def chat_file(self, *formatting, **key_format):
        return (self.chatdir + "chat_{tag}/{file}{ext}").format(*formatting, **key_format)

    def store(self, tag, log, gen):
        chat_folder = self.chat_folder(tag=tag)
        chat_card = self.chat_file(tag=tag, file="card", ext=".txt")
        if self.read_only:
            return
        try:
            if not os.path.exists(chat_folder):
                os.makedirs(chat_folder, exist_ok=True)
                self.logger.info("Storing a new chat. Folder {} created.".format(chat_folder))
        except:
            self.logger.error("Failed creating {} folder.".format(chat_folder))
            return
        file = open(chat_card, 'w')
        file.write(log)
        file.close()
        if gen is not None:
            chat_record = self.chat_file(tag=tag, file="record", ext=self.chatext)
            file = open(chat_record, 'w')
            file.write(gen)
            file.close()

    def get_reader(self, filename):
        file = open(self.chatdir + filename, 'rb')
        scribe = None
        try:
            reader, vocab = Reader.FromFile(pickle.load(file), self)
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

    def load_reader(self, filepath):
        file = open(filepath.format(filename="card", ext=".txt"), 'r')
        card = file.read()
        file.close()
        return Reader.FromCard(card, self)

    def wakeParrot(self, tag):
        filepath = self.chat_file(tag=tag, file="record", ext=self.chatext)
        try:
            file = open(filepath, 'r')
            record = file.read()
            file.close()
            return Generator.loads(record)
        except:
            self.logger.error("Record file {} not found.".format(filepath))
            return None

    def readers_pass(self):
        directory = os.fsencode(self.chatdir)
        for subdir in os.scandir(directory):
            dirname = subdir.name.decode("utf-8")
            if dirname.startswith("chat_"):
                cid = dirname[5:]
                try:
                    filepath = self.chatdir + dirname + "/{filename}{ext}"
                    reader = self.load_reader(filepath)
                    self.logger.info("Chat {} contents:\n".format(cid) + reader.card.dumps())
                    if self.bypass:
                        reader.set_period(random.randint(self.max_period//2, self.max_period))
                    elif scriptorium[cid].freq() > self.max_period:
                        scriptorium[cid].setFreq(self.max_period)
                except Exception as e:
                    self.logger.error("Failed reading {}".format(dirname))
                    self.logger.exception(e)
                    raise e

    """
    def wake_old(self):
        scriptorium = {}

        directory = os.fsencode(self.chatdir)
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if filename.endswith(self.chatext):
                cid = filename[:-(len(self.chatext))]
                if self.filter_cids is not None:
                    #self.logger.info("CID " + cid)
                    if not cid in self.filter_cids:
                        continue
                scriptorium[cid] = self.recall(filename)
                scribe = scriptorium[cid]
                if scribe is not None:
                    if self.bypass:
                        scribe.setFreq(random.randint(self.max_period//2, self.max_period))
                    elif scribe.freq() > self.max_period:
                        scribe.setFreq(self.max_period)
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
