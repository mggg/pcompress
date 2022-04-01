pub struct Diff {
    pub diff: Vec<Vec<usize>>,
}

impl Diff {
    pub fn new() -> Self {
        Self {
            diff: vec![vec![]],
        }
    }
    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            diff: vec![vec![]; capacity],
        }
    }
    pub fn add(&mut self, district: usize, node: usize) {
        // don't double-add
        if district >= self.diff.len() {
            self.diff.resize(district + 1, vec![]);
        }
        self.diff[district].push(node);
    }
    pub fn reset(&mut self) {
        for nodes in &mut self.diff {
            nodes.clear();
        }
    }
}
