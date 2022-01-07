from networkx.readwrite import generate_adjlist
import gerrychain
import json
import hashlib
import os
import requests
import shutil
from dateutil.parser import parse


def compute_graph_hash(graph) -> str:
    return hashlib.sha256("".join(generate_adjlist(graph)).encode()).hexdigest()

def fetch_cached_file(url: str, loc: str):
    fetch_file = True
    if os.path.isfile(loc):
        r = requests.head(url, allow_redirects=True)
        last_modified = parse(r.headers['last-modified']).timestamp()
        file_timestamp = os.path.getmtime(loc)

        if file_timestamp >= last_modified: 
            fetch_file = False

    if fetch_file:
        r = requests.get(url, allow_redirects=True)
        # print(r.headers)
        # with open(loc, 'wb') as f:
        #     f.write(r.content)
        with requests.get(url, stream=True) as r:
            with open(loc, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            f.close()
        r.close()