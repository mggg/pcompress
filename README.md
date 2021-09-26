## pcompress
Currently it is hard to store the state of every single step of a normal Markov Chain Monte Carlo from GerryChain Python or GerryChain Julia.
This repo aims to produce an efficient intermediate binary representation of partitions/districting assignments that will enable for generated plans to be saved on-the-fly.
Each step is represented as the diff from the previous step, enabling a significant reduction in disk usage per step.

## Installation
```bash
cargo install pcompress
pip install pcompress
```

## Python Usage
Note that `chain` is a normal MarkovChain object and `graph` is a normal GerryChain graph.

#### Recording

```python
from pcompress import Record

for partition in Record(chain, "pa-run.chain"):
    # normal chain stuff here
```

#### Replaying

```python
from pcompress import Record

for partition in Replay(graph, "pa-run.chain", updaters=my_updaters):
   # normal chain stuff here
```
