import pcompress
from gerrychain import Graph, updaters

graph = Graph.from_json("../examples/PA_VTDs.json")

my_updaters = {"population": updaters.Tally("TOTPOP", alias="population")}

for partition in pcompress.Replay(graph, "run.chain", updaters=my_updaters):
    print(partition.population)
