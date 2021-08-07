## pcompress
Currently it is hard to store the state of every single step of a normal Markov Chain Monte Carlo from GerryChain Python or GerryChain Julia.
This repo aims to produce an efficient binary representation of partitions/districting assignments that will enable for generated plans to be saved on-the-fly.
Each step is represented as the diff from the previous step, enabling a significant reduction in disk usage per step.

Note that if a step repeats, it will be omitted.

## Usage
See [`chain_flip`](https://github.com/InnovativeInventor/pcompress/blob/main/examples/chain_flip.py) and [`chain.sh`](https://github.com/InnovativeInventor/pcompress/blob/main/examples/chain.sh).

To decode, simply pipe the compressed output into `pcompress --decode`.

## Binary Representation
TODO: document this.

## Further compression
If you want to compress the output file further, `xz` is recommended.
With `xz` and pcompress, quite a few orders of magnitude of compression can be achieved.

E.g.:
```
xz -9 -k chain.output
```

## TODOs
- [ ] better checking/guarding against overflows
- [ ] variable sizes
- [ ] header format?
- [ ] rewind functionality
- [ ] poc of GerryChain Python and Julia rewind/replay

