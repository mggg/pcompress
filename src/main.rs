use std::io::prelude::*;
use std::io::BufWriter;
// use serde_json::{json, from_str};
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

    let stdout = std::io::stdout();
    let mut writer = std::io::BufWriter::with_capacity(usize::pow(2, 18), stdout.lock());

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
                    writer = export_json(writer, &mapping);
                    break
                }
            } else {
                writer = export_json(writer, &mapping);
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

    writer.flush().unwrap();
}

fn export_json<W: std::io::Write>(mut writer: BufWriter<W>, mapping: &[usize]) -> BufWriter<W> {
    // println!("{}", json!(mapping));
    writeln!(writer, "{:?}", mapping).unwrap();
    writer
}

fn encode() {
    let mut prev_mapping: Vec<usize> = Vec::new();
    let diff: &mut Vec<Vec<usize>> = &mut vec![vec![]; 40];

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
        let mapping: Vec<usize> = serde_json::from_str(&line).unwrap();
        let (diff, written) = compute_diff(&prev_mapping, &mapping, diff);
        if written {
            writer = export_diff(writer, diff);
            prev_mapping = mapping;
        }
        line.clear();
    }

    writer.flush().unwrap();
}

fn compute_diff<'a>(prev_mapping: &[usize], new_mapping: &[usize], assignment: &'a mut Vec<Vec<usize>>) -> (&'a Vec<Vec<usize>>, bool) {
    assignment.clear();

    let mut written = false;
    // let mut assignment: Vec<Vec<usize>> = vec![vec![]; max_district];
    for (node, district) in new_mapping.iter().enumerate() {
        if node >= prev_mapping.len() || prev_mapping[node] != *district{ // difference detected
            written = true;

            if *district >= assignment.len() {
                assignment.resize(*district+1, vec![]);
            }
            assignment[*district].push(node);
        }
    }
    (assignment, written)
}

fn export_diff<W: std::io::Write>(mut writer: BufWriter<W>, assignment: &[Vec<usize>]) -> BufWriter<W> {
    // Exports diff to custom binary representation

    let mut skipped_districts: u8 = 0;
    for (_district, nodes) in assignment.iter().enumerate() {
        if !nodes.is_empty() {
            if skipped_districts > 0 { // need to write skipped district marker
                writer.write_all(&(u16::MAX - 1).to_be_bytes()).unwrap(); // write district marker (16)
                writer.write_all(&skipped_districts.to_be_bytes()).unwrap(); // write number of skipped district(s) (8)
                skipped_districts = 0;
            }

            for node in nodes { // TODO: sort
                writer.write_all(&(*node as u16).to_be_bytes()).unwrap();
                // write node (16)
            }
        }
        skipped_districts += 1;
    }
    writer.write_all(&u16::MAX.to_be_bytes()).unwrap(); // write district marker (16)
    // write end of assignment marker (16)
    writer
}
