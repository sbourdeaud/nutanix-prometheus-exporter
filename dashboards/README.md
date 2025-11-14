# Grafana Dashboards for Nutanix Prometheus Exporter

This directory contains example Grafana dashboards for visualizing metrics collected by the Nutanix Prometheus Exporter.

## Available Dashboards

### 1. Nutanix Infrastructure Overview (`nutanix-overview.json`)
A high-level overview dashboard providing a quick snapshot of your entire Nutanix infrastructure.

**Key Metrics:**
- Total clusters, hosts/nodes, VMs, and storage containers
- Cluster resource utilization (CPU, memory)
- VM power state distribution
- Storage container encryption status
- Total vCPUs and vRAM

**Use Case:** Executive dashboards, NOC screens, quick health checks

### 2. Nutanix Cluster Details (`nutanix-cluster-details.json`)
Detailed metrics for individual clusters or cluster groups.

**Key Metrics:**
- Cluster CPU and memory utilization over time
- Storage performance (IOPS, latency, bandwidth)
- Storage container counts by replication factor (RF1, RF2, RF3)
- Encrypted storage container counts
- Cluster resource summary table

**Use Case:** Cluster performance monitoring, capacity planning, troubleshooting

### 3. Nutanix Hosts/Node Details (`nutanix-hosts-details.json`)
Host-level metrics for physical nodes in the cluster.

**Key Metrics:**
- Host CPU and memory utilization
- Storage performance per host
- Disk counts (total, SSD PCIe, SSD SATA)
- VMs per host
- Host resource summary

**Use Case:** Host performance analysis, capacity planning, hardware monitoring

### 4. Nutanix VM Details (`nutanix-vms-details.json`)
Virtual machine metrics and statistics.

**Key Metrics:**
- VM power state (on/off counts)
- VM protection status
- NGT (Nutanix Guest Tools) status
- VM I/O performance
- VM CPU and memory usage
- Boot type distribution (UEFI/Legacy)
- GPU-enabled VMs
- VM resource summary (vDisks, vNICs, vCPUs, vRAM)

**Use Case:** VM performance monitoring, resource optimization, capacity planning

### 5. Nutanix Storage Details (`nutanix-storage-details.json`)
Storage infrastructure metrics and capacity information.

**Key Metrics:**
- Storage container capacity (logical usage, reserved capacity)
- Storage container I/O performance
- Storage container counts (total, encrypted, by replication factor)
- Volume group counts
- Storage container details table

**Use Case:** Storage capacity planning, performance monitoring, optimization

## Prerequisites

Before importing these dashboards, ensure you have:

1. **Grafana 9.x or later** installed and running
2. **Prometheus** configured and scraping metrics from the Nutanix Prometheus Exporter
3. **Prometheus data source** configured in Grafana
4. **Nutanix Prometheus Exporter** running and collecting metrics

### Prometheus Configuration

Your Prometheus configuration should include a scrape job for the exporter:

```yaml
scrape_configs:
  - job_name: 'nutanix-exporter'
    static_configs:
      - targets: ['nutanix-exporter:8000']
    scrape_interval: 30s
    scrape_timeout: 10s
```

### Data Source Setup in Grafana

1. Go to **Configuration** → **Data Sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Configure:
   - **URL**: Your Prometheus server URL (e.g., `http://prometheus:9090`)
   - **Access**: Server (default)
5. Click **Save & Test**

## Importing Dashboards

### Method 1: Import from JSON File (Recommended)

1. **Open Grafana** and log in
2. Navigate to **Dashboards** → **Import**
3. Click **Upload JSON file**
4. Select the dashboard JSON file from this directory
5. Review the import settings:
   - **Name**: Dashboard name (can be modified)
   - **Folder**: Choose a folder or create a new one
   - **Unique identifier (uid)**: Leave as-is or modify
   - **Data source**: Select your Prometheus data source
6. Click **Import**

### Method 2: Copy/Paste JSON

