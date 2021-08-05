use std::io::prelude::*;
use std::io::BufWriter;
// use serde_json::{json, from_str};
use structopt::StructOpt;
use std::cmp;


#[derive(Debug, StructOpt, Clone)]
#[structopt(
    name = "PartitionCompress",
    about = "Efficient district/parition compression format"
)]
struct Opt {
    #[structopt(short = "d", long = "decode")]
    decode: bool,

    #[structopt(short = "l", long = "location", help = "Replay a specific step of a chain (zero-indexed). Zero replays all.", default_value = "0")]
    location: usize,
}

fn main() {
    let opt = Opt::from_args();
    if opt.decode {
        decode(opt.location);
    } else {
        encode();
    }
}

fn decode(location: usize) {
    let mut counter = 0;
    let mut district = 0;
    let mut prev_byte = 0;
    let mut mapping: Vec<usize> = Vec::new();
    let mut skip = true;

    let mut new_district = false;

    for b in std::io::stdin().bytes() {
        let byte = b.unwrap();
        let state = u16::from_be_bytes([prev_byte, byte]);
        prev_byte = byte;

        if skip {
            skip = false;
            continue
        }
        skip = true; // default to reading in two-byte chunks

        if new_district {
            district += u8::from_be_bytes([byte]);
            new_district = false;
            continue
        }

        // Detect special markers
        if state == u16::MAX-1 {
            new_district = true;
            skip = false; // the only time we only want single bytes
            continue
        } else if state == u16::MAX { // export and reset
            if location != 0 {
                if counter == location && location != 0 {
                    export_json(mapping.clone());
                    break
                }
            } else {
                export_json(mapping.clone());
            }
            counter += 1;
            district = 0;
            prev_byte = 0;
            continue
        }

        let node = state as usize;

        // Write
        if node >= mapping.len() { // add zeros if out of bounds
            mapping.resize(node+1, 0);
        }
        mapping[node] = district as usize;
    };
}

fn export_json(mapping: Vec<usize>) {
    println!("{:?}", mapping)
    // println!("{}", json!(mapping));
}

fn encode() {
    let mut first = true; // only used for a plausibilty check; can be removed
    let max_district: usize = 0; // district must be zero-indexed
    let mut prev_mapping: Vec<usize> = Vec::with_capacity(65536);
    // let mut prev_mapping: Vec<usize> = vec![0; 65536];
    let mut mapping = prev_mapping.clone();

    let stdout = std::io::stdout();
    let mut writer = std::io::BufWriter::with_capacity(usize::pow(2, 18), stdout.lock());

    loop {
        let mut line = String::new();
        let bytes = std::io::stdin().read_line(&mut line).unwrap();
        if bytes == 0 { // EOF; reset
            break
        }
        mapping = serde_json::from_str(&line).unwrap();
        prev_mapping.resize(mapping.len()+1, 0);
        let (diff, max_district, written) = compute_diff(&prev_mapping, max_district, &mapping);
        if written {
            let max_node = mapping.len();
            // export_diff(diff, max_node, max_district, first);

            writer = export_diff(writer, diff.clone(), max_node, first);

            prev_mapping = mapping.clone();
            first = false;
        }
        continue // continue expecting more
    }
}

fn compute_diff(prev_mapping: &Vec<usize>, mut max_district: usize, new_mapping: &Vec<usize>) -> (Vec<Vec<usize>>, usize, bool) {
    let mut written = false;
    let mut assignment: Vec<Vec<usize>> = vec![vec![]; 40];
    for (node, district) in new_mapping.iter().enumerate() {
        if prev_mapping[node] != *district { // update
            written = true;
            max_district = cmp::max(max_district+1, *district+1);
            assignment.resize(max_district+1, vec![]);

            assignment[*district].push(node);
        }
    }
    (assignment, max_district, written)
}

fn export_diff<W: std::io::Write>(mut writer: BufWriter<W>, assignment: Vec<Vec<usize>>, max_node: usize, first: bool) -> BufWriter<W> {
    // Exports diff to custom binary representation

    let mut skipped_districts: u8 = 0;
    for (district, nodes) in assignment.iter().enumerate() {
        if nodes.len() > 0 {
            if skipped_districts > 0 { // need to write skipped district marker
                if (first && district == 0) { // first one should be zero
                    panic!();
                }
                writer.write_all(&(u16::MAX - 1).to_be_bytes()).unwrap(); // write district marker (16)
                writer.write_all(&skipped_districts.to_be_bytes()).unwrap(); // write number of skipped district(s) (8)
                writer.flush().unwrap();
                skipped_districts = 0;
            }

            for node in nodes.clone() { // TODO: sort
                writer.write_all(&(node as u16).to_be_bytes()).unwrap();
                writer.flush().unwrap();
                // write node (16)
            }
        }
        skipped_districts += 1;
    }
    writer.write_all(&u16::MAX.to_be_bytes()).unwrap(); // write district marker (16)
    writer.flush().unwrap();
    // write end of assignment marker (16)
    writer
}
