#!/bin/bash

# Core Version Pinning Script for TB-02
# Updates Helm values and image tags to pin to a specific core version

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HELM_VALUES_DIR="$PROJECT_ROOT/ops/k8s"
TERRAFORM_DIR="$PROJECT_ROOT/ops/terraform/testbed"

# Function to print colored output
print_status() {
    local level=$1
    shift
    case $level in
        "INFO") echo -e "${BLUE}[INFO]${NC} $*" ;;
        "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} $*" ;;
        "WARNING") echo -e "${YELLOW}[WARNING]${NC} $*" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} $*" ;;
    esac
}

# Function to validate version format
validate_version() {
    local version=$1
    
    # Check if version matches semantic versioning (x.y.z)
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$ ]]; then
        print_status "ERROR" "Invalid version format: $version"
        print_status "ERROR" "Expected format: x.y.z or x.y.z-prerelease"
        exit 1
    fi
    
    print_status "INFO" "Version format validated: $version"
}

# Function to update Helm values
update_helm_values() {
    local version=$1
    local values_file="$HELM_VALUES_DIR/values.yaml"
    
    if [[ ! -f "$values_file" ]]; then
        print_status "WARNING" "Helm values file not found: $values_file"
        print_status "INFO" "Creating new values file..."
        mkdir -p "$(dirname "$values_file")"
        cat > "$values_file" << EOF
# Helm values for Provability Fabric Testbed
# Pinned to core version: $version

global:
  coreVersion: "$version"
  imageRegistry: "ghcr.io/provability-fabric"
  imagePullPolicy: IfNotPresent

core:
  image:
    repository: "core"
    tag: "$version"
    pullPolicy: IfNotPresent
  
  resources:
    limits:
      cpu: "1000m"
      memory: "2Gi"
    requests:
      cpu: "500m"
      memory: "1Gi"

gateway:
  image:
    repository: "gateway"
    tag: "$version"
    pullPolicy: IfNotPresent
  
  resources:
    limits:
      cpu: "500m"
      memory: "1Gi"
    requests:
      cpu: "250m"
      memory: "512Mi"

ingress:
  image:
    repository: "ingress"
    tag: "$version"
    pullPolicy: IfNotPresent
  
  resources:
    limits:
      cpu: "250m"
      memory: "512Mi"
    requests:
      cpu: "125m"
      memory: "256Mi"

monitoring:
  prometheus:
    image:
      repository: "prom/prometheus"
      tag: "v2.45.0"
  
  grafana:
    image:
      repository: "grafana/grafana"
      tag: "10.0.0"
EOF
        print_status "SUCCESS" "Created new Helm values file"
    else
        print_status "INFO" "Updating existing Helm values file..."
        
        # Update core version in values file
        if command -v yq >/dev/null 2>&1; then
            # Use yq if available for better YAML handling
            yq eval ".global.coreVersion = \"$version\"" -i "$values_file"
            yq eval ".core.image.tag = \"$version\"" -i "$values_file"
            yq eval ".gateway.image.tag = \"$version\"" -i "$values_file"
            yq eval ".ingress.image.tag = \"$version\"" -i "$values_file"
        else
            # Fallback to sed for basic replacements
            sed -i.bak "s/coreVersion: \".*\"/coreVersion: \"$version\"/g" "$values_file"
            sed -i.bak "s/tag: \".*\"/tag: \"$version\"/g" "$values_file"
            rm -f "${values_file}.bak"
        fi
        
        print_status "SUCCESS" "Updated Helm values file"
    fi
}

# Function to update Terraform variables
update_terraform_vars() {
    local version=$1
    local vars_file="$TERRAFORM_DIR/variables.tf"
    
    if [[ ! -f "$vars_file" ]]; then
        print_status "WARNING" "Terraform variables file not found: $vars_file"
        return 0
    fi
    
    print_status "INFO" "Updating Terraform variables..."
    
    # Update core version in variables.tf
    if grep -q "core_version" "$vars_file"; then
        sed -i.bak "s/default = \".*\"/default = \"$version\"/g" "$vars_file"
        rm -f "${vars_file}.bak"
        print_status "SUCCESS" "Updated Terraform variables"
    else
        print_status "INFO" "Adding core_version variable to Terraform..."
        cat >> "$vars_file" << EOF

variable "core_version" {
  description = "Provability Fabric Core version to deploy"
  type        = string
  default     = "$version"
}
EOF
        print_status "SUCCESS" "Added core_version variable to Terraform"
    fi
}

