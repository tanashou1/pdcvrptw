use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use serde::Deserialize;

const HIERARCHICAL_OBJECTIVE_SCALE: f64 = 1_000_000.0;

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
        let instance = serde_json::from_str(&text)
            .with_context(|| format!("failed to parse instance {}", path.display()))?;
        Ok(instance)
    }

    pub fn vehicle_limit(&self, depot_idx: usize) -> usize {
        let depot_id = &self.depots[depot_idx].id;
        self.vehicles_per_depot
            .get(depot_id)
            .copied()
            .unwrap_or_default()
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

    pub fn search_score(&self, route_count: usize, total_distance: f64) -> f64 {
        if self.objective_mode() == "vehicles_then_distance" {
            route_count as f64 * HIERARCHICAL_OBJECTIVE_SCALE + total_distance
        } else {
            total_distance
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
