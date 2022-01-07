import pcompress
from gerrychain import Graph

graph = Graph.from_json("../examples/PA_VTDs.json")

def test_search():
    history = pcompress.History()
    results = list(history.search(identifier = "77f48725e3eb16a50df8adac1bc069ef"))
    assert len(results) == 1

    counter = 0
    for partition in pcompress.Replay(graph, results[0]):
        counter += 1

    assert counter

def test_search_one():
    history = pcompress.History()
    result = history.search_one(identifier = "77f48725e3eb16a50df8adac1bc069ef")
    assert result

    counter = 0
    for partition in pcompress.Replay(graph, result):
        counter += 1

    assert counter