"""Unit tests for storage-container Prometheus label logic (issue #10)."""

from storage_container_labels import format_storage_container_label


def apply_owned_metrics(owned_metrics):
    """Simulate the fixed label loop: each metric carries its cluster owner.

    Returns a dict of label -> last value, matching how Gauge.labels(...).set works.
    """
    series = {}
    for storage_container_cluster, metric in owned_metrics:
        _key, entity, value = metric.split(':')
        label = format_storage_container_label(storage_container_cluster, entity)
        series[label] = value
    return series


def apply_buggy_name_lookup(details, metrics):
    """Simulate the pre-fix label loop that looks up cluster by container name."""
    series = {}
    for metric in metrics:
        _key, entity, value = metric.split(':')
        matching = [
            d['parent_name'] for d in details if d['entity_name'] == entity
        ]
        cluster = matching[0] if matching else entity
        label = format_storage_container_label(cluster, entity)
        series[label] = value
    return series


def test_format_label_with_parent():
    assert format_storage_container_label('CLUSTER_A', 'SelfServiceContainer') == (
        'CLUSTER_A_SelfServiceContainer'
    )


def test_format_label_replaces_dots_and_hyphens():
    assert format_storage_container_label('cluster.a-b', 'my-container.name') == (
        'cluster_a_b_my_container_name'
    )


def test_format_label_falls_back_when_parent_missing():
    assert format_storage_container_label(None, 'SelfServiceContainer') == (
        'SelfServiceContainer_SelfServiceContainer'
    )
    assert format_storage_container_label('', 'SelfServiceContainer') == (
        'SelfServiceContainer_SelfServiceContainer'
    )


def test_duplicate_names_across_clusters_produce_distinct_series():
    owned = [
        ('CLUSTER_A', 'nutanix_clustermgmt_storage_container_stats_storage_usage_bytes:SelfServiceContainer:100'),
        ('CLUSTER_B', 'nutanix_clustermgmt_storage_container_stats_storage_usage_bytes:SelfServiceContainer:200'),
        ('CLUSTER_C', 'nutanix_clustermgmt_storage_container_stats_storage_usage_bytes:SelfServiceContainer:300'),
    ]
    series = apply_owned_metrics(owned)
    assert series == {
        'CLUSTER_A_SelfServiceContainer': '100',
        'CLUSTER_B_SelfServiceContainer': '200',
        'CLUSTER_C_SelfServiceContainer': '300',
    }


def test_buggy_lookup_collapses_duplicate_names():
    """Document the pre-fix behaviour: same name → one series, last value wins."""
    details = [
        {'entity_name': 'SelfServiceContainer', 'parent_name': 'CLUSTER_A'},
        {'entity_name': 'SelfServiceContainer', 'parent_name': 'CLUSTER_B'},
        {'entity_name': 'SelfServiceContainer', 'parent_name': 'CLUSTER_C'},
    ]
    metrics = [
        'nutanix_clustermgmt_storage_container_stats_storage_usage_bytes:SelfServiceContainer:100',
        'nutanix_clustermgmt_storage_container_stats_storage_usage_bytes:SelfServiceContainer:200',
        'nutanix_clustermgmt_storage_container_stats_storage_usage_bytes:SelfServiceContainer:300',
    ]
    series = apply_buggy_name_lookup(details, metrics)
    assert len(series) == 1
    assert 'CLUSTER_A_SelfServiceContainer' in series
    assert series['CLUSTER_A_SelfServiceContainer'] == '300'


def test_unique_names_unchanged():
    owned = [
        ('CLUSTER_A', 'nutanix_clustermgmt_storage_container_stats_storage_usage_bytes:UniqueA:10'),
        ('CLUSTER_B', 'nutanix_clustermgmt_storage_container_stats_storage_usage_bytes:UniqueB:20'),
    ]
    series = apply_owned_metrics(owned)
    assert series == {
        'CLUSTER_A_UniqueA': '10',
        'CLUSTER_B_UniqueB': '20',
    }


def test_result_independent_of_completion_order():
    """as_completed order must not change which value belongs to which cluster."""
    order_a = [
        ('CLUSTER_B', 'nutanix_clustermgmt_storage_container_stats_storage_usage_bytes:SelfServiceContainer:200'),
        ('CLUSTER_A', 'nutanix_clustermgmt_storage_container_stats_storage_usage_bytes:SelfServiceContainer:100'),
    ]
    order_b = list(reversed(order_a))
    assert apply_owned_metrics(order_a) == apply_owned_metrics(order_b)
    assert apply_owned_metrics(order_a) == {
        'CLUSTER_A_SelfServiceContainer': '100',
        'CLUSTER_B_SelfServiceContainer': '200',
    }
