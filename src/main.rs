use std::io::prelude::*;
use std::io::BufWriter;
// use serde_json::{json, from_str};
// use serde_json::{Serializer};
// use serde::ser::Serialize;
use structopt::StructOpt;

// #[global_allocator]
// static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

#[derive(Debug, StructOpt, Clone)]
#[structopt(
    name = "pcompress",
    about = "Efficient district/parition compression format"
)]
struct Opt {
    #[structopt(short = "d", long = "decode")]
    decode: bool,

    #[structopt(long = "diff", help = "Only display the deltas across each step when decoding")]
    diff: bool,

    #[structopt(short = "l", long = "location", help = "Replay a specific step of a chain (zero-indexed). Zero replays all.", default_value = "0")]
    location: usize,

    #[structopt(short = "e", long = "extreme", help = "Enable compression up to district labelings")]
    extreme: bool,
}

pub struct Diff {
    diff: Vec<Vec<usize>>,
}

impl Diff {
    pub fn new() -> Self {
        Self {
            diff: vec![vec![]; 40],
        }
    }
    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            diff: vec![vec![]; capacity],
        }
    }
    pub fn add(&mut self, district: usize, node: usize) { // don't double-add
        if district >= self.diff.len() {
            self.diff.resize(district+1, vec![]);
        }
        self.diff[district].push(node);
    }
    pub fn reset(&mut self) {
        for nodes in &mut self.diff {
            nodes.clear();
        }
    }
}

fn main() {
    let opt = Opt::from_args();
    if opt.decode {
        decode(opt.location, opt.diff);
    } else {
        encode(opt.extreme);
    }
}

fn decode(location: usize, diff: bool) {
    let mut counter = 0;
    let mut district = 0;
    let mut prev_byte = 0;
    let mut mapping: Vec<u8> = Vec::with_capacity(1000);
    let mut delta: Diff = Diff::new();

    let stdin = std::io::stdin();
    let reader = std::io::BufReader::with_capacity(usize::pow(2, 24), stdin.lock());

    let stdout = std::io::stdout();
    let mut writer = std::io::BufWriter::with_capacity(usize::pow(2, 24), stdout.lock());
    // let mut ser = Serializer::new(writer);

    let mut skip = true;
    let mut new_district = false;

    for b in reader.bytes() {
        let byte = b.unwrap();

        if skip { // default to reading in two-byte chunks
            prev_byte = byte;
            skip = false;
            continue
        } else {
            skip = true;
        }

        if new_district {
            // district += u8::from_be_bytes([byte]);
            // assert!(u8::from_be(byte) > 0);
            district += u8::from_be(byte);
            new_district = false;
            continue
        }

        let state = u16::from_be_bytes([prev_byte, byte]);

        // Detect special markers
        if state == u16::MAX-1 {
            new_district = true;
            skip = false; // the only time we only want single bytes
        } else if state == u16::MAX { // export and reset
            if location == 0 || counter == location {
                if diff {
                    writer = export_delta(writer, &mut delta);
                    delta.reset();
                } else {
                    // mapping.serialize(&mut ser).unwrap();
                    writer = export_mapping(writer, &mapping);
                }
            }
            counter += 1;
            district = 0;
            prev_byte = 0;
        } else {
            let node = state as usize;

            // The first entry should be complete
            if counter == 0 && node >= mapping.len() {
                mapping.resize(node+1, 0); // add zeros if out of bounds
            }

            mapping[node] = district;
            if diff {
                delta.add(district as usize, node);
            }
        }
    };

    writer.flush().unwrap();
}

fn export_delta<W: std::io::Write>(mut writer: BufWriter<W>, delta: &mut Diff) -> BufWriter<W> {
    // writer.write_all(format!("{:?}", mapping).as_bytes()).unwrap();
    // writer.write_all(&serde_json::to_string(mapping).unwrap().into_bytes()).unwrap();
    writer.write_all(&serde_json::to_vec(&delta.diff).unwrap()).unwrap();
    writer.write_all("\n".as_bytes()).unwrap();
    writer
}

