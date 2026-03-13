use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use serde::Deserialize;

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
    pub distance_metric: String,
    pub time_window_distribution: BTreeMap<String, usize>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Instance {
    pub name: String,
    pub seed: u64,
    pub planning_horizon: TimeWindow,
    pub capacity: i32,
    pub vehicles_per_depot: BTreeMap<String, usize>,
    pub depots: Vec<Depot>,
    pub location_catalog: Vec<LocationCatalogEntry>,
    pub nodes: Vec<Node>,
    pub metadata: InstanceMetadata,
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