1. Open the dashboard JSON file in a text editor
2. Copy the entire contents
3. In Grafana, go to **Dashboards** → **Import**
4. Paste the JSON into the **Import via panel json** text area
5. Click **Load**
6. Configure as in Method 1, step 5
7. Click **Import**

### Method 3: Using Grafana CLI (for automation)

```bash
# Using grafana-cli (if available)
grafana-cli admin import-dashboard /path/to/nutanix-overview.json

# Or using API
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @nutanix-overview.json
```

## Dashboard Variables

Most dashboards include variables for filtering:

- **DS_PROMETHEUS**: Data source selector (auto-configured)
- **cluster**: Filter by cluster name (in cluster details dashboard)
- **host**: Filter by host name (in hosts dashboard)
- **vm**: Filter by VM name (in VMs dashboard)
- **entity**: Filter by entity (cluster/host name)
- **storage_container**: Filter by storage container (in storage dashboard)

Variables support:
- **All** option to show all entities
- **Multi-select** for comparing multiple entities
- **Auto-refresh** to update available values

## Metric Naming Conventions

The exporter uses the following metric naming patterns:

### Count Metrics
- `nutanix_count_*` - Entity counts with `entity` label
- Examples:
  - `nutanix_count_cluster{entity="cluster-name"}`
  - `nutanix_count_vm{entity="cluster-name"}`
  - `nutanix_count_node{entity="cluster-name"}`

### Cluster Stats
- `nutanix_clustermgmt_cluster_stats_*` - Cluster statistics with `cluster` label
- Examples:
  - `nutanix_clustermgmt_cluster_stats_hypervisor_cpu_usage_ppm{cluster="cluster-name"}`
  - `nutanix_clustermgmt_cluster_stats_hypervisor_memory_usage_ppm{cluster="cluster-name"}`

### Host Stats
- `nutanix_clustermgmt_host_stats_*` - Host statistics with `host` label
- Examples:
  - `nutanix_clustermgmt_host_stats_hypervisor_cpu_usage_ppm{host="host-name"}`
  - `nutanix_clustermgmt_host_stats_hypervisor_memory_usage_ppm{host="host-name"}`

### VM Stats
- `nutanix_vmm_ahv_stats_vm_*` - VM statistics with `vm` label
- Examples:
  - `nutanix_vmm_ahv_stats_vm_hypervisor_cpu_usage_ppm{vm="vm-name"}`
  - `nutanix_vmm_ahv_stats_vm_hypervisor_memory_usage_ppm{vm="vm-name"}`

### Storage Container Stats
- `nutanix_clustermgmt_storage_container_stats_*` - Storage container statistics with `storage_container` label
- Examples:
  - `nutanix_clustermgmt_storage_container_stats_logical_usage_bytes{storage_container="container-name"}`
  - `nutanix_clustermgmt_storage_container_stats_reserved_capacity_bytes{storage_container="container-name"}`

## Example PromQL Queries

### Cluster CPU Usage Percentage
```promql
avg(nutanix_clustermgmt_cluster_stats_hypervisor_cpu_usage_ppm) / 10000
```

### Total VMs Across All Clusters
```promql
sum(nutanix_count_vm)
```

### VMs Powered On vs Off
```promql
sum(nutanix_count_vm_on)
sum(nutanix_count_vm_off)
```

### Storage Container Capacity Usage
```promql
nutanix_clustermgmt_storage_container_stats_logical_usage_bytes
```

### Host I/O Performance
```promql
rate(nutanix_clustermgmt_host_stats_storage_tier_ssd_controller_io_bandwidth_kbps[5m])
```

### VM Memory Usage Percentage
```promql
avg(nutanix_vmm_ahv_stats_vm_hypervisor_memory_usage_ppm) / 10000
```

### Encrypted Storage Containers Count
```promql
sum(nutanix_count_storage_container_encrypted)
```

## Troubleshooting

### No Data Appearing

