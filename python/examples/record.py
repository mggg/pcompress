import matplotlib.pyplot as plt
import pandas as pd
import pcompress
from gerrychain import (
    GeographicPartition,
    Partition,
    Graph,
    MarkovChain,
    proposals,
    updaters,
    constraints,
    accept,
    Election,
)
from gerrychain.proposals import recom
from functools import partial
import tqdm

graph = Graph.from_json("../examples/PA_VTDs.json")
initial_partition = Partition(
    graph,
    assignment="CD_2011",
)

my_updaters = {"population": updaters.Tally("TOTPOP", alias="population")}
initial_partition = GeographicPartition(
    graph, assignment="CD_2011", updaters=my_updaters
)

ideal_population = sum(initial_partition["population"].values()) / len(
    initial_partition
)

# We use functools.partial to bind the extra parameters (pop_col, pop_target, epsilon, node_repeats)
# of the recom proposal.
proposal = partial(
    recom, pop_col="TOTPOP", pop_target=ideal_population, epsilon=0.02, node_repeats=2
)

compactness_bound = constraints.UpperBound(
    lambda p: len(p["cut_edges"]), 2 * len(initial_partition["cut_edges"])
)

pop_constraint = constraints.within_percent_of_ideal_population(initial_partition, 0.02)

chain = MarkovChain(
    proposal=proposal,
    constraints=[pop_constraint],
    accept=accept.always_accept,
    initial_state=initial_partition,
    total_steps=10,
)

for partition in pcompress.Record(chain, "run.chain"):
    print(partition)

## Or, if you want a progress bar
# for partition in pcompress.Record(tqdm.tqdm(chain), "run.chain"):
#     print(partition)
