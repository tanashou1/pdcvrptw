use std::collections::HashSet;

#[derive(Debug, Clone)]
pub struct Route {
    pub depot_idx: usize,
    pub stops: Vec<usize>,
}

impl Route {
    pub fn new(depot_idx: usize) -> Self {
        Self {
            depot_idx,
            stops: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct SolutionState {
    pub routes: Vec<Route>,
}

impl SolutionState {
    pub fn used_vehicle_count(&self, depot_idx: usize) -> usize {
        self.routes
            .iter()
            .filter(|route| route.depot_idx == depot_idx)
            .count()
    }

    pub fn all_nodes(&self) -> Vec<usize> {
        self.routes
            .iter()
            .flat_map(|route| route.stops.iter().copied())
            .collect()
    }

    pub fn remove_nodes(&mut self, nodes: &[usize]) {
        let remove_set = nodes.iter().copied().collect::<HashSet<_>>();

        for route in &mut self.routes {
            route
                .stops
                .retain(|node_idx| !remove_set.contains(node_idx));
        }

        self.routes.retain(|route| !route.stops.is_empty());
    }
}
