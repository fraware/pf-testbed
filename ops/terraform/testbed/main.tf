terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "secretmanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com"
  ])
  
  project = var.project_id
  service = each.value
  
  disable_dependent_services = false
  disable_on_destroy        = false
}

# VPC for testbed
resource "google_compute_network" "testbed_vpc" {
  name                    = "testbed-vpc-${var.environment}"
  auto_create_subnetworks = false
  routing_mode           = "REGIONAL"
  
  depends_on = [google_project_service.required_apis]
}

# Subnet for GKE cluster
resource "google_compute_subnetwork" "testbed_subnet" {
  name          = "testbed-subnet-${var.environment}"
  ip_cidr_range = var.subnet_cidr
  network       = google_compute_network.testbed_vpc.id
  region        = var.region
  
  # Enable flow logs for network policy enforcement
  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling       = 0.5
    metadata           = "INCLUDE_ALL_METADATA"
  }
}

# GKE cluster
resource "google_container_cluster" "testbed_cluster" {
  name     = "testbed-cluster-${var.environment}"
  location = var.zone
  
  # Remove default node pool
  remove_default_node_pool = true
  initial_node_count       = 1
  
  # Network configuration
  network    = google_compute_network.testbed_vpc.id
  subnetwork = google_compute_subnetwork.testbed_subnet.id
  
  # Security configuration
  enable_shielded_nodes = true
  
  # Network policy for pod-to-pod communication control
  network_policy {
    enabled = true
    provider = "CALICO"
  }
  
  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block = var.master_cidr
  }
  
  # Master authorized networks
  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "All"
    }
  }
  
  # Release channel for automatic upgrades
  release_channel {
    channel = "REGULAR"
  }
  
  # Maintenance policy
  maintenance_policy {
    recurring_window {
      start_time = "2024-01-01T02:00:00Z"
      end_time   = "2024-01-01T06:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SU"
    }
  }
  
  # Node auto-upgrade and auto-repair
  node_config {
    machine_type = "e2-standard-4"
    disk_size_gb = 100
    disk_type    = "pd-ssd"
    
    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/compute"
    ]
    
    # Shielded instance configuration
    shielded_instance_config {
      enable_integrity_monitoring = true
    }
    
    # Workload metadata configuration
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    # Labels for node selection
    labels = {
      environment = var.environment
      purpose     = "testbed"
    }
    
    # Taints for dedicated nodes
    taint {
      key    = "dedicated"
      value  = "testbed"
      effect = "NO_SCHEDULE"
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# Node pool for testbed workloads
resource "google_container_node_pool" "testbed_nodes" {
  name       = "testbed-nodes-${var.environment}"
  location   = var.zone
  cluster    = google_container_cluster.testbed_cluster.name
  node_count = var.node_count
  
  # Autoscaling configuration
  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }
  
  # Node configuration
  node_config {
    machine_type = "e2-standard-8"
    disk_size_gb = 200
    disk_type    = "pd-ssd"
    
    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/compute"
    ]
    
    # Shielded instance configuration
    shielded_instance_config {
      enable_integrity_monitoring = true
    }
    
    # Workload metadata configuration
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    # Labels for node selection
    labels = {
      environment = var.environment
      purpose     = "testbed"
      workload    = "general"
    }
    
    # Taints for dedicated nodes
    taint {
      key    = "dedicated"
      value  = "testbed"
      effect = "NO_SCHEDULE"
    }
  }
  
  # Management configuration
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  
  # Upgrade strategy
  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }
}

# Service account for GKE nodes
resource "google_service_account" "gke_nodes" {
  account_id   = "gke-nodes-${var.environment}"
  display_name = "GKE Nodes Service Account"
  description  = "Service account for GKE nodes in testbed"
}

# IAM binding for GKE nodes
resource "google_project_iam_binding" "gke_nodes_binding" {
  project = var.project_id
  role    = "roles/container.nodeServiceAccount"
  
  members = [
    "serviceAccount:${google_service_account.gke_nodes.email}"
  ]
}

# Cloud NAT for outbound internet access
resource "google_compute_router" "testbed_router" {
  name    = "testbed-router-${var.environment}"
  region  = var.region
  network = google_compute_network.testbed_vpc.id
}

resource "google_compute_router_nat" "testbed_nat" {
  name                               = "testbed-nat-${var.environment}"
  router                            = google_compute_router.testbed_router.name
  region                            = var.region
  nat_ip_allocate_option            = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall rules for GKE
resource "google_compute_firewall" "gke_master" {
  name    = "gke-master-${var.environment}"
  network = google_compute_network.testbed_vpc.id
  
  allow {
    protocol = "tcp"
    ports    = ["443", "6443"]
  }
  
  source_ranges = [var.master_cidr]
  target_tags   = ["gke-master"]
}

resource "google_compute_firewall" "gke_nodes" {
  name    = "gke-nodes-${var.environment}"
  network = google_compute_network.testbed_vpc.id
  
  allow {
    protocol = "tcp"
    ports    = ["30000-32767"]
  }
  
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["gke-node"]
}

# Outputs
output "cluster_name" {
  value = google_container_cluster.testbed_cluster.name
}

output "cluster_endpoint" {
  value = google_container_cluster.testbed_cluster.endpoint
}

output "cluster_ca_certificate" {
  value = base64decode(google_container_cluster.testbed_cluster.master_auth[0].cluster_ca_certificate)
}

output "vpc_name" {
  value = google_compute_network.testbed_vpc.name
}

output "subnet_name" {
  value = google_compute_subnetwork.testbed_subnet.name
}
