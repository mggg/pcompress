import matplotlib.pyplot as plt
import pandas as pd
import pcompress
import itertools
import pytest
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

graph = Graph.from_json("../examples/PA_VTDs.json")

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


def test_setup():
    for partition in pcompress.Record(chain, "run.chain"):
        pass


@pytest.mark.parametrize("extreme, geographic", itertools.product([True, False], repeat=2))
def test_inverse(extreme, geographic):
    counter = 0
    c = 0
    # old_partition = []
    partitions = []
    new_partitions = []

    for partition in pcompress.Record(chain, "run.chain", extreme=extreme):
        partitions.append(partition.assignment.to_series())
        assert len(partition.assignment.to_series())
        # assignment = [-1] * len(partition.assignment)  # a little expensive, but defensive TODO: refactor
        # for node, part in partition.assignment.items():
        #     assignment[node] = part - 1

        # assert -1 not in assignment

        # if len(old_partition):
        #     if assignment != old_partition:
        #         partitions.append(assignment)
        #         counter += 1
        # else:
        #     partitions.append(assignment)

        # old_partition = assignment

    for c, partition in enumerate(pcompress.Replay(graph, "run.chain", geographic=geographic)):
        new_partitions.append(partition.assignment.to_series())
        assert len(partition.assignment.to_series())
        # assignment = [-1] * len(partition.assignment)  # a little expensive, but defensive TODO: refactor
        # for node, part in partition.assignment.items():
        #     assignment[node] = part - 1

        # assert -1 not in assignment

        # assignment_orig = partitions.pop(0)
        # assert assignment_orig == assignment, len(assignment_orig)
    assert c == counter

    for partition, new_partition in zip(partitions, new_partitions):
        assert (partition.values == new_partition.values).all()
