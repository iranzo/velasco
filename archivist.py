
import os, random, pickle
from reader import Reader
from generator import Generator


class Archivist(object):

    def __init__(self, logger, chatdir=None, chatext=None, admin=0,
                 period_inc=5, save_count=15, max_period=100000, max_len=50,
                 read_only=False, filter_cids=None, bypass=False
                 ):
        if chatdir is None or len(chatdir) == 0:
            chatdir = "./"
        elif chatext is None:  # Can be len(chatext) == 0
            raise ValueError("Chatlog file extension is invalid")
        self.logger = logger
        self.chatdir = chatdir
        self.chatext = chatext
        self.admin = admin
        self.period_inc = period_inc
        self.save_count = save_count
        self.max_period = max_period
        self.max_len = max_len
        self.read_only = read_only
        self.filter_cids = filter_cids
        self.bypass = bypass

    def chat_folder(self, *formatting, **key_format):
        return ("./" + self.chatdir + "chat_{tag}").format(*formatting, **key_format)

    def chat_file(self, *formatting, **key_format):
        return ("./" + self.chatdir + "chat_{tag}/{file}{ext}").format(*formatting, **key_format)

    def store(self, tag, data, gen):
        chat_folder = self.chat_folder(tag=tag)
        chat_card = self.chat_file(tag=tag, file="card", ext=".txt")

        if self.read_only:
            return
        try:
            if not os.path.exists(chat_folder):
                os.makedirs(chat_folder, exist_ok=True)
                self.logger.info("Storing a new chat. Folder {} created.".format(chat_folder))
        except Exception:
            self.logger.error("Failed creating {} folder.".format(chat_folder))
            return
        file = open(chat_card, 'w')
        file.write(data)
        file.close()

        if gen is not None:
            chat_record = self.chat_file(tag=tag, file="record", ext=self.chatext)
            file = open(chat_record, 'w', encoding="utf-16")
            file.write(gen)
            file.close()

    def load_vocab(self, tag):
        filepath = self.chat_file(tag=tag, file="record", ext=self.chatext)
        try:
            file = open(filepath, 'r')
            record = file.read().encode().decode('utf-8')
            file.close()
            return record
        except Exception as e:
            self.logger.error("Vocabulary file {} not found.".format(filepath))
            self.logger.exception(e)
            return None

    def load_reader(self, tag):
        filepath = self.chat_file(tag=tag, file="card", ext=".txt")
        try:
            reader_file = open(filepath, 'r')
            reader = reader_file.read()
            reader_file.close()
            return reader
        except OSError:
            self.logger.error("Metadata file {} not found.".format(filepath))
            return None

    def get_reader(self, tag):
        reader = self.load_reader(tag)
        if reader:
            vocab_dump = self.load_vocab(tag)
            if vocab_dump:
                vocab = Generator.loads(vocab_dump)
            else:
                vocab = Generator()
            return Reader.FromCard(reader, vocab, self.max_period, self.logger)
        else:
            return None

    def load_reader_old(self, filename):
        file = open(self.chatdir + filename, 'rb')
        reader = None
        try:
            reader, vocab = Reader.FromFile(pickle.load(file), self)
            self.logger.info("Unpickled {}{}".format(self.chatdir, filename))
        except pickle.UnpicklingError:
            file.close()
            file = open(self.chatdir + filename, 'r')
            try:
                scribe = Reader.FromFile(file.read(), self)
                self.logger.info("Read {}{} text file".format(self.chatdir, filename))
            except Exception as e:
                self.logger.error("Failed reading {}{}".format(self.chatdir, filename))
                self.logger.exception(e)
                raise e
        file.close()
        return scribe

    def chat_count(self):
        count = 0
        directory = os.fsencode(self.chatdir)
        for subdir in os.scandir(directory):
            dirname = subdir.name.decode("utf-8")
            if dirname.startswith("chat_"):
                count += 1
        return count

    def readers_pass(self):
        directory = os.fsencode(self.chatdir)
        for subdir in os.scandir(directory):
            dirname = subdir.name.decode("utf-8")
            if dirname.startswith("chat_"):
                cid = dirname[5:]
                try:
                    reader = self.get_reader(cid)
                    # self.logger.info("Chat {} contents:\n{}".format(cid, reader.card.dumps()))
                    self.logger.info("Successfully passed through {} ({}) chat.\n".format(cid, reader.title()))
                    if self.bypass:  # I forgot what I made this for
                        reader.set_period(random.randint(self.max_period // 2, self.max_period))
                    elif reader.period() > self.max_period:
                        reader.set_period(self.max_period)
                    self.store(*reader.archive())
                    yield reader
                except Exception as e:
                    self.logger.error("Failed passing through {}".format(dirname))
                    self.logger.exception(e)
                    raise e

    def update(self, oldext=None):
        for reader in self.readers_pass():
            try:
                self.store(*reader.archive())
            except Exception as e:
                e.message = e.message[:1000]
                self.logger.exception(e)
                yield reader.cid()
