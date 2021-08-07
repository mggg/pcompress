import pcompress
from gerrychain import Graph

graph = Graph.from_json("../examples/PA_VTDs.json")

for partition in pcompress.Replay(graph, "run.chain"):
    print(partition)
