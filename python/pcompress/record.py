from gerrychain import Partition, GeographicPartition
from gerrychain.partition.assignment import Assignment
from collections.abc import Iterable
# import ast
import json
import multiprocessing

import subprocess

import functools
import sys


class Record:
    def __init__(
        self,
        chain: Iterable[Partition],
        filename,
        executable="pcompress",
        # executable="pv",
        threads=None,
        extreme=True,
    ):
        self.chain = iter(chain)
        self.filename = filename
        self.extreme = extreme

        if not threads:
            self.threads = multiprocessing.cpu_count()
        else:
            self.threads = threads

        if self.extreme:
            self.child = subprocess.Popen(
                f"{executable} | xz -e -T {self.threads} > {self.filename}",
                shell=True,
                stdin=subprocess.PIPE,
            )
        else:
            self.child = subprocess.Popen(
                f"{executable} | xz -T {self.threads} > {self.filename}",
                shell=True,
                stdin=subprocess.PIPE,
            )

    def __iter__(self):
        return self

    def __len__(self):
        return len(self.chain)

    def __next__(self):
        try:
            step = next(self.chain)
            assignment = list(step.assignment.to_series().sort_index())
            assignment = [x-1 for x in assignment]  # GerryChain is 1-indexed

            state = str(assignment).rstrip() + "\n"
            # self.child.sendline(state.encode())
            self.child.stdin.write(state.encode())
            return step

        except StopIteration:  # kill child process
            self.child.stdin.close()
            self.child.wait()
            raise

    def sendline(self, state):
        # bytestring = b""
        counter = 0
        limit = 1024
        while counter < len(state):
            if counter+limit < len(state):
                # bytestring += state[counter:counter+limit]
                self.child.send(state[counter:counter+limit])
            else:
                # bytestring += state[counter:]
                self.child.send(state[counter:])
            counter += limit

        # assert len(bytestring) == len(state)
        self.child.send("\n".encode())
        return True

class Replay:
    def __init__(
        self,
        graph,
        filename,
        updaters=None,
        executable="pcompress -d",
        # executable="pv",
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

        self.child = subprocess.Popen(
            f"/bin/bash -c 'cat {self.filename} | unxz -T {self.threads} | {executable}'",
            shell=True,
            stdout=subprocess.PIPE,
        )

    def __iter__(self):
        return self

    def __next__(self):
        assignment_line = self.child.stdout.readline()
        if not assignment_line:
            self.child.terminate()
            self.child.wait()
            raise StopIteration

        # assignment = ast.literal_eval(assignment_line.decode().rstrip())
        assignment = json.loads(assignment_line)

        if not isinstance(assignment, list) or not assignment:
            self.child.terminate()
            self.child.wait()
            raise TypeError("Invalid chain!")

        assignment = [x+1 for x in assignment]  # GerryChain is 1-indexed

        if self.geographic:
            return GeographicPartition(
                self.graph,
                dict(enumerate(assignment)),
                # Assignment.from_dict(dict(enumerate(assignment))),
                self.updaters,
                *self.args,
                **self.kwargs,
            )
        else:
            return Partition(
                self.graph,
                dict(enumerate(assignment)),
                # Assignment.from_dict(dict(enumerate(assignment))),
                self.updaters,
                *self.args,
                **self.kwargs,
            )
