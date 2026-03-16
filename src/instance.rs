use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use serde::Deserialize;

const HIERARCHICAL_OBJECTIVE_SCALE: f64 = 1_000_000.0;
const OPTIONAL_OBJECTIVE_SCALE: f64 = 1_000_000_000_000.0;
const REQUIRED_OBJECTIVE_SCALE: f64 = 1_000_000_000_000_000_000.0;

fn default_benchmark_group() -> String {
    "synthetic".to_string()
}

fn default_distance_metric() -> String {
    "euclidean_int_half_up".to_string()
}

fn default_load_profile() -> String {
    "balanced_start".to_string()
}

fn default_objective_mode() -> String {
    "distance_only".to_string()
}

fn default_required() -> bool {
    true
}

#[derive(Debug, Clone, Deserialize)]
pub struct TimeWindow {
    pub start: i64,
    pub end: i64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Depot {
    pub id: String,
    pub x: f64,
    pub y: f64,
    pub tw: TimeWindow,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Vehicle {
    pub id: String,
    pub depot_id: String,
}

#[derive(Debug, Clone, Copy, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum NodeKind {
    Pickup,
    Delivery,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Node {
    pub id: String,
    pub request_id: String,
    pub kind: NodeKind,
    pub x: f64,
    pub y: f64,
    pub demand: i32,
    pub service_duration: i64,
    pub tw: TimeWindow,
    pub location_id: String,
    pub time_window_label: String,
    #[serde(default = "default_required")]
    pub required: bool,
    #[serde(default)]
    pub fixed_vehicle_id: Option<String>,
    #[serde(default)]
    pub source_index: Option<usize>,
    #[serde(default)]
    pub sibling_source_index: Option<usize>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct LocationCatalogEntry {
    pub id: String,
    pub x: f64,
    pub y: f64,
    pub home_depot_id: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct InstanceMetadata {
    pub request_count: usize,
    pub node_count: usize,
    pub location_count: usize,
    pub vehicle_count: usize,
    pub variant: String,
    #[serde(default = "default_benchmark_group")]
    pub benchmark_group: String,
    #[serde(default = "default_distance_metric")]
    pub distance_metric: String,
    #[serde(default)]
    pub time_window_distribution: BTreeMap<String, usize>,
    #[serde(default = "default_load_profile")]
    pub load_profile: String,
    #[serde(default = "default_objective_mode")]
    pub objective_mode: String,
    #[serde(default)]
    pub enforce_precedence: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Instance {
    pub name: String,
    pub seed: u64,
    pub planning_horizon: TimeWindow,
    pub capacity: i32,
    pub vehicles_per_depot: BTreeMap<String, usize>,
    pub depots: Vec<Depot>,
    #[serde(default)]
    pub vehicles: Vec<Vehicle>,
    #[serde(default)]
    pub location_catalog: Vec<LocationCatalogEntry>,
    pub nodes: Vec<Node>,
    pub metadata: InstanceMetadata,
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct RequestPair {
    pub request_id: String,
    pub pickup_idx: usize,
    pub delivery_idx: usize,
}

#[derive(Debug, Default)]
struct PairAccumulator {
    pickup_idx: Option<usize>,
    delivery_idx: Option<usize>,
}

impl Instance {
    pub fn from_path(path: &Path) -> Result<Self> {
        let text = fs::read_to_string(path)
            .with_context(|| format!("failed to read instance {}", path.display()))?;
        let instance: Self = serde_json::from_str(&text)
            .with_context(|| format!("failed to parse instance {}", path.display()))?;
        instance
            .normalized()
            .with_context(|| format!("failed to normalize instance {}", path.display()))
    }

    pub fn normalized(mut self) -> Result<Self> {
        if self.vehicles.is_empty() {
            self.vehicles = self.generate_default_vehicles();
        }

        let depot_ids = self
            .depots
            .iter()
            .map(|depot| depot.id.as_str())
            .collect::<BTreeSet<_>>();
        let mut vehicle_counts = BTreeMap::<&str, usize>::new();

        for vehicle in &self.vehicles {
            if !depot_ids.contains(vehicle.depot_id.as_str()) {
                anyhow::bail!(
                    "vehicle {} references unknown depot {}",
                    vehicle.id,
                    vehicle.depot_id
                );
            }
            *vehicle_counts.entry(vehicle.depot_id.as_str()).or_default() += 1;
        }

        for depot in &self.depots {
            let expected = self
                .vehicles_per_depot
                .get(&depot.id)
                .copied()
                .unwrap_or_default();
            let actual = vehicle_counts
                .get(depot.id.as_str())
                .copied()
                .unwrap_or_default();
            if actual != expected {
                anyhow::bail!(
                    "depot {} declares {} vehicles but {} are configured",
                    depot.id,
                    expected,
                    actual
                );
            }
        }

        for node in &self.nodes {
            if let Some(vehicle_id) = &node.fixed_vehicle_id {
                if self.vehicle_idx_by_id(vehicle_id).is_none() {
                    anyhow::bail!(
                        "node {} references unknown fixed vehicle {}",
                        node.id,
                        vehicle_id
                    );
                }
            }
        }

        Ok(self)
    }

    fn generate_default_vehicles(&self) -> Vec<Vehicle> {
        self.depots
            .iter()
            .flat_map(|depot| {
                let count = self
                    .vehicles_per_depot
                    .get(&depot.id)
                    .copied()
                    .unwrap_or_default();
                (0..count).map(move |slot| Vehicle {
                    id: format!("{}_V{:02}", depot.id, slot),
                    depot_id: depot.id.clone(),
                })
            })
            .collect()
    }

    pub fn vehicle_limit(&self, depot_idx: usize) -> usize {
        let depot_id = &self.depots[depot_idx].id;
        self.vehicles
            .iter()
            .filter(|vehicle| vehicle.depot_id == *depot_id)
            .count()
    }

    pub fn uses_double_distance(&self) -> bool {
        self.metadata.distance_metric == "euclidean_double"
    }

    pub fn uses_balanced_start_load(&self) -> bool {
        self.metadata.load_profile == "balanced_start"
    }

    pub fn enforces_precedence(&self) -> bool {
        self.metadata.enforce_precedence
    }

    pub fn objective_mode(&self) -> &str {
        &self.metadata.objective_mode
    }

    pub fn vehicle(&self, vehicle_idx: usize) -> &Vehicle {
        &self.vehicles[vehicle_idx]
    }

    pub fn vehicle_idx_by_id(&self, vehicle_id: &str) -> Option<usize> {
        self.vehicles
            .iter()
            .position(|vehicle| vehicle.id == vehicle_id)
    }

    pub fn vehicle_indices_for_depot(&self, depot_idx: usize) -> Vec<usize> {
        let depot_id = &self.depots[depot_idx].id;
        self.vehicles
            .iter()
            .enumerate()
            .filter_map(|(vehicle_idx, vehicle)| {
                (vehicle.depot_id == *depot_id).then_some(vehicle_idx)
            })
            .collect()
    }

    pub fn depot_idx_by_id(&self, depot_id: &str) -> Option<usize> {
        self.depots.iter().position(|depot| depot.id == depot_id)
    }

    pub fn depot_idx_for_vehicle(&self, vehicle_idx: usize) -> usize {
        self.depot_idx_by_id(&self.vehicle(vehicle_idx).depot_id)
            .expect("vehicle references a known depot")
    }

    pub fn node_is_required(&self, node_idx: usize) -> bool {
        self.nodes[node_idx].required
    }

    pub fn node_is_optional(&self, node_idx: usize) -> bool {
        !self.node_is_required(node_idx)
    }

    pub fn node_is_fixed(&self, node_idx: usize) -> bool {
        self.nodes[node_idx].fixed_vehicle_id.is_some()
    }

    pub fn compatible_vehicle_idx(&self, node_idx: usize) -> Option<usize> {
        self.nodes[node_idx]
            .fixed_vehicle_id
            .as_deref()
            .and_then(|vehicle_id| self.vehicle_idx_by_id(vehicle_id))
    }

    pub fn node_is_compatible_with_vehicle(&self, node_idx: usize, vehicle_idx: usize) -> bool {
        self.compatible_vehicle_idx(node_idx)
            .map(|fixed_vehicle_idx| fixed_vehicle_idx == vehicle_idx)
            .unwrap_or(true)
    }

    pub fn comparison_distance(&self, value: f64) -> f64 {
        if self.uses_double_distance() {
            (value * 100.0).round() / 100.0
        } else {
            value.round()
        }
    }

    pub fn serialise_distance(&self, value: f64) -> f64 {
        if self.uses_double_distance() {
            (value * 1_000_000.0).round() / 1_000_000.0
        } else {
            value.round()
        }
    }

    pub fn search_score(
        &self,
        route_count: usize,
        total_distance: f64,
        missing_required_count: usize,
        missing_optional_count: usize,
    ) -> f64 {
        match self.objective_mode() {
            "vehicles_then_distance" => {
                route_count as f64 * HIERARCHICAL_OBJECTIVE_SCALE + total_distance
            }
            "optional_then_vehicles_then_distance" => {
                missing_required_count as f64 * REQUIRED_OBJECTIVE_SCALE
                    + missing_optional_count as f64 * OPTIONAL_OBJECTIVE_SCALE
                    + route_count as f64 * HIERARCHICAL_OBJECTIVE_SCALE
                    + total_distance
            }
            _ => total_distance,
        }
    }

    pub fn request_pairs(&self) -> Vec<RequestPair> {
        let mut grouped = BTreeMap::<String, PairAccumulator>::new();

        for (node_idx, node) in self.nodes.iter().enumerate() {
            let entry = grouped.entry(node.request_id.clone()).or_default();

            match node.kind {
                NodeKind::Pickup => entry.pickup_idx = Some(node_idx),
                NodeKind::Delivery => entry.delivery_idx = Some(node_idx),
            }
        }

        grouped
            .into_iter()
            .filter_map(|(request_id, accumulator)| {
                Some(RequestPair {
                    request_id,
                    pickup_idx: accumulator.pickup_idx?,
                    delivery_idx: accumulator.delivery_idx?,
                })
            })
            .collect()
    }

    pub fn request_pairs_from_nodes(&self, nodes: &[usize]) -> Vec<RequestPair> {
        let selected_requests = nodes
            .iter()
            .map(|node_idx| self.nodes[*node_idx].request_id.clone())
            .collect::<BTreeSet<_>>();

        self.request_pairs()
            .into_iter()
            .filter(|pair| selected_requests.contains(&pair.request_id))
            .collect()
    }
}

pub fn instance_paths(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut paths = fs::read_dir(dir)
        .with_context(|| format!("failed to list instances in {}", dir.display()))?
        .filter_map(|entry| entry.ok().map(|item| item.path()))
        .filter(|path| {
            path.extension()
                .is_some_and(|extension| extension == "json")
                && path
                    .file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.starts_with("instance_"))
        })
        .collect::<Vec<_>>();

    paths.sort();
    Ok(paths)
}
