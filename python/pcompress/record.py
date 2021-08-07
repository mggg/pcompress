from gerrychain import Partition, GeographicPartition
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
        executable="PartitionCompress",
        threads=None,
        extreme=False,
    ):
        self.chain = iter(chain)
        self.filename = filename

        self.path = pexpect.which("PartitionCompress")
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
            state = str(list(step.assignment.to_series()))
            self.child.sendline(state.encode())
            return step

        except StopIteration:
            self.child.sendeof()
            self.child.wait()
            pexpect.popen_spawn.PopenSpawn(
                f"xz -T {self.threads} {self.filename}.tmp"
            ).wait()
            pexpect.popen_spawn.PopenSpawn(
                f"mv {self.filename}.tmp.xz {self.filename}"
            ).wait()
            raise


class Replay:
    def __init__(
        self,
        graph,
        filename,
        updaters=None,
        executable="PartitionCompress",
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
            f"/bin/bash -c 'cat {self.filename} | unxz -T {self.threads} | {self.path} -d'"
        )

    def __iter__(self):
        return self

    def __next__(self):
        assignment_line = self.child.readline()
        if not assignment_line:
            raise StopIteration

        assignment = ast.literal_eval(assignment_line.decode())

        if not isinstance(assignment, list):
            raise TypeError("Invalid chain!")

        if self.geographic:
            return GeographicPartition(
                self.graph,
                dict(enumerate(assignment)),
                self.updaters,
                *self.args,
                **self.kwargs,
            )
        else:
            return Partition(
                self.graph,
                dict(enumerate(assignment)),
                self.updaters,
                *self.args,
                **self.kwargs,
            )