1. **Verify Prometheus is scraping the exporter:**
   ```bash
   curl http://prometheus:9090/api/v1/targets
   ```
   Check that the nutanix-exporter target is UP.

2. **Verify metrics are being exported:**
   ```bash
   curl http://nutanix-exporter:8000/metrics | grep nutanix
   ```

3. **Check data source connection:**
   - In Grafana, go to Configuration → Data Sources
   - Click on your Prometheus data source
   - Click "Save & Test"
   - Verify it shows "Data source is working"

4. **Verify time range:**
   - Ensure your dashboard time range includes when metrics were collected
   - Try "Last 6 hours" or "Last 24 hours"

### Variables Not Populating

1. **Check if metrics exist:**
   ```bash
   curl http://prometheus:9090/api/v1/label/entity/values
   ```

2. **Verify label names:**
   - Different metrics use different labels (`entity`, `cluster`, `host`, `vm`, `storage_container`)
   - Check the metric naming conventions above

3. **Update variable query:**
   - Edit the dashboard
   - Go to Dashboard Settings → Variables
   - Verify the query matches available metrics

### Panels Showing "No Data"

1. **Check metric names:**
   - Some metrics may not be available if certain features are disabled
   - Verify the exporter configuration matches the dashboard expectations

2. **Check label filters:**
   - Ensure variable values match actual label values
   - Try selecting "All" in variables

3. **Verify metric collection:**
   - Check exporter logs for errors
   - Verify environment variables are set correctly

### Performance Issues

1. **Reduce time range** for faster queries
2. **Use rate() functions** for counter metrics
3. **Limit variable selections** to fewer entities
4. **Increase Prometheus query timeout** if needed

## Customization

### Modifying Dashboards

1. **Edit in Grafana:**
   - Open the dashboard
   - Click the gear icon (⚙️) → **Settings**
   - Click **JSON Model** to edit the raw JSON
   - Or use the visual editor to modify panels

2. **Add New Panels:**
   - Click **Add** → **Visualization**
   - Select **Prometheus** as data source
   - Use the metric naming conventions above

3. **Modify Variables:**
   - Dashboard Settings → Variables
   - Edit queries to match your environment

### Creating Custom Dashboards

Use these dashboards as templates:

1. Copy a similar dashboard JSON
2. Modify panel queries
3. Adjust panel positions and sizes
4. Update dashboard title and tags
5. Change the UID to avoid conflicts

## Dashboard Refresh Intervals

All dashboards are configured with:
- **Auto-refresh**: 30 seconds (can be changed in dashboard settings)
- **Default time range**: Last 6 hours
- **Time picker**: Enabled

To modify:
1. Open dashboard
2. Click time picker (top right)
3. Adjust refresh interval
4. Change time range as needed

## Best Practices

1. **Start with Overview Dashboard:**
   - Import the overview dashboard first
   - Verify data is appearing correctly
   - Then import detailed dashboards

2. **Organize in Folders:**
   - Create a "Nutanix" folder in Grafana
   - Import all dashboards into this folder
   - Makes management easier

3. **Set Up Alerts:**
   - Use Grafana alerting features
   - Create alerts for critical metrics
   - Example: Alert when cluster CPU > 80%

4. **Regular Updates:**
   - Dashboards may need updates as exporter evolves
   - Check for new metrics and add panels as needed

5. **Documentation:**
   - Add annotations to dashboards for important events
   - Document any custom modifications

## Support

For issues or questions:
- Check the main [README.md](../README.md) for exporter documentation
- Review [ENHANCEMENTS.md](../ENHANCEMENTS.md) for code improvements
- Check Prometheus and Grafana logs for errors
- Verify exporter is running and collecting metrics

## Version Compatibility

- **Grafana**: 9.0+ (tested with 9.x and 10.x)
- **Prometheus**: 2.x
- **Exporter**: All versions (v4, legacy, redfish modes)

## License

These dashboards are provided as examples and can be freely modified to suit your needs.

