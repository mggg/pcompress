from gerrychain import Partition, GeographicPartition
from gerrychain.partition.assignment import Assignment
from collections.abc import Iterable
import pexpect
import pexpect.popen_spawn
import ast
import multiprocessing


class Record:
    def __init__(
        self,
        chain: Iterable[Partition],
        filename,
        executable="pcompress",
        threads=None,
        extreme=False,
    ):
        self.chain = iter(chain)
        self.filename = filename
        self.extreme = extreme

        self.path = pexpect.which("pcompress")
        self.child = pexpect.popen_spawn.PopenSpawn(
            f"/bin/bash -c '{self.path} > {self.filename}.tmp'"
        )
        # TODO: add overwrite warnings/protection

        if not threads:
            self.threads = multiprocessing.cpu_count()
        else:
            self.threads = threads

    def __iter__(self):
        return self

    def __len__(self):
        return len(self.chain)

    def __next__(self):
        try:
            step = next(self.chain)
            assignment = list(step.assignment.to_series())

            state = str(assignment)
            self.sendline(state.encode())
            return step

        except StopIteration:
            self.child.sendeof()
            self.child.wait()
            if self.extreme:
                pexpect.popen_spawn.PopenSpawn(
                    f"xz -e -T {self.threads} {self.filename}.tmp"
                ).wait()
            else:
                pexpect.popen_spawn.PopenSpawn(
                    f"xz -T {self.threads} {self.filename}.tmp"
                ).wait()
            pexpect.popen_spawn.PopenSpawn(
                f"mv {self.filename}.tmp.xz {self.filename}"
            ).wait()
            raise

    def sendline(self, state):
        counter = 0
        limit = 1024
        while counter < len(state):
            if counter+limit < len(state):
                self.child.send(state[counter:counter+limit])
            else:
                self.child.send(state[counter:])
            counter += limit
        if counter == len(state):
            self.child.send("\n".encode())
            return True

class Replay:
    def __init__(
        self,
        graph,
        filename,
        updaters=None,
        executable="pcompress",
        threads=None,
        geographic=False,
        *args,
        **kwargs,
    ):
        self.graph = graph
        self.filename = filename
        self.updaters = updaters
        self.geographic = geographic

        self.args = args
        self.kwargs = kwargs

        if not threads:
            self.threads = multiprocessing.cpu_count()
        else:
            self.threads = threads

        self.path = pexpect.which(executable)
        self.child = pexpect.popen_spawn.PopenSpawn(
            f"/bin/bash -c 'cat {self.filename} | unxz -T {self.threads} | {self.path} -d'",
        )

    def __iter__(self):
        return self

    def __next__(self):
        assignment_line = self.child.readline()
        if not assignment_line:
            raise StopIteration

        assignment = ast.literal_eval(assignment_line.decode().rstrip())

        if not isinstance(assignment, list):
            raise TypeError("Invalid chain!")

        # print(assignment)
        assignment = [x+1 for x in assignment]  # GerryChain is 1-indexed

        if self.geographic:
            return GeographicPartition(
                self.graph,
                # dict(enumerate(assignment)),
                Assignment.from_dict(dict(enumerate(assignment))),
                self.updaters,
                *self.args,
                **self.kwargs,
            )
        else:
            return Partition(
                self.graph,
                # dict(enumerate(assignment)),
                Assignment.from_dict(dict(enumerate(assignment))),
                self.updaters,
                *self.args,
                **self.kwargs,
            )