fn export_mapping<W: std::io::Write>(mut writer: BufWriter<W>, mapping: &[u8]) -> BufWriter<W> {
    // writer.write_all(format!("{:?}", mapping).as_bytes()).unwrap();
    // writer.write_all(&serde_json::to_string(mapping).unwrap().into_bytes()).unwrap();
    writer.write_all(&serde_json::to_vec(mapping).unwrap()).unwrap();
    writer.write_all("\n".as_bytes()).unwrap();
    writer
}

fn encode(extreme: bool) {
    let mut prev_mapping: Vec<usize> = Vec::new();
    let mut delta: Diff = Diff::new();
    let mut alt_delta: Diff = Diff::new(); // unused if extreme is false

    let stdin = std::io::stdin();
    let mut reader = std::io::BufReader::with_capacity(usize::pow(2, 22), stdin.lock());

    let stdout = std::io::stdout();
    let mut writer = std::io::BufWriter::with_capacity(usize::pow(2, 22), stdout.lock());

    let mut line = String::new();
    loop {
        let bytes = reader.read_line(&mut line).unwrap();
        if bytes == 0 { // EOF; reset
            break
        }
        let mut mapping: Vec<usize> = serde_json::from_str(line.trim()).expect("Could not read input.");
        let (mut delta, written) = compute_diff(&prev_mapping, &mapping, &mut delta);

        if written {
            // See if we can swap district labels around for better compression
            if extreme { // assumes only two districts are being swapped
                let mut counter: usize = 0;
                let mut first: usize = 0;
                let mut second: usize = 0;

                for (district, nodes) in delta.diff.iter().enumerate() {
                    if !nodes.is_empty() {
                        if counter == 0 {
                            first = district;
                        } else if counter == 1 {
                            second = district;
                        }
                        counter += 1;
                    }
                }

                if counter == 2 { // ensure only two districts are being swapped
                    let swapped_mapping: Vec<usize> = mapping.iter().map(|district| {
                        if *district == first {
                            return second;
                        } else if *district == second {
                            return first;
                        } else {
                            return *district;
                        }
                    }).collect::<Vec<usize>>();
                    let (alt_delta, _alt_written) = compute_diff(&prev_mapping, &swapped_mapping, &mut alt_delta);
                    if alt_delta.diff.iter().map(|nodes| {nodes.len()}).sum::<usize>() < delta.diff.iter().map(|nodes| {nodes.len()}).sum::<usize>() {
                        mapping = swapped_mapping;
                        delta = alt_delta;
                    }
                }
            }

            writer = export_diff(writer, &delta);
            prev_mapping = mapping;
        }

        line.clear();
    }

    writer.flush().unwrap();
}

pub fn compute_diff<'a>(prev_mapping: &[usize], new_mapping: &[usize], delta: &'a mut Diff) -> (&'a Diff, bool) {
    delta.reset();

    let mut written = false;
    for (node, district) in new_mapping.iter().enumerate() {
        if node >= prev_mapping.len() || prev_mapping[node] != *district { // difference detected
            written = true;
            delta.add(*district, node);
        }
    }
    (delta, written)
}

pub fn export_diff<W: std::io::Write>(mut writer: BufWriter<W>, delta: &Diff) -> BufWriter<W> {
    // Exports diff to custom binary representation
    let mut first = true;

    let mut skipped_districts: u8 = 0;
    for (_district, nodes) in delta.diff.iter().enumerate() {
        if nodes.is_empty() {
            skipped_districts += 1;
        } else {
            // if skipped_districts > 0 { // need to write skipped district marker
            // }
            if ! first {
                writer.write_all(&(u16::MAX - 1).to_be_bytes()).unwrap(); // write district marker (16)
                writer.write_all(&skipped_districts.to_be_bytes()).unwrap(); // write number of skipped district(s) (8)
            }

            for node in nodes { // TODO: sort
                writer.write_all(&(*node as u16).to_be_bytes()).unwrap();
                // write node (16)
            }
            skipped_districts = 1;
        }
        first = false;
    }
    writer.write_all(&u16::MAX.to_be_bytes()).unwrap(); // write district marker (16)
    // write end of diff marker (16)
    writer
}
