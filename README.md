## pcompress
Currently it is hard to store the state of every single step of a normal Markov Chain Monte Carlo from GerryChain Python or GerryChain Julia.
This repo aims to produce an efficient intermediate binary representation of partitions/districting assignments that will enable for generated plans to be saved on-the-fly.
Each step is represented as the diff from the previous step, enabling a significant reduction in disk usage per step.
The intermediate representation is then compressed with LZMA2 (via XZ).

With pcompress, you can save/replay MCMC runs in a portable format, enabling our current use cases such as:
- proactively running MCMC on various states, then replaying at much higher speeds (e.g. 10-30x in PA at the congressional level) for quick analysis turnaround time
- taking advantage of the speed of GerryChain Julia (or [frcw.rs](https://github.com/pjrule/frcw.rs)) while using the rich analysis tooling for GerryChain Python
- saving MCMC runs for easy, exact reproducibility of experiments
- etc.

## Installation
```bash
cargo install pcompress
pip install pcompress
```

## Python Usage (with GerryChain)
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
