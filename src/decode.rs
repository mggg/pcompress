use std::io::{Read, Write, BufWriter};

use super::diff::Diff as Diff;

pub fn decode<R: Read, W: Write>(reader: std::io::BufReader<R>, mut writer: std::io::BufWriter<W>, location: usize, diff: bool) {
    let mut counter = 0;
    let mut district = 0;
    let mut prev_byte = 0;
    let mut mapping: Vec<u8> = Vec::with_capacity(1000);
    let mut delta: Diff = Diff::new();

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
                } else {
                    // mapping.serialize(&mut ser).unwrap();
                    writer = export_mapping(writer, &mapping);
                }
            }
            counter += 1;
            district = 0;
            prev_byte = 0;
            if diff {
                delta.reset();
            }
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
