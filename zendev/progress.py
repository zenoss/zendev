
import py
from multiprocessing import Pool, Queue
from collections import defaultdict
from termcolor import colored
from progressbar import ETA, Bar, ProgressBar, RotatingMarker
from git.remote import RemoteProgress


class GitProgress(RemoteProgress):
    def __init__(self, name):
        self.name = name
        self.progress = {}
        self.err = ''
        super(GitProgress, self).__init__()

    def _update(self, op_code, cur_count, max_count=None, message=''):
        prog = self.progress.get(op_code)
        if not prog:
            print
            widgets = [
                colored(self.name, 'white'),
                Bar(
                    marker=colored('=', 'blue'),
                    left=colored('  [', 'blue'),
                    right=colored(']  ', 'blue'),
                    ),
                ETA()
            ]
            prog = self.progress[op_code] = ProgressBar(int(max_count), widgets=widgets)
            prog.start()
        prog.update(int(cur_count))

    def update(self, *args, **kwargs):
        res, self.out, self.err = py.io.StdCaptureFD.call(self._update, *args, **kwargs)




class MultiGit(object):
    def __init__(self, repos, concurrency=1):
        self.repos = list(repos)
        self.pool = Pool(concurrency)
    
    def sync(self):
        d = defaultdict(Queue)
        for repo in self.repos:
            repo.progress = MultiprocessingProgress(d[repo])
        def doit(repo):
            repo.sync()
        self.pool.map(doit, self.repos)
        for queue in d.values():
            print queue.get()


