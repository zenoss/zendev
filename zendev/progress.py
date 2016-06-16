import py
from termcolor import colored
from progressbar import ETA, Bar, ProgressBar, Percentage, Timer
from git.remote import RemoteProgress


_translation = {
    None: ('Waiting', 'blue'),
    4:    ('Counting objects', 'white'),
    8:    ('Compressing objects', 'white'),
    16:   ('Writing objects', 'white'),
    32:   ('Receiving objects', 'white'),
    34:   ('Error', 'red'),
    64:   ('Resolving deltas', 'white'),
    66:   ('Done!', 'green')
}

def _translate(op_code):
    s, color = _translation.get(op_code, _translation[34])
    return colored(s.ljust(19), color)


def progress(name, message, max_count, just=20):
    widgets = [
        colored(name.rjust(just), 'cyan'),
        ' ',
        Bar(marker='=', left='[', right=']'),
        ' ',
        message,
    ]
    return ProgressBar(int(max_count), widgets=widgets)



class SimpleGitProgressBar(RemoteProgress):
    def __init__(self, name):
        super(SimpleGitProgressBar, self).__init__()
        self.name = name
        self.op_code = None
        self.bar = progress(self.name, _translate(None), 10, just=len(self.name))
        self.bar.start()

    def update(self, op_code, cur_count, max_count, message=None):
        if op_code != self.op_code:
            self.op_code = op_code
            max_count = int(max_count) if max_count else int(cur_count)
            self.bar = progress(self.name, _translate(op_code), max_count,
                    just=len(self.name))
            self.bar.start()
        cur_count = int(cur_count)
        if (cur_count > self.bar.maxval):
            self.bar.maxval = cur_count
        self.bar.update(cur_count)


class GitProgressBar(object):
    def __init__(self, name, justification=20):
        self.justification = justification
        self.name = name
        self.op_code = None
        self.bar = progress(self.name, _translate(None), 10, just=self.justification)
        res, out, self._err = py.io.StdCaptureFD.call(self.bar.start)

    def get(self):
        return self._err

    def done(self):
        self.update(66, 1, 1)

    def update(self, op_code, cur_count, max_count):
        if op_code != self.op_code:
            self.op_code = op_code
            max_count = int(max_count) if max_count else int(cur_count)
            self.bar = progress(self.name, _translate(op_code), max_count,
                    just=self.justification)
            py.io.StdCaptureFD.call(self.bar.start)
        cur_count = int(cur_count)
        if (cur_count > self.bar.maxval):
            self.bar.maxval = cur_count
        res, out, err = py.io.StdCaptureFD.call(
            self.bar.update, cur_count)
        if err:
            self._err = err
