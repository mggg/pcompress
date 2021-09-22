from gerrychain import Partition, GeographicPartition
from gerrychain.partition.assignment import Assignment
from typing import Iterable
from itertools import chain
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
            if executable == "pcompress":
                executable = "pcompress -e"

            self.child = subprocess.Popen(
                f"{executable} | xz -e -T {self.threads} > {self.filename}",
                # f"{executable} | xz --lzma2=preset=9e,lp=1,lc=0,pb=0,mf=bt3 -T {self.threads} > {self.filename}",
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
            assignment = list(step.assignment.to_series().sort_index().astype(int))
            minimum = min(assignment)
            assignment = [x-minimum for x in assignment]  # GerryChain is sometimes 1-indexed

            state = str(assignment).rstrip() + "\n"
            # self.child.sendline(state.encode())
            self.child.stdin.write(state.encode())
            return step

        except StopIteration:  # kill child process
            self.child.stdin.close()
            self.child.wait()

            self.child.terminate()
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
        flips=True,
        *args,
        **kwargs,
    ):
        self.graph = graph
        self.filename = filename
        self.updaters = updaters
        self.geographic = geographic
        self.flips = flips

        self.args = args
        self.kwargs = kwargs

        if not threads:
            self.threads = multiprocessing.cpu_count()
        else:
            self.threads = threads

        if self.flips and executable == "pcompress -d":
            executable = "pcompress -d --diff"

        self.child = subprocess.Popen(
            f"/bin/bash -c 'cat {self.filename} | unxz -T {self.threads} | {executable}'",
            shell=True,
            stdout=subprocess.PIPE,
        )

        self.counter = 0

    def terminate_child(self):
        """
        A blocking call to terminate the child
        """
        self.child.terminate()
        self.child.wait()

    def __iter__(self):
        return self

    def __next__(self):
        if self.flips:
            partition = self.read_flips()
        else:
            partition = self.read_assignment()

        self.counter += 1
        return partition

    def read_flips(self):
        delta_line = self.child.stdout.readline()
        if not delta_line:
            self.terminate_child()
            raise StopIteration

        # assignment = ast.literal_eval(assignment_line.decode().rstrip())
        delta = json.loads(delta_line)

        if not isinstance(delta, list) or not delta:
            self.terminate_child()
            raise TypeError("Invalid chain!")

        delta_assignment = {}
        for district, nodes in enumerate(delta):  # GerryChain is 1-indexed
            for node in nodes:
                delta_assignment[node] = district+1

        if self.counter == 0:
            args = [
                self.graph,
                delta_assignment,
            ]
            if self.updaters:
                args.append(self.updaters)
            args.extend(self.args)

            if self.geographic:
                self.partition = GeographicPartition(
                    *args,
                    **self.kwargs,
                )
            else:
                self.partition = Partition(
                    *args,
                    **self.kwargs,
                )
        else:
            self.partition = self.partition.flip(delta_assignment)

        return self.partition

    def read_assignment(self):
        assignment_line = self.child.stdout.readline()
        if not assignment_line:
            self.terminate_child()
            raise StopIteration

        # assignment = ast.literal_eval(assignment_line.decode().rstrip())
        assignment = json.loads(assignment_line)

        if not isinstance(assignment, list) or not assignment:
            self.terminate_child()
            raise TypeError("Invalid chain!")

        assignment = [x+1 for x in assignment]  # GerryChain is 1-indexed

        args = [
            self.graph,
            dict(enumerate(assignment)),
        ]
        if self.updaters:
            args.append(self.updaters)
        args.extend(self.args)

        if self.geographic:
            return GeographicPartition(
                *args,
                **self.kwargs,
            )
        else:
            return Partition(
                *args,
                **self.kwargs,
            )
