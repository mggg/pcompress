from gerrychain import Graph, Partition, Election
from gerrychain.updaters import Tally, cut_edges
from gerrychain import MarkovChain
from gerrychain.proposals import propose_random_flip
from gerrychain.constraints import single_flip_contiguous
from gerrychain.proposals import recom
from gerrychain.accept import always_accept
from functools import partial
import tqdm


"""
Example taken from the official GerryChain docs:
https://gerrychain.readthedocs.io/en/latest/user/quickstart.html
"""

graph = Graph.from_json("./PA_VTDs.json")

initial_partition = Partition(
    graph,
    assignment="CD_2011",
)


chain = MarkovChain(
    proposal=propose_random_flip,
    constraints=[single_flip_contiguous],
    accept=always_accept,
    initial_state=initial_partition,
    total_steps=100000
)

for partition in tqdm.tqdm(chain):  # Valid output implementation
    print([x[1] for x in sorted(partition.assignment.to_dict().items(), key=lambda x: x[0])])