# Function to update Docker Compose
update_docker_compose() {
    local version=$1
    local compose_file="$PROJECT_ROOT/docker-compose.yml"
    
    if [[ ! -f "$compose_file" ]]; then
        print_status "WARNING" "Docker Compose file not found: $compose_file"
        return 0
    fi
    
    print_status "INFO" "Updating Docker Compose file..."
    
    # Update image tags in docker-compose.yml
    sed -i.bak "s/image:.*:.*/image: ghcr.io\/provability-fabric\/core:$version/g" "$compose_file"
    sed -i.bak "s/image:.*:.*/image: ghcr.io\/provability-fabric\/gateway:$version/g" "$compose_file"
    sed -i.bak "s/image:.*:.*/image: ghcr.io\/provability-fabric\/ingress:$version/g" "$compose_file"
    
    rm -f "${compose_file}.bak"
    print_status "SUCCESS" "Updated Docker Compose file"
}

# Function to update environment variables
update_env_vars() {
    local version=$1
    local env_file="$PROJECT_ROOT/.env.example"
    
    if [[ ! -f "$env_file" ]]; then
        print_status "WARNING" "Environment file not found: $env_file"
        return 0
    fi
    
    print_status "INFO" "Updating environment variables..."
    
    # Update core version in .env.example
    if grep -q "CORE_VERSION" "$env_file"; then
        sed -i.bak "s/CORE_VERSION=.*/CORE_VERSION=$version/g" "$env_file"
    else
        echo "" >> "$env_file"
        echo "# Core version pinning" >> "$env_file"
        echo "CORE_VERSION=$version" >> "$env_file"
    fi
    
    rm -f "${env_file}.bak"
    print_status "SUCCESS" "Updated environment variables"
}

# Function to create version lock file
create_version_lock() {
    local version=$1
    local lock_file="$PROJECT_ROOT/.core-version-lock"
    
    print_status "INFO" "Creating version lock file..."
    
    cat > "$lock_file" << EOF
# Core Version Lock File
# This file pins the Provability Fabric Core version
# Generated: $(date -u)
# Version: $version

CORE_VERSION=$version
LOCK_TIMESTAMP=$(date -u +%s)
LOCK_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
EOF
    
    print_status "SUCCESS" "Created version lock file: $lock_file"
}

# Function to verify changes
verify_changes() {
    local version=$1
    
    print_status "INFO" "Verifying version pinning changes..."
    
    # Check if all files were updated
    local errors=0
    
    # Check Helm values
    if [[ -f "$HELM_VALUES_DIR/values.yaml" ]]; then
        if grep -q "coreVersion: \"$version\"" "$HELM_VALUES_DIR/values.yaml"; then
            print_status "SUCCESS" "Helm values updated correctly"
        else
            print_status "ERROR" "Helm values not updated correctly"
            ((errors++))
        fi
    fi
    
    # Check version lock file
    if [[ -f ".core-version-lock" ]]; then
        if grep -q "CORE_VERSION=$version" ".core-version-lock"; then
            print_status "SUCCESS" "Version lock file created correctly"
        else
            print_status "ERROR" "Version lock file not created correctly"
            ((errors++))
        fi
    fi
    
    if [[ $errors -eq 0 ]]; then
        print_status "SUCCESS" "All version pinning changes verified successfully"
        return 0
    else
        print_status "ERROR" "Version pinning verification failed with $errors errors"
        return 1
    fi
}

# Main function
main() {
    local version=${1:-}
    
    print_status "INFO" "Starting core version pinning process..."
    print_status "INFO" "Script directory: $SCRIPT_DIR"
    print_status "INFO" "Project root: $PROJECT_ROOT"
    
    # Check if version is provided
    if [[ -z "$version" ]]; then
        print_status "ERROR" "No version specified"
        print_status "INFO" "Usage: $0 <version>"
        print_status "INFO" "Example: $0 v1.2.3"
        exit 1
    fi
    
    # Validate version format
    validate_version "$version"
    
    # Check if we're in a git repository
    if [[ ! -d ".git" ]]; then
        print_status "WARNING" "Not in a git repository - some features may not work"
    fi
    
    # Update all configuration files
    update_helm_values "$version"
    update_terraform_vars "$version"
    update_docker_compose "$version"
    update_env_vars "$version"
    
    # Create version lock file
    create_version_lock "$version"
    
    # Verify all changes
    verify_changes "$version"
    
    print_status "SUCCESS" "Core version $version pinned successfully!"
    print_status "INFO" "Next steps:"
    print_status "INFO" "1. Review the changes: git diff"
    print_status "INFO" "2. Commit the changes: git add . && git commit -m 'Pin core version to $version'"
    print_status "INFO" "3. Deploy: make testbed-up"
}

# Run main function with all arguments
main "$@"
