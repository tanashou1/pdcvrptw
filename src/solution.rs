use std::collections::HashSet;

#[derive(Debug, Clone)]
pub struct Route {
    pub depot_idx: usize,
    pub vehicle_idx: usize,
    pub stops: Vec<usize>,
}

impl Route {
    pub fn new(depot_idx: usize, vehicle_idx: usize) -> Self {
        Self {
            depot_idx,
            vehicle_idx,
            stops: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct SolutionState {
    pub routes: Vec<Route>,
    pub unassigned_nodes: Vec<usize>,
}

impl SolutionState {
    pub fn used_vehicle_count(&self, depot_idx: usize) -> usize {
        self.routes
            .iter()
            .filter(|route| route.depot_idx == depot_idx)
            .count()
    }

    pub fn is_vehicle_used(&self, vehicle_idx: usize) -> bool {
        self.routes
            .iter()
            .any(|route| route.vehicle_idx == vehicle_idx)
    }

    pub fn route_index_for_vehicle(&self, vehicle_idx: usize) -> Option<usize> {
        self.routes
            .iter()
            .position(|route| route.vehicle_idx == vehicle_idx)
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

        self.unassigned_nodes
            .retain(|node_idx| !remove_set.contains(node_idx));
        self.routes.retain(|route| !route.stops.is_empty());
    }

    pub fn add_unassigned_node(&mut self, node_idx: usize) {
        if !self.unassigned_nodes.contains(&node_idx) {
            self.unassigned_nodes.push(node_idx);
        }
    }

    pub fn add_unassigned_nodes(&mut self, nodes: &[usize]) {
        for &node_idx in nodes {
            self.add_unassigned_node(node_idx);
        }
        self.normalize_unassigned_nodes();
    }

    pub fn take_unassigned_nodes(&mut self) -> Vec<usize> {
        std::mem::take(&mut self.unassigned_nodes)
    }

    pub fn normalize_unassigned_nodes(&mut self) {
        let served = self
            .routes
            .iter()
            .flat_map(|route| route.stops.iter().copied())
            .collect::<HashSet<_>>();
        self.unassigned_nodes
            .retain(|node_idx| !served.contains(node_idx));
        self.unassigned_nodes.sort_unstable();
        self.unassigned_nodes.dedup();
    }
}
