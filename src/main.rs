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

    #[structopt(
        long = "diff",
        help = "Only display the deltas across each step when decoding"
    )]
    diff: bool,

    #[structopt(
        short = "l",
        long = "location",
        help = "Replay a specific step of a chain (zero-indexed). Zero replays all.",
        default_value = "0"
    )]
    location: usize,

    #[structopt(
        short = "e",
        long = "extreme",
        help = "Enable compression up to district labelings"
    )]
    extreme: bool,
}

fn main() {
    let stdin = std::io::stdin();
    let reader = std::io::BufReader::with_capacity(usize::pow(2, 24), stdin.lock());

    let stdout = std::io::stdout();
    let writer = std::io::BufWriter::with_capacity(usize::pow(2, 24), stdout.lock());

    let opt = Opt::from_args();
    if opt.decode {
        pcompress::decode::decode(reader, writer, opt.location, opt.diff);
    } else {
        pcompress::encode::encode(reader, writer, opt.extreme);
    }
}
