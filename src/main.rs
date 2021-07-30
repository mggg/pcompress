use std::io::prelude::*;
use serde_json::json;
use structopt::StructOpt;


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
    let mut counter: usize = 0;
    let mut node: usize = 0;
    let mut district: usize = 0; // there cannot be more than 254 districts as 255 and 256 are reserved
    let mut max_district: usize = 0; // district must be zero-indexed
    let mut prev_mapping: Vec<usize> = Vec::with_capacity(65536);
    // let mut prev_mapping: Vec<usize> = vec![0; 65536];
    let mut mapping = prev_mapping.clone();

    loop {
        let mut line = String::new();
        let bytes = std::io::stdin().read_line(&mut line).unwrap();
        if bytes == 0 { // EOF; reset
            break
        }
        if line.contains("END") {
            counter = 0;
            district = 0;
            let (diff, written) = compute_diff(&prev_mapping, &mapping, max_district);
            if written {
                let max_node = mapping.len();
                // export_diff(diff, max_node, max_district, first);
                export_diff(diff.clone(), max_node, max_district, first);

                prev_mapping = mapping.clone();
                first = false;
            }
            continue // continue expecting more
        }

        let input: Vec<&str> = line.split_whitespace().collect();

        if input.len() == 2 {
            // precint district
            node = usize::from_str_radix(input[0], 10).unwrap();
            district = usize::from_str_radix(input[1], 10).unwrap();
        } else if input.len() == 1 {
            // district
            node = counter.clone();
            district = usize::from_str_radix(input[0], 10).unwrap();
        } else {
            panic!();
        }

        if node >= mapping.len() { // add zeros if out of bounds
            mapping.resize(node+1, 0);
            prev_mapping.resize(node+1, 0);
        }
        mapping[node] = district;

        if district >= max_district {
            max_district = district + 1; // assuming district is zero-indexed
        }

        counter += 1;
    }
}

fn compute_diff(prev_mapping: &Vec<usize>, new_mapping: &Vec<usize>, max_district: usize) -> (Vec<Vec<usize>>, bool) {
    let mut written = false;
    let mut assignment: Vec<Vec<usize>> = vec![vec![]; max_district];
    for (node, district) in new_mapping.iter().enumerate() {
        if prev_mapping[node] != *district { // update
            written = true;
            assignment[*district].push(node);
        }
    }
    (assignment, written)
}

fn export_diff(assignment: Vec<Vec<usize>>, max_node: usize, max_district: usize, first: bool) {
    // Exports diff to custom binary representation

    let mut out = std::io::stdout();
    let mut skipped_districts: u8 = 0;
    for i in 0..max_district {
        if assignment[i].len() > 0 {
            if skipped_districts > 0 { // need to write skipped district marker
                if (first && i == 0) { // first one should be zero
                    panic!();
                }
                out.write_all(&(u16::MAX - 1).to_be_bytes()).unwrap(); // write district marker (16)
                out.write_all(&skipped_districts.to_be_bytes()).unwrap(); // write number of skipped district(s) (8)
                out.flush().unwrap();
                skipped_districts = 0;
            }

            for node in assignment[i].clone() { // TODO: sort
                out.write_all(&(node as u16).to_be_bytes()).unwrap();
                out.flush().unwrap();
                // write node (16)
            }
        }
        skipped_districts += 1;
    }
    out.write_all(&u16::MAX.to_be_bytes()).unwrap(); // write district marker (16)
    out.flush().unwrap();
    // write end of assignment marker (16)
}
