from .history import ChainMetadata
from .utils import compute_graph_hash, fetch_cached_file

from gerrychain import Partition, GeographicPartition
from typing import Union
import os
import time
import json
import requests
import shutil
import multiprocessing

import subprocess

class Replay:
    def __init__(
        self,
        graph,
        chain_name: Union[str, ChainMetadata],
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

        if isinstance(chain_name, ChainMetadata):
            print("ChainMetadata detected")
            self.filename = f"/tmp/{chain_name.identifier}.chain"
            url = chain_name.url + chain_name.identifier
            fetch_cached_file(url, self.filename)
            # if not os.path.isfile(self.filename):
            #     with requests.get(url, stream=True) as r:
            #         with open(self.filename, 'wb') as f:
            #             shutil.copyfileobj(r.raw, f)
            assert compute_graph_hash(self.graph) == chain_name.graph_hash, "Not the same graph!"
            time.sleep(2)
        else:
            self.filename = chain_name

        self.updaters = updaters
        self.geographic = geographic
        self.flips = flips
        self.executable = executable

        self.args = args
        self.kwargs = kwargs

        if not threads:
            self.threads = multiprocessing.cpu_count()
        else:
            self.threads = threads

        if self.flips and self.executable == "pcompress -d":
            self.executable = "pcompress -d --diff"

        self.child = subprocess.Popen(
            f"/bin/bash -c 'cat {self.filename} | unxz -T {self.threads} | {self.executable}'",
            shell=True,
            stdout=subprocess.PIPE,
        )

        self.counter = 0
        self.length = None

    def __len__(self):
        """
        A slightly expensive way to calculate chain lengths
        """
        if self.length is None:
            counter = subprocess.Popen(
                f"/bin/bash -c 'cat {self.filename} | unxz -T {self.threads} | {self.executable} | wc -l'",
                shell=True,
                stdout=subprocess.PIPE,
            )
            self.length = int(counter.stdout.readline().rstrip())
            counter.terminate()
            counter.wait()

        return self.length

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

            if partition.parent:
                partition.parent.parent = None
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

        assignment = [x for x in assignment]  # GerryChain is 1-indexed

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