use crate::instance::Instance;

#[derive(Debug, Clone)]
pub struct DistanceMatrix {
    size: usize,
    depot_count: usize,
    values: Vec<f64>,
}

impl DistanceMatrix {
    pub fn build(instance: &Instance) -> Self {
        let mut points = Vec::with_capacity(instance.depots.len() + instance.nodes.len());
        points.extend(instance.depots.iter().map(|depot| (depot.x, depot.y)));
        points.extend(instance.nodes.iter().map(|node| (node.x, node.y)));

        let size = points.len();
        let mut values = vec![0.0_f64; size * size];

        for from in 0..size {
            for to in 0..size {
                if from == to {
                    continue;
                }

                let (from_x, from_y) = points[from];
                let (to_x, to_y) = points[to];
                values[from * size + to] = distance_between(instance, from_x, from_y, to_x, to_y);
            }
        }

        Self {
            size,
            depot_count: instance.depots.len(),
            values,
        }
    }

    pub fn distance(&self, from: usize, to: usize) -> f64 {
        self.values[from * self.size + to]
    }

    pub fn depot_location(&self, depot_idx: usize) -> usize {
        depot_idx
    }

    pub fn node_location(&self, node_idx: usize) -> usize {
        self.depot_count + node_idx
    }
}

fn distance_between(instance: &Instance, from_x: f64, from_y: f64, to_x: f64, to_y: f64) -> f64 {
    let dx = from_x - to_x;
    let dy = from_y - to_y;
    let exact = dx.hypot(dy);

    if instance.uses_double_distance() {
        exact
    } else {
        (exact + 0.5).floor()
    }
}
