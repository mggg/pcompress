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
def test_population(extreme, geographic):
    """
    Test that population counts remain the same
    """
    populations = []
    new_populations = []

    for partition in pcompress.Record(chain, "run.chain", extreme=extreme):
        populations.append(partition.population.values())

    for c, partition in enumerate(pcompress.Replay(graph, "run.chain", geographic=geographic, updaters=my_updaters)):
        new_populations.append(partition.population.values())

    assert len(populations) == len(new_populations)

    for population, new_population in zip(populations, new_populations):
        assert sorted(population) == sorted(new_population)

@pytest.mark.parametrize("geographic", [True, False])
def test_inverse(geographic):
    partitions = []
    new_partitions = []

    for partition in pcompress.Record(chain, "run.chain", extreme=False):
        assignment = partition.assignment.to_series().sort_index()
        assert len(partition.assignment.to_series())
        partitions.append(assignment)

    for c, partition in enumerate(pcompress.Replay(graph, "run.chain", geographic=geographic)):
        new_partitions.append(partition.assignment.to_series().sort_index())
        assert len(partition.assignment.to_series())

    assert len(partitions) == len(new_partitions)

    for partition, new_partition in zip(partitions, new_partitions):
        partition_assignment = list(partition.sort_index())
        new_partition_assignment = list(new_partition.sort_index())
        for i, each_value in enumerate(partition_assignment):
            assert each_value == new_partition_assignment[i], i
