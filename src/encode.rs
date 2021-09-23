use std::io::{Read, Write, BufRead, BufWriter};

use super::diff::Diff as Diff;

pub fn encode<R: Read, W: Write>(mut reader: std::io::BufReader<R>, mut writer: std::io::BufWriter<W>, extreme: bool) {
    let mut prev_mapping: Vec<usize> = Vec::new();
    let mut delta: Diff = Diff::new();
    let mut alt_delta: Diff = Diff::new(); // unused if extreme is false

    let mut line = String::new();
    loop {
        let bytes = reader.read_line(&mut line).unwrap();
        if bytes == 0 { // EOF; reset
            break
        }
        let mut mapping: Vec<usize> = serde_json::from_str(line.trim()).expect("Could not read input.");
        let (mut delta, written) = compute_diff(&prev_mapping, &mapping, &mut delta);

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

        line.clear();
    }

    writer.flush().unwrap();
}

fn compute_diff<'a>(prev_mapping: &[usize], new_mapping: &[usize], delta: &'a mut Diff) -> (&'a Diff, bool) {
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

fn export_diff<W: std::io::Write>(mut writer: BufWriter<W>, delta: &Diff) -> BufWriter<W> {
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
