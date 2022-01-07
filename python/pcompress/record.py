from .utils import compute_graph_hash

from gerrychain import Partition
from typing import Iterable
import time
import multiprocessing
import inspect
import getpass
import os
import sys
import git
import requests
import pkg_resources

import subprocess

ESSENTIAL_PKGS = ["pcompress", "gerrychain", "maup", "geopandas", "shapely", "evaltools", "pygeos"]

class Record:
    def __init__(
        self,
        chain: Iterable[Partition],
        filename,
        executable: str = "pcompress",
        # executable="pv",
        threads: int = None,
        extreme: bool = True,
        metadata: dict = {},
        cloud: bool = False,
        cloud_url: str = "http://127.0.0.1:5000",
        api_key: str = None
    ):
        self.chain = iter(chain)
        self.filename = filename
        self.extreme = extreme
        self.executable = executable
        self.cloud = cloud
        self.cloud_url = cloud_url
        self.metadata = metadata
        self.start_time = int(time.time())

        if not api_key:
            self.api_key = os.environ.get("GERRYCHAIN_API_KEY")
        else:
            self.api_key = api_key

        if not threads:
            self.threads = multiprocessing.cpu_count()
        else:
            self.threads = threads

        if self.extreme:
            if self.executable == "pcompress":
                self.executable = "pcompress -e"

            self.child = subprocess.Popen(
                f"{self.executable} | xz -e -T {self.threads} > {self.filename}",
                # f"{self.executable} | xz --lzma2=preset=9e,lp=1,lc=0,pb=0,mf=bt3 -T {self.threads} > {self.filename}",
                shell=True,
                stdin=subprocess.PIPE,
            )
        else:
            self.child = subprocess.Popen(
                f"{self.executable} | xz -T {self.threads} > {self.filename}",
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
            state = str(assignment).rstrip() + "\n"
            self.child.stdin.write(state.encode())
            return step

        except StopIteration:  # kill child process
            self.end_time = int(time.time())

            self.child.stdin.close()
            self.child.wait()

            self.child.terminate()
            self.child.wait()

            if self.cloud:
                time.sleep(1)
                self.metadata |= {
                    "start_timestamp": self.start_time, 
                    "end_timestamp": self.end_time, 
                    "filename": self.filename, 
                    "graph_hash": compute_graph_hash(self.chain.state.graph),
                    "user": getpass.getuser(),
                    "git_commit": None,
                    "git_repo_clean": None,
                    "shasum256": subprocess.run(f"shasum -a 256 {self.filename}", shell=True, capture_output=True).stdout.decode()
                }

                for pkg in ESSENTIAL_PKGS:
                    try:
                        self.metadata[f"{pkg}_version"] = pkg_resources.get_distribution(pkg).version
                    except pkg_resources.DistributionNotFound:
                        self.metadata[f"{pkg}_version"] = "Not installed"
                    self.metadata["python_version"] = sys.version

                try:
                    repo = git.Repo(".", search_parent_directories=True)
                    if repo.index.diff(repo.head.commit) or repo.untracked_files:
                        dirty = True
                        self.metadata["git_repo_clean"] = False
                    else:
                        self.metadata["git_repo_clean"] = True

                    self.metadata["git_commit"] = str(repo.head.commit.hexsha)
                
                    self.metadata["call_stack"] = ",".join(
                        x.filename for x in inspect.stack()
                    ) 

                except (git.exc.InvalidGitRepositoryError, ValueError) as e:
                    pass

                with open(self.filename, "rb") as f:
                    upload_status = requests.post(self.cloud_url, files={
                        "pcompress": f
                    }, data = self.metadata, headers= {
                        "GERRYCHAIN-API-KEY": self.api_key
                    })

                # TODO: switch to using UserWarnings
                if upload_status.status_code == 200:
                    print("Chain object uploaded as:", upload_status.text, "with hash", self.metadata["shasum256"])  
                    self.identifier = upload_status.text
                elif upload_status.status_code == 401:
                    print("Access denied. Upload failed.", file=sys.stderr)
                else:
                    print("Server error. Upload failed.", file=sys.stderr)

            raise
