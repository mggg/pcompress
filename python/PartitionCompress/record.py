from gerrychain import Partition
from collections.abc import Iterable
import pexpect
import pexpect.popen_spawn
import ast

class Record:
    def __init__(self, chain: Iterable[Partition], filename, executable = "PartitionCompress"):
        self.chain = iter(chain)
        self.filename = filename

        self.path = pexpect.which("PartitionCompress")
        self.child = pexpect.popen_spawn.PopenSpawn(f"/bin/bash -c '{self.path} | xz > {self.filename}'")

    def __iter__(self):
        return self

    def __len__(self):
        return len(self.chain)

    def __next__(self):
        try:
            step = next(self.chain)
            state = str([x[1] for x in sorted(step.assignment.to_dict().items(), key=lambda x: x[0])])
            self.child.sendline(state.encode())
            return step

        except StopIteration:
            self.child.sendeof()
            raise

class Replay:
    def __init__(self, graph, filename, updaters = None, executable = "PartitionCompress", *args, **kwargs):
        self.graph = graph
        self.filename = filename
        self.updaters = updaters

        self.args = args
        self.kwargs = kwargs

        self.path = pexpect.which(executable)
        self.child = pexpect.popen_spawn.PopenSpawn(f"/bin/bash -c 'cat {self.filename} | unxz | {self.path} -d'")

    def __iter__(self):
        return self

    def __next__(self):
        assignment_line = self.child.readline()
        if not assignment_line:
            raise StopIteration

        assignment = ast.literal_eval(assignment_line.decode())

        if not isinstance(assignment, list):
            raise TypeError("Invalid chain!")

        return Partition(self.graph, dict(enumerate(assignment)), self.updaters, *self.args, **self.kwargs)
