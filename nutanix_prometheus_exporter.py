""" extracts metrics from Nutanix API and publishes them in 
    prometheus format on a web service.

    Args:
        prism: The IP or FQDN of Prism.
        username: The Prism user name.
        secure: boolean to indicate if certs should be verified.

    Returns:
        csv file.
"""

#todo: add concurrent processing for volume disk entities retrieval
#todo: replace tqdm stats collection with function
#todo: create function for stats creation where possible
#todo: make sure all response = api calls are done in try/except with proper exception handling
#todo: add code for handling API rate limit errors
#todo: add licensing
#todo: add lcm
#todo: add iam

#region #*IMPORT
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timezone, timedelta
import os
import traceback
import json
import importlib
import time
import re
import math
import socket
import ipaddress
import urllib3
import requests
import tqdm
import inflection
from humanfriendly import format_timespan
from prometheus_client import start_http_server, Gauge, Info

import ntnx_vmm_py_client
import ntnx_clustermgmt_py_client
import ntnx_networking_py_client
import ntnx_prism_py_client
import ntnx_files_py_client
import ntnx_objects_py_client
import ntnx_volumes_py_client
import ntnx_datapolicies_py_client
import ntnx_dataprotection_py_client
import ntnx_microseg_py_client
import ntnx_monitoring_py_client
#endregion #*IMPORT


#region #*GLOBAL VAR CONFIG
unique_pc_count_metrics = [
    "nutanix_count_cluster",
    "nutanix_count_subnet_overlay",
    "nutanix_count_vpc",
    "nutanix_count_subnet_vlan",
    "nutanix_count_subnet_external",
    "nutanix_count_subnet_vlan_basic",
    "nutanix_count_subnet_vlan_advanced",
    "nutanix_count_bgp_session",
    "nutanix_count_gateway",
    "nutanix_count_layer2_stretch",
    "nutanix_count_load_balancer_session",
    "nutanix_count_network_controller",
    "nutanix_count_routing_policy",
    "nutanix_count_traffic_mirror",
    "nutanix_count_uplink_bond",
    "nutanix_count_virtual_switch",
    "nutanix_count_vpn_connection",
    "nutanix_count_files_server",
    "nutanix_count_files_unified_namespace",
    "nutanix_count_objects_object_stores",
    "nutanix_count_protection_policy",
    "nutanix_count_protection_policy_schedule",
    "nutanix_count_protection_policy_schedule_crash_consistent",
    "nutanix_count_protection_policy_schedule_app_consistent",
    "nutanix_count_protection_policy_schedule_sync",
    "nutanix_count_protection_policy_schedule_nearsync",
    "nutanix_count_protection_policy_schedule_async",
    "nutanix_count_category",
    "nutanix_count_category_system",
    "nutanix_count_category_user",
    "nutanix_count_category_internal",
    "nutanix_count_category_key",
    "nutanix_count_dr_protected_entities_sync",
    "nutanix_count_dr_protected_entities_nearsync",
    "nutanix_count_dr_protected_entities_async",
    "nutanix_count_dr_protected_entities_status_in_sync",
    "nutanix_count_dr_protected_entities_status_syncing",
    "nutanix_count_dr_protected_entities_status_out_of_sync",
    "nutanix_count_dr_recovery_points",
    "nutanix_count_dr_recovery_points_vm",
    "nutanix_count_dr_recovery_points_vg",
    "nutanix_count_dr_recovery_points_crash_consistent",
    "nutanix_count_dr_recovery_points_application_consistent",
    "nutanix_count_microseg_network_security_policy",
    "nutanix_count_microseg_network_security_policy_vlan",
    "nutanix_count_microseg_network_security_policy_vpc",
    "nutanix_count_microseg_network_security_policy_save",
    "nutanix_count_microseg_network_security_policy_monitor",
    "nutanix_count_microseg_network_security_policy_enforce",
    "nutanix_count_microseg_network_security_policy_quarantine",
    "nutanix_count_microseg_network_security_policy_isolation",
    "nutanix_count_microseg_network_security_policy_application",
    "nutanix_count_microseg_address_group",
    "nutanix_count_microseg_service_group",
    "nutanix_count_task",
    "nutanix_count_task_queued",
    "nutanix_count_task_running",
    "nutanix_count_task_canceling",
    "nutanix_count_task_succeeded",
    "nutanix_count_task_failed",
    "nutanix_count_task_canceled",
    "nutanix_count_task_suspended",
    "nutanix_count_monitoring_alert",
    "nutanix_count_monitoring_alert_resolved",
    "nutanix_count_monitoring_alert_not_resolved",
    "nutanix_count_monitoring_alert_acknowledged",
    "nutanix_count_monitoring_alert_not_acknowledged",
    "nutanix_count_monitoring_alert_info",
    "nutanix_count_monitoring_alert_warning",
    "nutanix_count_monitoring_alert_critical",
    "nutanix_count_monitoring_alert_info_not_resolved",
    "nutanix_count_monitoring_alert_warning_not_resolved",
    "nutanix_count_monitoring_alert_critical_not_resolved",
    "nutanix_count_monitoring_alert_info_not_acknowledged",
    "nutanix_count_monitoring_alert_warning_not_acknowledged",
    "nutanix_count_monitoring_alert_critical_not_acknowledged",
    "nutanix_count_monitoring_audit",
    "nutanix_count_monitoring_audit_succeeded",
    "nutanix_count_monitoring_audit_failed",
    "nutanix_count_monitoring_audit_aborted",
]
shared_pc_cluster_count_metrics = [
    "nutanix_count_vg",
    "nutanix_count_vg_shared",
    "nutanix_count_vg_not_shared",
    "nutanix_count_vm",
    "nutanix_count_vm_on",
    "nutanix_count_vm_off",
    "nutanix_count_vm_boot_legacy",
    "nutanix_count_vm_boot_uefi",
    "nutanix_count_vm_gpus",
    "nutanix_count_vm_unprotected",
    "nutanix_count_vm_pd_protected",
    "nutanix_count_vm_rule_protected",
    "nutanix_count_vcpu",
    "nutanix_count_vram_mib",
    "nutanix_count_vdisk",
    "nutanix_count_vdisk_ide",
    "nutanix_count_vdisk_sata",
    "nutanix_count_vdisk_scsi",
    "nutanix_count_vnic",
    "nutanix_count_node",
    "nutanix_count_storage_container",
    "nutanix_count_storage_container_encrypted",
    "nutanix_count_storage_container_rf1",
    "nutanix_count_storage_container_rf2",
    "nutanix_count_storage_container_rf3",
    "nutanix_count_ngt_installed",
    "nutanix_count_ngt_enabled",
    "nutanix_count_ngt_reachable",
    "nutanix_count_ngt_vss_snapshot_capable",
    "nutanix_count_subnet"
]
shared_cluster_host_count_metrics = [
    "nutanix_count_vm",
    "nutanix_count_vm_on",
    "nutanix_count_vm_off",
    "nutanix_count_vm_boot_legacy",
    "nutanix_count_vm_boot_uefi",
    "nutanix_count_vm_gpus",
    "nutanix_count_vm_unprotected",
    "nutanix_count_vm_pd_protected",
    "nutanix_count_vm_rule_protected",
    "nutanix_count_vcpu",
    "nutanix_count_vram_mib",
    "nutanix_count_vdisk",
    "nutanix_count_vdisk_ide",
    "nutanix_count_vdisk_sata",
    "nutanix_count_vdisk_scsi",
    "nutanix_count_vnic",
    "nutanix_count_disk",
    "nutanix_count_disk_ssd_pcie",
    "nutanix_count_disk_ssd_sata",
    "nutanix_count_disk_das_sata",
    "nutanix_count_disk_ssd_mem_nvme",
    "nutanix_count_ngt_installed",
    "nutanix_count_ngt_enabled",
    "nutanix_count_ngt_reachable",
    "nutanix_count_ngt_vss_snapshot_capable",
]
unique_cluster_count_metrics = [
    "nutanix_count_vg",
    "nutanix_count_vg_shared",
    "nutanix_count_vg_not_shared",
    "nutanix_count_node",
    "nutanix_count_storage_container",
    "nutanix_count_storage_container_encrypted",
    "nutanix_count_storage_container_rf1",
    "nutanix_count_storage_container_rf2",
    "nutanix_count_storage_container_rf3",
    "nutanix_count_subnet"
]
#endregion


#region #*CLASS
class PrintColors:
    """ used in print statements for colored output
    """
    OK = '\033[92m' #GREEN
    SUCCESS = '\033[96m' #CYAN
    DATA = '\033[097m' #WHITE
    WARNING = '\033[93m' #YELLOW
    FAIL = '\033[91m' #RED
    STEP = '\033[95m' #PURPLE
    RESET = '\033[0m' #RESET COLOR


class NutanixMetrics:
    """
    Representation of Prometheus metrics and loop to fetch and transform
    application metrics into Prometheus metrics.
    """


    def __init__(self,
                 app_port=9440, polling_interval_seconds=30, api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,
                 unique_pc_count_metrics=unique_pc_count_metrics,shared_pc_cluster_count_metrics=shared_pc_cluster_count_metrics,shared_cluster_host_count_metrics=shared_cluster_host_count_metrics,unique_cluster_count_metrics=unique_cluster_count_metrics,
                 prism='127.0.0.1', user='admin', pwd='Nutanix/4u', prism_secure=False,
                 cluster_metrics=True, hosts_metrics=True, storage_containers_metrics=True,disks_metrics=False, networking_metrics=False, files_metrics=False, object_metrics=False, volumes_metrics=False, ncm_ssp_metrics=False, prism_central_metrics = False, microseg_metrics = False,
                 vm_list='',
                 show_stats_only=False):
        #region self.
        self.app_port = app_port
        self.polling_interval_seconds = polling_interval_seconds
        self.api_requests_timeout_seconds = api_requests_timeout_seconds
        self.api_requests_retries = api_requests_retries
        self.api_sleep_seconds_between_retries = api_sleep_seconds_between_retries
        self.prism = prism
        self.user = user
        self.pwd = pwd
        self.prism_secure = prism_secure
        self.cluster_metrics = cluster_metrics
        self.hosts_metrics = hosts_metrics
        self.storage_containers_metrics = storage_containers_metrics
        self.disks_metrics = disks_metrics
        self.networking_metrics = networking_metrics
        self.files_metrics = files_metrics
        self.object_metrics = object_metrics
        self.volumes_metrics = volumes_metrics
        self.ncm_ssp_metrics = ncm_ssp_metrics
        self.vm_list = vm_list
        self.show_stats_only = show_stats_only
        self.prism_central_metrics = prism_central_metrics
        self.microseg_metrics = microseg_metrics
        self.unique_pc_count_metrics = unique_pc_count_metrics
        self.shared_pc_cluster_count_metrics = shared_pc_cluster_count_metrics
        self.shared_cluster_host_count_metrics = shared_cluster_host_count_metrics
        self.unique_cluster_count_metrics = unique_cluster_count_metrics
        #endregion self.

        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [INFO] Initializing v4 API metrics...{PrintColors.RESET}")
        stats_count = 0
        complete_stats_list = {}
        complete_stats_list.update({'info': {}})

        #region #?prism_central
        if self.prism_central_metrics:
            stats_count += len(self.shared_pc_cluster_count_metrics)
            complete_stats_list.update({'prism_central': []})
            complete_stats_list['prism_central'].append(self.shared_pc_cluster_count_metrics)
            stats_count += len(self.unique_pc_count_metrics)
            complete_stats_list['prism_central'].append(unique_pc_count_metrics)
            for key_string in self.unique_pc_count_metrics:
                setattr(self, key_string, Gauge(key_string, key_string, ['entity']))
        if self.prism_central_metrics and not self.cluster_metrics:
            for key_string in self.shared_pc_cluster_count_metrics:
                setattr(self, key_string, Gauge(key_string, key_string, ['entity']))
        #endregion #?prism_central

        #region #?clusters
        if self.cluster_metrics:
            #region stats
            #* processing classes in clustermgmt
            ntnx_clustermgmt_py_client_stats = ['HostStats','ClusterStats']
            complete_stats_list.update({'clustermgmt': {}})
            if self.storage_containers_metrics:
                ntnx_clustermgmt_py_client_stats.append('StorageContainerStats')
            if self.disks_metrics:
                ntnx_clustermgmt_py_client_stats.append('DiskStats')
            for class_name in ntnx_clustermgmt_py_client_stats:
                class_ = getattr(ntnx_clustermgmt_py_client, class_name)
                stats = class_()
                stats_metrics = [stat[len(f"_{class_name}__"):] for stat in vars(stats) if stat.startswith(f"_{class_name}__")]
                instance_type = inflection.underscore(class_name.replace("Stats", ""))
                class_snake_case_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
                for stat in stats_metrics:
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_clustermgmt_{class_snake_case_name}_{stat}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    setattr(self, key_string, Gauge(key_string, key_string, [instance_type]))
                    #print(f"Adding {instance_type}:{key_string}")
                stats_count += len(stats_metrics)
                complete_stats_list['clustermgmt'].update({instance_type: []})
                complete_stats_list['clustermgmt'][instance_type].append(stats_metrics)
                #print(f"{class_name}: {stats_metrics}")
            #endregion stats

            #region count
            ntnx_clustermgmt_instance_type_count = ['host','cluster']
            stats_count += len(self.shared_cluster_host_count_metrics)
            for instance_type in ntnx_clustermgmt_instance_type_count:
                complete_stats_list['clustermgmt'][instance_type].append(self.shared_cluster_host_count_metrics)
            for key_string in self.shared_cluster_host_count_metrics:
                setattr(self, key_string, Gauge(key_string, key_string, ['entity']))
            stats_count += len(self.unique_cluster_count_metrics)
            complete_stats_list['clustermgmt']['cluster'].append(self.unique_cluster_count_metrics)
            for key_string in self.unique_cluster_count_metrics:
                setattr(self, key_string, Gauge(key_string, key_string, ['entity']))
            #endregion count

            #other misc info based metrics
            setattr(self, 'nutanix_cluster', Info('nutanix_cluster', 'Misc cluster information'))
            stats_count += 1
            complete_stats_list['info'].update({'nutanix_cluster': []})
        #endregion #?clusters

        #region #?networking
        if self.networking_metrics:
            #region stats
            #* processing classes in networking
            ntnx_networking_py_client_stats = ['Layer2StretchStats','LoadBalancerSessionStats','TrafficMirrorStats','VpcNsStats','VpnConnectionStats']
            complete_stats_list.update({'networking': {}})
            for class_name in ntnx_networking_py_client_stats:
                class_ = getattr(ntnx_networking_py_client, class_name)
                stats = class_()
                stats_metrics = [stat[len(f"_{class_name}__"):] for stat in vars(stats) if stat.startswith(f"_{class_name}__")]
                instance_type = inflection.underscore(class_name.replace("Stats", ""))
                class_snake_case_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
                for stat in stats_metrics:
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_networking_{class_snake_case_name}_{stat}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    setattr(self, key_string, Gauge(key_string, key_string, [instance_type]))
                    #print(f"Adding {instance_type}:{key_string}")
                stats_count += len(stats_metrics)
                complete_stats_list['networking'].update({instance_type: []})
                complete_stats_list['networking'][instance_type].append(stats_metrics)
                #print(f"{class_name}: {stats_metrics}")
            #endregion stats
        #endregion #?networking

        #region #?vmm
        if self.vm_list != '':
            #region stats
            #* processing classes in vmm
            ntnx_vmm_py_client_stats = ['AhvStatsVmStatsTuple','AhvStatsVmDiskStatsTuple','AhvStatsVmNicStatsTuple']
            complete_stats_list.update({'vmm': {}})
            exclude_list = ['timestamp','_reserved','_object_type','_unknown_fields','cluster','hypervisor_type']
            for class_name in ntnx_vmm_py_client_stats:
                class_ = getattr(ntnx_vmm_py_client, class_name)
                stats = class_()
                stats_dictionary = stats.to_dict()
                vmm_stats = []
                for stat in stats_dictionary:
                    if stat not in exclude_list:
                        vmm_stats.append(stat)
                instance_type_name = class_name.replace("StatsTuple", "")
                class_snake_case_name = re.sub(r'(?<!^)(?=[A-Z])', '_', instance_type_name).lower()
                instance_type_name = instance_type_name.replace("AhvStats", "")
                instance_type = inflection.underscore(instance_type_name)
                #print(instance_type)
                for stat in vmm_stats:
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_vmm_{class_snake_case_name}_{stat}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    setattr(self, key_string, Gauge(key_string, key_string, [instance_type]))
                    #print(f"Adding {instance_type}:{key_string}")
                stats_count += len(vmm_stats)
                complete_stats_list['vmm'].update({instance_type: []})
                complete_stats_list['vmm'][instance_type].append(vmm_stats)
                #print(f"{class_name}: {vmm_stats}")
            #endregion stats
        #endregion #?vmm

        #region #?files
        if self.files_metrics:
            #region stats
            #* processing classes in files
            ntnx_files_py_client_stats = ['AntivirusStats','FileServerStats','MountTargetStats']
            complete_stats_list.update({'files': {}})
            for class_name in ntnx_files_py_client_stats:
                class_ = getattr(ntnx_files_py_client, class_name)
                stats = class_()
                stats_metrics = [stat[len(f"_{class_name}__"):] for stat in vars(stats) if stat.startswith(f"_{class_name}__")]
                instance_type = inflection.underscore(class_name.replace("Stats", ""))
                class_snake_case_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
                for stat in stats_metrics:
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_files_{class_snake_case_name}_{stat}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    setattr(self, key_string, Gauge(key_string, key_string, [instance_type]))
                    #print(f"Adding {instance_type}:{key_string}")
                stats_count += len(stats_metrics)
                complete_stats_list['files'].update({instance_type: []})
                complete_stats_list['files'][instance_type].append(stats_metrics)
                #print(f"{class_name}: {stats_metrics}")
            #endregion stats
        #endregion #?files

        #region #?object
        if self.object_metrics:
            #region stats
            #* processing classes in objects
            ntnx_objects_py_client_stats = ['ObjectstoreStats']
            complete_stats_list.update({'object': {}})
            for class_name in ntnx_objects_py_client_stats:
                class_ = getattr(ntnx_objects_py_client, class_name)
                stats = class_()
                stats_metrics = [stat[len(f"_{class_name}__"):] for stat in vars(stats) if stat.startswith(f"_{class_name}__")]
                instance_type = inflection.underscore(class_name.replace("Stats", ""))
                class_snake_case_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
                for stat in stats_metrics:
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_objects_{class_snake_case_name}_{stat}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    setattr(self, key_string, Gauge(key_string, key_string, [instance_type]))
                    #print(f"Adding {instance_type}:{key_string}")
                stats_count += len(stats_metrics)
                complete_stats_list['object'].update({instance_type: []})
                complete_stats_list['object'][instance_type].append(stats_metrics)
                #print(f"{class_name}: {stats_metrics}")
            #endregion stats
        #endregion #?object

        #region #?volumes
        if self.volumes_metrics:
            #region stats
            #* processing classes in volumes
            ntnx_volumes_py_client_stats = ['VolumeDiskStats','VolumeGroupStats']
            complete_stats_list.update({'volumes': {}})
            for class_name in ntnx_volumes_py_client_stats:
                class_ = getattr(ntnx_volumes_py_client, class_name)
                stats = class_()
                stats_metrics = [stat[len(f"_{class_name}__"):] for stat in vars(stats) if stat.startswith(f"_{class_name}__")]
                instance_type = inflection.underscore(class_name.replace("Stats", ""))
                class_snake_case_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
                for stat in stats_metrics:
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_volumes_{class_snake_case_name}_{stat}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    setattr(self, key_string, Gauge(key_string, key_string, [instance_type]))
                    #print(f"Adding {instance_type}:{key_string}")
                stats_count += len(stats_metrics)
                complete_stats_list['volumes'].update({instance_type: []})
                complete_stats_list['volumes'][instance_type].append(stats_metrics)
                #print(f"{class_name}: {stats_metrics}")
            #endregion stats
        #endregion #?volumes

        print(f"{PrintColors.DATA}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [DATA] Initialized {stats_count} metrics.{PrintColors.RESET}")
        #print(json.dumps(complete_stats_list, indent=4))

        #todo: add entity count metrics
        if self.show_stats_only is True:
            print(json.dumps(complete_stats_list, indent=4))
            exit(0)


    def run_metrics_loop(self):
        """Metrics fetching loop"""
        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Starting metrics loop {PrintColors.RESET}")
        while True:
            loop_start_time = datetime.now(timezone.utc)
            self.fetch()
            loop_end_time = datetime.now(timezone.utc)
            print(f"{PrintColors.STEP}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [STEP] Fetching all metrics took {format_timespan(loop_end_time - loop_start_time)}!{PrintColors.RESET}")
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Waiting for {self.polling_interval_seconds} seconds...{PrintColors.RESET}")
            time.sleep(self.polling_interval_seconds)


    def fetch(self):
        """
        Get metrics from application and refresh Prometheus metrics with
        new values.
        """

        #define entity per page quantity limit when fetching entities from the Nutanix v4 API
        limit=100

        #initialize variables
        cluster_list, host_list, storage_container_list, disk_list, subnet_list, layer2_stretch_list, load_balancer_sessions_list, traffic_mirrors_list, vpc_list, vpn_connection_list, vms_list, files_server_list, object_store_list, volume_group_list = ([] for i in range(14))


        #region #?prism_central
        if self.prism_central_metrics:
            try:
                ipaddress.ip_address(self.prism)
                try:
                    prism_central_hostname = socket.gethostbyaddr(self.prism)[0]
                except:
                    prism_central_hostname = self.prism
            except:
                prism_central_hostname = self.prism

            #region vg
            if self.volumes_metrics:
                volumes_client = v4_init_api_client(module='ntnx_volumes_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
                volume_group_list = v4_get_all_entities(module=ntnx_volumes_py_client,client=volumes_client,function='list_volume_groups',limit=limit,module_entity_api='VolumeGroupsApi')
                self.__dict__["nutanix_count_vg"].labels(entity=prism_central_hostname).set(len(volume_group_list))
                self.__dict__["nutanix_count_vg_shared"].labels(entity=prism_central_hostname).set(len([vg for vg in volume_group_list if vg.sharing_status == 'SHARED']))
                self.__dict__["nutanix_count_vg_not_shared"].labels(entity=prism_central_hostname).set(len([vg for vg in volume_group_list if vg.sharing_status == 'NOT_SHARED']))
            #endregion vg

            #region vm
            vmm_client = v4_init_api_client(module='ntnx_vmm_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
            vms_list = v4_get_all_entities(module=ntnx_vmm_py_client,client=vmm_client,function='list_vms',limit=limit,module_entity_api='VmApi')
            self.__dict__["nutanix_count_vm"].labels(entity=prism_central_hostname).set(len(vms_list))
            self.__dict__["nutanix_count_vm_on"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_list if vm.power_state == 'ON']))
            self.__dict__["nutanix_count_vm_off"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_list if vm.power_state == 'OFF']))
            self.__dict__["nutanix_count_vm_boot_legacy"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_list if vm.boot_config.__class__.__name__ == 'LegacyBoot']))
            self.__dict__["nutanix_count_vm_boot_uefi"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_list if vm.boot_config.__class__.__name__ == 'UefiBoot']))
            self.__dict__["nutanix_count_vm_gpus"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_list if vm.gpus]))
            self.__dict__["nutanix_count_vm_unprotected"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_list if vm.protection_type == 'UNPROTECTED']))
            self.__dict__["nutanix_count_vm_pd_protected"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_list if vm.protection_type == 'PD_PROTECTED']))
            self.__dict__["nutanix_count_vm_rule_protected"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_list if vm.protection_type == 'RULE_PROTECTED']))
            self.__dict__["nutanix_count_vcpu"].labels(entity=prism_central_hostname).set(sum([(vm.num_sockets * vm.num_cores_per_socket) for vm in vms_list]))
            self.__dict__["nutanix_count_vram_mib"].labels(entity=prism_central_hostname).set(sum([(vm.memory_size_bytes / 1048576) for vm in vms_list]))
            self.__dict__["nutanix_count_vdisk"].labels(entity=prism_central_hostname).set(sum(any(vdisk.backing_info.__class__.__name__ == 'VmDisk' for vdisk in vm.disks) for vm in vms_list if vm.disks))
            self.__dict__["nutanix_count_vdisk_ide"].labels(entity=prism_central_hostname).set(sum(any((vdisk.backing_info.__class__.__name__ == 'VmDisk' and vdisk.disk_address.bus_type == 'IDE') for vdisk in vm.disks) for vm in vms_list if vm.disks))
            self.__dict__["nutanix_count_vdisk_sata"].labels(entity=prism_central_hostname).set(sum(any((vdisk.backing_info.__class__.__name__ == 'VmDisk' and vdisk.disk_address.bus_type == 'SATA') for vdisk in vm.disks) for vm in vms_list if vm.disks))
            self.__dict__["nutanix_count_vdisk_scsi"].labels(entity=prism_central_hostname).set(sum(any((vdisk.backing_info.__class__.__name__ == 'VmDisk' and vdisk.disk_address.bus_type == 'SCSI') for vdisk in vm.disks) for vm in vms_list if vm.disks))
            self.__dict__["nutanix_count_vnic"].labels(entity=prism_central_hostname).set(sum([len(vm.nics) for vm in vms_list if vm.nics]))
            vms_with_ngt = [vm for vm in vms_list if vm.guest_tools]
            self.__dict__["nutanix_count_ngt_installed"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_with_ngt if vm.guest_tools.is_installed is True]))
            self.__dict__["nutanix_count_ngt_enabled"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_with_ngt if vm.guest_tools.is_enabled is True]))
            self.__dict__["nutanix_count_ngt_reachable"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_with_ngt if vm.guest_tools.is_reachable is True]))
            self.__dict__["nutanix_count_ngt_vss_snapshot_capable"].labels(entity=prism_central_hostname).set(len([vm for vm in vms_with_ngt if vm.guest_tools.is_vss_snapshot_capable is True])),
            #endregion vm

            #region cluster
            clustermgmt_client = v4_init_api_client(module='ntnx_clustermgmt_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
            cluster_list = v4_get_all_entities(module=ntnx_clustermgmt_py_client,client=clustermgmt_client,function='list_clusters',limit=limit,module_entity_api='ClustersApi')
            self.__dict__["nutanix_count_cluster"].labels(entity=prism_central_hostname).set(len([cluster for cluster in cluster_list if 'PRISM_CENTRAL' not in cluster.config.cluster_function]))
            #endregion cluster

            #region host
            clustermgmt_client = v4_init_api_client(module='ntnx_clustermgmt_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
            host_list = v4_get_all_entities(module=ntnx_clustermgmt_py_client,client=clustermgmt_client,function='list_hosts',limit=limit,module_entity_api='ClustersApi')
            self.__dict__["nutanix_count_node"].labels(entity=prism_central_hostname).set(len(host_list))
            #endregion host

            #region storage_container
            clustermgmt_client = v4_init_api_client(module='ntnx_clustermgmt_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
            storage_container_list = v4_get_all_entities(module=ntnx_clustermgmt_py_client,client=clustermgmt_client,function='list_storage_containers',limit=limit,module_entity_api='StorageContainersApi')
            self.__dict__["nutanix_count_storage_container"].labels(entity=prism_central_hostname).set(len(storage_container_list))
            self.__dict__["nutanix_count_storage_container_encrypted"].labels(entity=prism_central_hostname).set(len([storage_container for storage_container in storage_container_list if storage_container.is_encrypted is True]))
            self.__dict__["nutanix_count_storage_container_rf1"].labels(entity=prism_central_hostname).set(len([storage_container for storage_container in storage_container_list if storage_container.replication_factor == 1]))
            self.__dict__["nutanix_count_storage_container_rf2"].labels(entity=prism_central_hostname).set(len([storage_container for storage_container in storage_container_list if storage_container.replication_factor == 2]))
            self.__dict__["nutanix_count_storage_container_rf3"].labels(entity=prism_central_hostname).set(len([storage_container for storage_container in storage_container_list if storage_container.replication_factor == 3]))
            #endregion storage_container

            #region networking
            networking_client = v4_init_api_client(module='ntnx_networking_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)

            subnet_list = v4_get_all_subnets(client=networking_client,limit=limit)
            self.__dict__["nutanix_count_subnet"].labels(entity=prism_central_hostname).set(len(subnet_list))
            self.__dict__["nutanix_count_subnet_vlan"].labels(entity=prism_central_hostname).set(len([subnet for subnet in subnet_list if subnet.subnet_type == 'VLAN']))
            self.__dict__["nutanix_count_subnet_vlan_basic"].labels(entity=prism_central_hostname).set(len([subnet for subnet in subnet_list if (subnet.is_advanced_networking is False) and (subnet.subnet_type == 'VLAN')]))
            self.__dict__["nutanix_count_subnet_vlan_advanced"].labels(entity=prism_central_hostname).set(len([subnet for subnet in subnet_list if (subnet.is_advanced_networking is True) and (subnet.subnet_type == 'VLAN')]))
            self.__dict__["nutanix_count_subnet_overlay"].labels(entity=prism_central_hostname).set(len([subnet for subnet in subnet_list if subnet.subnet_type == 'OVERLAY']))
            self.__dict__["nutanix_count_subnet_external"].labels(entity=prism_central_hostname).set(len([subnet for subnet in subnet_list if subnet.is_external is True]))

            if self.networking_metrics:
                vpc_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_vpcs',limit=limit,module_entity_api='VpcsApi')
                self.__dict__["nutanix_count_vpc"].labels(entity=prism_central_hostname).set(len(vpc_list))

                bgp_session_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_bgp_sessions',limit=limit,module_entity_api='BgpSessionsApi')
                self.__dict__["nutanix_count_bgp_session"].labels(entity=prism_central_hostname).set(len(bgp_session_list))

                gateway_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_gateways',limit=limit,module_entity_api='GatewaysApi')
                self.__dict__["nutanix_count_gateway"].labels(entity=prism_central_hostname).set(len(gateway_list))

                layer2_stretch_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_layer2_stretches',limit=limit,module_entity_api='Layer2StretchesApi')
                self.__dict__["nutanix_count_layer2_stretch"].labels(entity=prism_central_hostname).set(len(layer2_stretch_list))

                load_balancer_sessions_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_load_balancer_sessions',limit=limit,module_entity_api='LoadBalancerSessionsApi')
                self.__dict__["nutanix_count_load_balancer_session"].labels(entity=prism_central_hostname).set(len(load_balancer_sessions_list))

                traffic_mirrors_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_traffic_mirrors',limit=limit,module_entity_api='TrafficMirrorsApi')
                self.__dict__["nutanix_count_traffic_mirror"].labels(entity=prism_central_hostname).set(len(traffic_mirrors_list))

                network_controller_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_network_controllers',limit=limit,module_entity_api='NetworkControllersApi')
                self.__dict__["nutanix_count_network_controller"].labels(entity=prism_central_hostname).set(len(network_controller_list))

                routing_policy_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_routing_policies',limit=limit,module_entity_api='RoutingPoliciesApi')
                self.__dict__["nutanix_count_routing_policy"].labels(entity=prism_central_hostname).set(len(routing_policy_list))

                uplink_bond_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_uplink_bonds',limit=limit,module_entity_api='UplinkBondsApi')
                self.__dict__["nutanix_count_uplink_bond"].labels(entity=prism_central_hostname).set(len(uplink_bond_list))

                virtual_switch_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_virtual_switches',limit=limit,module_entity_api='VirtualSwitchesApi')
                self.__dict__["nutanix_count_virtual_switch"].labels(entity=prism_central_hostname).set(len(virtual_switch_list))

                vpn_connection_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_vpn_connections',limit=limit,module_entity_api='VpnConnectionsApi')
                self.__dict__["nutanix_count_vpn_connection"].labels(entity=prism_central_hostname).set(len(vpn_connection_list))
            #endregion networking

            #region files
            if self.files_metrics:
                files_client = v4_init_api_client(module='ntnx_files_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)

                files_server_list = v4_get_all_entities(module=ntnx_files_py_client,client=files_client,function='list_file_servers',limit=limit,module_entity_api='FileServersApi')
                self.__dict__["nutanix_count_files_server"].labels(entity=prism_central_hostname).set(len(files_server_list))

                unified_namespace_list = v4_get_all_entities(module=ntnx_files_py_client,client=files_client,function='list_unified_namespaces',limit=limit,module_entity_api='UnifiedNamespacesApi')
                self.__dict__["nutanix_count_files_unified_namespace"].labels(entity=prism_central_hostname).set(len(unified_namespace_list))
            #endregion files

            #region object
            if self.object_metrics:
                objects_client = v4_init_api_client(module='ntnx_objects_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
                object_store_list = v4_get_all_entities(module=ntnx_objects_py_client,client=objects_client,function='list_objectstores',limit=limit,module_entity_api='ObjectStoresApi')
                self.__dict__["nutanix_count_objects_object_stores"].labels(entity=prism_central_hostname).set(len(object_store_list))
            #endregion object

            #region categories
            prism_client = v4_init_api_client(module='ntnx_prism_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
            category_list = v4_get_all_entities(module=ntnx_prism_py_client,client=prism_client,function='list_categories',limit=limit,module_entity_api='CategoriesApi',select='extId,key,type')
            self.__dict__["nutanix_count_category"].labels(entity=prism_central_hostname).set(len(category_list))
            self.__dict__["nutanix_count_category_system"].labels(entity=prism_central_hostname).set(len([category for category in category_list if category.type == 'SYSTEM']))
            self.__dict__["nutanix_count_category_user"].labels(entity=prism_central_hostname).set(len([category for category in category_list if category.type == 'USER']))
            self.__dict__["nutanix_count_category_internal"].labels(entity=prism_central_hostname).set(len([category for category in category_list if category.type == 'INTERNAL']))
            self.__dict__["nutanix_count_category_key"].labels(entity=prism_central_hostname).set(len((Counter(category.key for category in category_list).keys())))
            #endregion categories

            #region tasks
            task_list = v4_get_all_entities(module=ntnx_prism_py_client,client=prism_client,function='list_tasks',limit=limit,module_entity_api='TasksApi',select='status')
            self.__dict__["nutanix_count_task"].labels(entity=prism_central_hostname).set(len(task_list))
            self.__dict__["nutanix_count_task_queued"].labels(entity=prism_central_hostname).set(len([task for task in task_list if task.status == 'QUEUED']))
            self.__dict__["nutanix_count_task_running"].labels(entity=prism_central_hostname).set(len([task for task in task_list if task.status == 'RUNNING']))
            self.__dict__["nutanix_count_task_canceling"].labels(entity=prism_central_hostname).set(len([task for task in task_list if task.status == 'CANCELING']))
            self.__dict__["nutanix_count_task_succeeded"].labels(entity=prism_central_hostname).set(len([task for task in task_list if task.status == 'SUCCEEDED']))
            self.__dict__["nutanix_count_task_failed"].labels(entity=prism_central_hostname).set(len([task for task in task_list if task.status == 'FAILED']))
            self.__dict__["nutanix_count_task_canceled"].labels(entity=prism_central_hostname).set(len([task for task in task_list if task.status == 'CANCELED']))
            self.__dict__["nutanix_count_task_suspended"].labels(entity=prism_central_hostname).set(len([task for task in task_list if task.status == 'SUSPENDED']))
            #endregion tasks

            #region monitoring
            monitoring_client = v4_init_api_client(module='ntnx_monitoring_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)

            #region alert
            alert_list = v4_get_all_entities(module=ntnx_monitoring_py_client,client=monitoring_client,function='list_alerts',limit=limit,module_entity_api='AlertsApi',select='isResolved,isAcknowledged,severity')
            self.__dict__["nutanix_count_monitoring_alert"].labels(entity=prism_central_hostname).set(len(alert_list))
            self.__dict__["nutanix_count_monitoring_alert_resolved"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if alert.is_resolved is True]))
            self.__dict__["nutanix_count_monitoring_alert_not_resolved"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if alert.is_resolved is not True]))
            self.__dict__["nutanix_count_monitoring_alert_acknowledged"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if alert.is_acknowledged is True]))
            self.__dict__["nutanix_count_monitoring_alert_not_acknowledged"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if alert.is_acknowledged is not True]))
            self.__dict__["nutanix_count_monitoring_alert_info"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if alert.severity == 'INFO']))
            self.__dict__["nutanix_count_monitoring_alert_warning"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if alert.severity == 'WARNING']))
            self.__dict__["nutanix_count_monitoring_alert_critical"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if alert.severity == 'CRITICAL']))
            self.__dict__["nutanix_count_monitoring_alert_info_not_resolved"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if (alert.severity == 'INFO' and alert.is_resolved is not True)]))
            self.__dict__["nutanix_count_monitoring_alert_warning_not_resolved"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if (alert.severity == 'WARNING' and alert.is_resolved is not True)]))
            self.__dict__["nutanix_count_monitoring_alert_critical_not_resolved"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if (alert.severity == 'CRITICAL' and alert.is_resolved is not True)]))
            self.__dict__["nutanix_count_monitoring_alert_info_not_acknowledged"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if (alert.severity == 'INFO' and alert.is_acknowledged is not True)]))
            self.__dict__["nutanix_count_monitoring_alert_warning_not_acknowledged"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if (alert.severity == 'WARNING' and alert.is_acknowledged is not True)]))
            self.__dict__["nutanix_count_monitoring_alert_critical_not_acknowledged"].labels(entity=prism_central_hostname).set(len([alert for alert in alert_list if (alert.severity == 'CRITICAL' and alert.is_acknowledged is not True)]))
            #endregion alert

            #region audit
            #! too slow to retrieve and causing rate limit issues
            """ audit_list = v4_get_all_entities(module=ntnx_monitoring_py_client,client=monitoring_client,function='list_audits',limit=limit,module_entity_api='AuditsApi',select='status')
            self.__dict__["nutanix_count_monitoring_audit"].labels(entity=prism_central_hostname).set(len(audit_list))
            self.__dict__["nutanix_count_monitoring_audit_succeeded"].labels(entity=prism_central_hostname).set(len([audit for audit in audit_list if audit.status == 'SUCEEDED']))
            self.__dict__["nutanix_count_monitoring_audit_failed"].labels(entity=prism_central_hostname).set(len([audit for audit in audit_list if audit.status == 'FAILED']))
            self.__dict__["nutanix_count_monitoring_audit_aborted"].labels(entity=prism_central_hostname).set(len([audit for audit in audit_list if audit.status == 'ABORTED'])) """
            #endregion audit

            #endregion monitoring

            #region protection policies
            datapolicies_client = v4_init_api_client(module='ntnx_datapolicies_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
            protection_policy_list = v4_get_all_entities(module=ntnx_datapolicies_py_client,client=datapolicies_client,function='list_protection_policies',limit=limit,module_entity_api='ProtectionPoliciesApi')
            self.__dict__["nutanix_count_protection_policy"].labels(entity=prism_central_hostname).set(len(protection_policy_list))
            #! from now on we're dividing by 2 because in the API, a replication configuration between 2 locations is in fact a single configuration created by the user
            self.__dict__["nutanix_count_protection_policy_schedule"].labels(entity=prism_central_hostname).set(sum([math.ceil(len(protection_policy.replication_configurations)/2) for protection_policy in protection_policy_list]))
            self.__dict__["nutanix_count_protection_policy_schedule_crash_consistent"].labels(entity=prism_central_hostname).set(sum([math.ceil(len([configuration.schedule for configuration in protection_policy.replication_configurations if configuration.schedule.recovery_point_type == 'CRASH_CONSISTENT'])/2) for protection_policy in protection_policy_list]))
            self.__dict__["nutanix_count_protection_policy_schedule_app_consistent"].labels(entity=prism_central_hostname).set(sum([math.ceil(len([configuration.schedule for configuration in protection_policy.replication_configurations if configuration.schedule.recovery_point_type == 'APPLICATION_CONSISTENT'])/2) for protection_policy in protection_policy_list]))
            #? sync is where RPO = 0
            self.__dict__["nutanix_count_protection_policy_schedule_sync"].labels(entity=prism_central_hostname).set(sum([math.ceil(len([configuration.schedule for configuration in protection_policy.replication_configurations if configuration.schedule.recovery_point_objective_time_seconds == 0])/2) for protection_policy in protection_policy_list]))
            #? nearsync is where RPO > 0 but <= 900
            self.__dict__["nutanix_count_protection_policy_schedule_nearsync"].labels(entity=prism_central_hostname).set(sum([math.ceil(len([configuration.schedule for configuration in protection_policy.replication_configurations if (configuration.schedule.recovery_point_objective_time_seconds > 0) and (configuration.schedule.recovery_point_objective_time_seconds <= 900)])/2) for protection_policy in protection_policy_list]))
            #? sync is where RPO > 900
            self.__dict__["nutanix_count_protection_policy_schedule_async"].labels(entity=prism_central_hostname).set(sum([math.ceil(len([configuration.schedule for configuration in protection_policy.replication_configurations if configuration.schedule.recovery_point_objective_time_seconds > 900])/2) for protection_policy in protection_policy_list]))

            protection_policy_sync_ext_id_list = [protection_policy.ext_id for protection_policy in protection_policy_list if [configuration.schedule for configuration in protection_policy.replication_configurations if configuration.schedule.recovery_point_objective_time_seconds == 0]]
            protection_policy_nearsync_ext_id_list = [protection_policy.ext_id for protection_policy in protection_policy_list if [configuration.schedule for configuration in protection_policy.replication_configurations if configuration.schedule.recovery_point_objective_time_seconds > 0 and configuration.schedule.recovery_point_objective_time_seconds <= 900]]
            protection_policy_async_ext_id_list = [protection_policy.ext_id for protection_policy in protection_policy_list if [configuration.schedule for configuration in protection_policy.replication_configurations if configuration.schedule.recovery_point_objective_time_seconds > 900]]
            count_of_protected_vms_per_policy_ext_id = Counter([vm.protection_policy_state.policy.ext_id for vm in vms_list if vm.protection_policy_state])
            self.__dict__["nutanix_count_dr_protected_entities_sync"].labels(entity=prism_central_hostname).set(sum([count_of_protected_vms_per_policy_ext_id[ext_id] for ext_id in protection_policy_sync_ext_id_list]))
            self.__dict__["nutanix_count_dr_protected_entities_nearsync"].labels(entity=prism_central_hostname).set(sum([count_of_protected_vms_per_policy_ext_id[ext_id] for ext_id in protection_policy_nearsync_ext_id_list]))
            self.__dict__["nutanix_count_dr_protected_entities_async"].labels(entity=prism_central_hostname).set(sum([count_of_protected_vms_per_policy_ext_id[ext_id] for ext_id in protection_policy_async_ext_id_list]))
            #endregion protection policies

            #region data protection
            #todo: what about vgs?
            nutanix_dr_protected_vm_list = [vm for vm in vms_list if vm.protection_policy_state]
            dataprotection_client = v4_init_api_client(module='ntnx_dataprotection_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
            dataprotection_api = ntnx_dataprotection_py_client.ProtectedResourcesApi(api_client=dataprotection_client)
            entity_list=[]
            error_list=[]
            if len(nutanix_dr_protected_vm_list) >0:
                with tqdm.tqdm(total=len(nutanix_dr_protected_vm_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching protected resources state") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                dataprotection_api.get_protected_resource_by_id,
                                extId=entity.ext_id
                            ) for entity in nutanix_dr_protected_vm_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if hasattr(entities, 'data'):
                                    if isinstance(entities.data, Iterable):
                                        entity_list.extend(entities.data)
                                    else:
                                        entity_list.append(entities.data)
                            except ntnx_dataprotection_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                                    #raise(e.status)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                protected_resource_list = entity_list
                #print([protected_resource.replication_states for protected_resource in protected_resource_list])
                self.__dict__["nutanix_count_dr_protected_entities_status_in_sync"].labels(entity=prism_central_hostname).set(sum([len([replication_state for replication_state in protected_resource.replication_states if replication_state.replication_status == 'IN_SYNC']) for protected_resource in protected_resource_list if protected_resource.replication_states]))
                self.__dict__["nutanix_count_dr_protected_entities_status_syncing"].labels(entity=prism_central_hostname).set(sum([len([replication_state for replication_state in protected_resource.replication_states if replication_state.replication_status == 'SYNCING']) for protected_resource in protected_resource_list if protected_resource.replication_states]))
                self.__dict__["nutanix_count_dr_protected_entities_status_out_of_sync"].labels(entity=prism_central_hostname).set(sum([len([replication_state for replication_state in protected_resource.replication_states if replication_state.replication_status == 'OUT_OF_SYNC']) for protected_resource in protected_resource_list if protected_resource.replication_states]))
            
            recovery_point_list = v4_get_all_entities(module=ntnx_dataprotection_py_client,client=dataprotection_client,function='list_recovery_points',limit=limit,module_entity_api='RecoveryPointsApi')
            self.__dict__["nutanix_count_dr_recovery_points"].labels(entity=prism_central_hostname).set(len(recovery_point_list))
            self.__dict__["nutanix_count_dr_recovery_points_vm"].labels(entity=prism_central_hostname).set(sum([len([vm_recovery_point for vm_recovery_point in recovery_point.vm_recovery_points]) for recovery_point in recovery_point_list if recovery_point.vm_recovery_points]))
            self.__dict__["nutanix_count_dr_recovery_points_vg"].labels(entity=prism_central_hostname).set(sum([len([vg_recovery_point for vg_recovery_point in recovery_point.volume_group_recovery_points]) for recovery_point in recovery_point_list if recovery_point.volume_group_recovery_points]))
            self.__dict__["nutanix_count_dr_recovery_points_crash_consistent"].labels(entity=prism_central_hostname).set(len([recovery_point for recovery_point in recovery_point_list if recovery_point.recovery_point_type == 'CRASH_CONSISTENT']))
            self.__dict__["nutanix_count_dr_recovery_points_application_consistent"].labels(entity=prism_central_hostname).set(len([recovery_point for recovery_point in recovery_point_list if recovery_point.recovery_point_type == 'APPLICATION_CONSISTENT']))
            #endregion data protection

            #region microseg
            if self.microseg_metrics:
                microseg_client = v4_init_api_client(module='ntnx_microseg_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)

                network_security_policy_list = v4_get_all_entities(module=ntnx_microseg_py_client,client=microseg_client,function='list_network_security_policies',limit=limit,module_entity_api='NetworkSecurityPoliciesApi')
                self.__dict__["nutanix_count_microseg_network_security_policy"].labels(entity=prism_central_hostname).set(len(network_security_policy_list))
                self.__dict__["nutanix_count_microseg_network_security_policy_vlan"].labels(entity=prism_central_hostname).set(len([policy for policy in network_security_policy_list if policy.scope in ['ALL_VLAN']]))
                self.__dict__["nutanix_count_microseg_network_security_policy_vpc"].labels(entity=prism_central_hostname).set(len([policy for policy in network_security_policy_list if policy.scope in ['ALL_VPC','VPC_LIST']]))
                self.__dict__["nutanix_count_microseg_network_security_policy_save"].labels(entity=prism_central_hostname).set(len([policy for policy in network_security_policy_list if policy.state == 'SAVE']))
                self.__dict__["nutanix_count_microseg_network_security_policy_monitor"].labels(entity=prism_central_hostname).set(len([policy for policy in network_security_policy_list if policy.state == 'MONITOR']))
                self.__dict__["nutanix_count_microseg_network_security_policy_enforce"].labels(entity=prism_central_hostname).set(len([policy for policy in network_security_policy_list if policy.state == 'ENFORCE']))
                self.__dict__["nutanix_count_microseg_network_security_policy_quarantine"].labels(entity=prism_central_hostname).set(len([policy for policy in network_security_policy_list if policy.type == 'QUARANTINE']))
                self.__dict__["nutanix_count_microseg_network_security_policy_isolation"].labels(entity=prism_central_hostname).set(len([policy for policy in network_security_policy_list if policy.type == 'ISOLATION']))
                self.__dict__["nutanix_count_microseg_network_security_policy_application"].labels(entity=prism_central_hostname).set(len([policy for policy in network_security_policy_list if policy.type == 'APPLICATION']))

                #! security policy rules can take minutes to retrieve if there are a lot of security policies
                """ entity_list=[]
                error_list=[]
                with tqdm.tqdm(total=len(network_security_policy_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching network security policy rules") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_all_entities,
                                module=ntnx_microseg_py_client,
                                client=microseg_client,
                                function='list_network_security_policy_rules',
                                limit=limit,
                                module_entity_api='NetworkSecurityPoliciesApi',
                                parent_entity_ext_id = entity.ext_id
                            ) for entity in network_security_policy_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if hasattr(entities, 'data'):
                                    if isinstance(entities.data, Iterable):
                                        entity_list.extend(entities.data)
                                    else:
                                        entity_list.append(entities.data)
                            except ntnx_dataprotection_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                                    #raise(e.status)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                network_security_policy_rule_list = entity_list
                self.__dict__["nutanix_count_microseg_network_security_policy_rule"].labels(entity=prism_central_hostname).set(len(network_security_policy_rule_list)) """
                
                address_group_list = v4_get_all_entities(module=ntnx_microseg_py_client,client=microseg_client,function='list_address_groups',limit=limit,module_entity_api='AddressGroupsApi')
                self.__dict__["nutanix_count_microseg_address_group"].labels(entity=prism_central_hostname).set(len(address_group_list))

                service_group_list = v4_get_all_entities(module=ntnx_microseg_py_client,client=microseg_client,function='list_service_groups',limit=limit,module_entity_api='ServiceGroupsApi')
                self.__dict__["nutanix_count_microseg_service_group"].labels(entity=prism_central_hostname).set(len(service_group_list))
            #endregion microseg

        #endregion #?prism_central


        #region #?clustermgmt
        #* initialize variable for API client configuration
        clustermgmt_client = v4_init_api_client(module='ntnx_clustermgmt_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)

        #region #?clusters
        if self.cluster_metrics:
            cluster_list = v4_get_all_entities(module=ntnx_clustermgmt_py_client,client=clustermgmt_client,function='list_clusters',limit=limit,module_entity_api='ClustersApi')

            #region stats
            #* get metrics for each cluster
            cluster_details_list = []
            metrics=[]
            error_list=[]
            for entity in cluster_list:
                if 'PRISM_CENTRAL' in entity.config.cluster_function:
                    continue
                entity_details = {
                    'entity_name': entity.name,
                    'entity_uuid': entity.ext_id,
                }
                cluster_details_list.append(entity_details)
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(cluster_details_list)} entities...{PrintColors.RESET}")
            with tqdm.tqdm(total=len(cluster_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching cluster metrics") as progress_bar:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(
                            v4_get_entity_stats,
                            client=clustermgmt_client,
                            module=ntnx_clustermgmt_py_client,
                            entity_api='ClustersApi',
                            function='get_cluster_stats',
                            entity=cluster,
                            metric_key_prefix='nutanix_clustermgmt_cluster_stats_',
                            sampling_interval=30,
                            stat_type='LAST'
                        ) for cluster in cluster_details_list]
                    for future in as_completed(futures):
                        try:
                            entities = future.result()
                            if isinstance(entities, Iterable):
                                metrics.extend(entities)
                            else:
                                metrics.append(entities)
                        except ntnx_clustermgmt_py_client.rest.ApiException as e:
                            error_data = json.loads(e.body)
                            for error in error_data['data']['error']:
                                #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                error_list.append(error_message)
                        except Exception as e:
                            print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                        finally:
                            progress_bar.update(1)
            for error in error_list:
                print(error)
            for metric in metrics:
                #print(metric)
                key, entity, value = metric.split(':')
                #print(f"key: {key}, entity: {entity}, value: {value}")
                self.__dict__[key].labels(cluster=entity).set(value)
            #endregion stats

            #region count

            #region vg
            if not volume_group_list:
                volumes_client = v4_init_api_client(module='ntnx_volumes_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
                volume_group_list = v4_get_all_entities(module=ntnx_volumes_py_client,client=volumes_client,function='list_volume_groups',limit=limit,module_entity_api='VolumeGroupsApi')
            for cluster in cluster_list:
                if 'PRISM_CENTRAL' not in cluster.config.cluster_function:
                    self.__dict__["nutanix_count_vg"].labels(entity=cluster.name).set(len([vg for vg in volume_group_list if vg.cluster_reference == cluster.ext_id]))
            #endregion vg

            #region vm
            if not vms_list:
                vmm_client = v4_init_api_client(module='ntnx_vmm_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
                vms_list = v4_get_all_entities(module=ntnx_vmm_py_client,client=vmm_client,function='list_vms',limit=limit,module_entity_api='VmApi')
            for cluster in cluster_list:
                if 'PRISM_CENTRAL' not in cluster.config.cluster_function:
                    cluster_vms_list= [vm for vm in vms_list if vm.cluster.ext_id == cluster.ext_id]
                    self.__dict__["nutanix_count_vm"].labels(entity=cluster.name).set(len(cluster_vms_list))
                    self.__dict__["nutanix_count_vm_on"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_list if vm.power_state == 'ON']))
                    self.__dict__["nutanix_count_vm_off"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_list if vm.power_state == 'OFF']))
                    self.__dict__["nutanix_count_vm_boot_legacy"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_list if vm.boot_config.__class__.__name__ == 'LegacyBoot']))
                    self.__dict__["nutanix_count_vm_boot_uefi"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_list if vm.boot_config.__class__.__name__ == 'UefiBoot']))
                    self.__dict__["nutanix_count_vm_gpus"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_list if vm.gpus]))
                    self.__dict__["nutanix_count_vm_unprotected"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_list if vm.protection_type == 'UNPROTECTED']))
                    self.__dict__["nutanix_count_vm_pd_protected"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_list if vm.protection_type == 'PD_PROTECTED']))
                    self.__dict__["nutanix_count_vm_rule_protected"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_list if vm.protection_type == 'RULE_PROTECTED']))
                    self.__dict__["nutanix_count_vcpu"].labels(entity=cluster.name).set(sum([(vm.num_sockets * vm.num_cores_per_socket) for vm in cluster_vms_list]))
                    self.__dict__["nutanix_count_vram_mib"].labels(entity=cluster.name).set(sum([(vm.memory_size_bytes / 1048576) for vm in cluster_vms_list]))
                    self.__dict__["nutanix_count_vdisk"].labels(entity=cluster.name).set(sum(any(vdisk.backing_info.__class__.__name__ == 'VmDisk' for vdisk in vm.disks) for vm in cluster_vms_list if vm.disks))
                    self.__dict__["nutanix_count_vdisk_ide"].labels(entity=cluster.name).set(sum(any((vdisk.backing_info.__class__.__name__ == 'VmDisk' and vdisk.disk_address.bus_type == 'IDE') for vdisk in vm.disks) for vm in cluster_vms_list if vm.disks))
                    self.__dict__["nutanix_count_vdisk_sata"].labels(entity=cluster.name).set(sum(any((vdisk.backing_info.__class__.__name__ == 'VmDisk' and vdisk.disk_address.bus_type == 'SATA') for vdisk in vm.disks) for vm in cluster_vms_list if vm.disks))
                    self.__dict__["nutanix_count_vdisk_scsi"].labels(entity=cluster.name).set(sum(any((vdisk.backing_info.__class__.__name__ == 'VmDisk' and vdisk.disk_address.bus_type == 'SCSI') for vdisk in vm.disks) for vm in cluster_vms_list if vm.disks))
                    self.__dict__["nutanix_count_vnic"].labels(entity=cluster.name).set(sum([len(vm.nics) for vm in cluster_vms_list if vm.nics]))
                    cluster_vms_with_ngt = [vm for vm in cluster_vms_list if vm.guest_tools]
                    self.__dict__["nutanix_count_ngt_installed"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_with_ngt if vm.guest_tools.is_installed is True]))
                    self.__dict__["nutanix_count_ngt_enabled"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_with_ngt if vm.guest_tools.is_enabled is True]))
                    self.__dict__["nutanix_count_ngt_reachable"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_with_ngt if vm.guest_tools.is_reachable is True]))
                    self.__dict__["nutanix_count_ngt_vss_snapshot_capable"].labels(entity=cluster.name).set(len([vm for vm in cluster_vms_with_ngt if vm.guest_tools.is_vss_snapshot_capable is True]))
            #endregion vm

            #region host
            if not host_list:
                clustermgmt_client = v4_init_api_client(module='ntnx_clustermgmt_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
                host_list = v4_get_all_entities(module=ntnx_clustermgmt_py_client,client=clustermgmt_client,function='list_hosts',limit=limit,module_entity_api='ClustersApi')
            for cluster in cluster_list:
                if 'PRISM_CENTRAL' not in cluster.config.cluster_function:
                    cluster_hosts_list = [host for host in host_list if host.cluster.uuid == cluster.ext_id]
                    self.__dict__["nutanix_count_node"].labels(entity=cluster.name).set(len(cluster_hosts_list))
            #endregion host

            #region storage_container
            if not storage_container_list:
                clustermgmt_client = v4_init_api_client(module='ntnx_clustermgmt_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
                storage_container_list = v4_get_all_entities(module=ntnx_clustermgmt_py_client,client=clustermgmt_client,function='list_storage_containers',limit=limit,module_entity_api='StorageContainersApi')
            for cluster in cluster_list:
                if 'PRISM_CENTRAL' not in cluster.config.cluster_function:
                    cluster_storage_containers_list = [storage_container for storage_container in storage_container_list if storage_container.cluster_ext_id == cluster.ext_id]
                    self.__dict__["nutanix_count_storage_container"].labels(entity=cluster.name).set(len(cluster_storage_containers_list))
                    self.__dict__["nutanix_count_storage_container_encrypted"].labels(entity=cluster.name).set(len([storage_container for storage_container in cluster_storage_containers_list if storage_container.is_encrypted is True]))
                    self.__dict__["nutanix_count_storage_container_rf1"].labels(entity=cluster.name).set(len([storage_container for storage_container in cluster_storage_containers_list if storage_container.replication_factor == 1]))
                    self.__dict__["nutanix_count_storage_container_rf2"].labels(entity=cluster.name).set(len([storage_container for storage_container in cluster_storage_containers_list if storage_container.replication_factor == 2]))
                    self.__dict__["nutanix_count_storage_container_rf3"].labels(entity=cluster.name).set(len([storage_container for storage_container in cluster_storage_containers_list if storage_container.replication_factor == 3]))
            #endregion storage_container

            #region disk
            if not disk_list:
                clustermgmt_client = v4_init_api_client(module='ntnx_clustermgmt_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
                disk_list = v4_get_all_entities(module=ntnx_clustermgmt_py_client,client=clustermgmt_client,function='list_disks',limit=limit,module_entity_api='DisksApi')
            for cluster in cluster_list:
                if 'PRISM_CENTRAL' not in cluster.config.cluster_function:
                    cluster_disk_list = [disk for disk in disk_list if disk.cluster_ext_id == cluster.ext_id]
                    self.__dict__["nutanix_count_disk"].labels(entity=cluster.name).set(len(cluster_disk_list))
                    self.__dict__["nutanix_count_disk_ssd_pcie"].labels(entity=cluster.name).set(len([disk for disk in cluster_disk_list if disk.storage_tier == 'SSD_PCIE']))
                    self.__dict__["nutanix_count_disk_ssd_sata"].labels(entity=cluster.name).set(len([disk for disk in cluster_disk_list if disk.storage_tier == 'SSD_SATA']))
                    self.__dict__["nutanix_count_disk_das_sata"].labels(entity=cluster.name).set(len([disk for disk in cluster_disk_list if disk.storage_tier == 'DAS_SATA']))
                    self.__dict__["nutanix_count_disk_ssd_mem_nvme"].labels(entity=cluster.name).set(len([disk for disk in cluster_disk_list if disk.storage_tier == 'SSD_MEM_NVME']))
            #endregion disk

            #region networking
            if not subnet_list:
                networking_client = v4_init_api_client(module='ntnx_networking_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
                subnet_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_subnets',limit=limit,module_entity_api='SubnetsApi')
            for cluster in cluster_list:
                if 'PRISM_CENTRAL' not in cluster.config.cluster_function:
                    cluster_subnets_list = [subnet for subnet in subnet_list if subnet.cluster_reference == cluster.ext_id]
                    self.__dict__["nutanix_count_subnet"].labels(entity=cluster.name).set(len(cluster_subnets_list))
            #endregion networking

            #endregion count

        #endregion #?clusters

        #region #?hosts
        if self.hosts_metrics:
            if not host_list:
                host_list = v4_get_all_entities(module=ntnx_clustermgmt_py_client,client=clustermgmt_client,function='list_hosts',limit=limit,module_entity_api='ClustersApi')

            #region stats
            #* get metrics for each cluster
            host_details_list = []
            metrics=[]
            error_list=[]
            for entity in host_list:
                entity_details = {
                    'entity_name': entity.host_name,
                    'entity_uuid': entity.ext_id,
                    'entity_parent_uuid': entity.cluster.uuid,
                }
                #print(entity_details)
                host_details_list.append(entity_details)
            #print(host_details_list)
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(host_details_list)} entities...{PrintColors.RESET}")
            with tqdm.tqdm(total=len(host_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching hosts metrics") as progress_bar:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(
                            v4_get_entity_stats,
                            client=clustermgmt_client,
                            module=ntnx_clustermgmt_py_client,
                            entity_api='ClustersApi',
                            function='get_host_stats',
                            entity=host,
                            metric_key_prefix='nutanix_clustermgmt_host_stats_',
                            sampling_interval=30,
                            stat_type='LAST'
                        ) for host in host_details_list]
                    for future in as_completed(futures):
                        try:
                            entities = future.result()
                            if isinstance(entities, Iterable):
                                metrics.extend(entities)
                            else:
                                metrics.append(entities)
                        except ntnx_clustermgmt_py_client.rest.ApiException as e:
                            error_data = json.loads(e.body)
                            for error in error_data['data']['error']:
                                #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                error_list.append(error_message)
                        except Exception as e:
                            print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                        finally:
                            progress_bar.update(1)
            for error in error_list:
                print(error)
            for metric in metrics:
                #print(metric)
                key, entity, value = metric.split(':')
                #print(f"key: {key}, entity: {entity}, value: {value}")
                self.__dict__[key].labels(host=entity).set(value)
            #endregion stats

            #region count

            #region vm
            if not vms_list:
                vmm_client = v4_init_api_client(module='ntnx_vmm_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
                vms_list = v4_get_all_entities(module=ntnx_vmm_py_client,client=vmm_client,function='list_vms',limit=limit,module_entity_api='VmApi')
            for host in host_list:
                powered_on_vms_list= [vm for vm in vms_list if vm.power_state == 'ON']
                host_vms_list= [vm for vm in powered_on_vms_list if vm.host.ext_id == host.ext_id]
                self.__dict__["nutanix_count_vm"].labels(entity=host.host_name).set(len(host_vms_list))
                self.__dict__["nutanix_count_vm_on"].labels(entity=host.host_name).set(len([vm for vm in host_vms_list if vm.power_state == 'ON']))
                self.__dict__["nutanix_count_vm_off"].labels(entity=host.host_name).set(len([vm for vm in host_vms_list if vm.power_state == 'OFF']))
                self.__dict__["nutanix_count_vm_boot_legacy"].labels(entity=host.host_name).set(len([vm for vm in host_vms_list if vm.boot_config.__class__.__name__ == 'LegacyBoot']))
                self.__dict__["nutanix_count_vm_boot_uefi"].labels(entity=host.host_name).set(len([vm for vm in host_vms_list if vm.boot_config.__class__.__name__ == 'UefiBoot']))
                self.__dict__["nutanix_count_vm_gpus"].labels(entity=host.host_name).set(len([vm for vm in host_vms_list if vm.gpus]))
                self.__dict__["nutanix_count_vm_unprotected"].labels(entity=host.host_name).set(len([vm for vm in host_vms_list if vm.protection_type == 'UNPROTECTED']))
                self.__dict__["nutanix_count_vm_pd_protected"].labels(entity=host.host_name).set(len([vm for vm in host_vms_list if vm.protection_type == 'PD_PROTECTED']))
                self.__dict__["nutanix_count_vm_rule_protected"].labels(entity=host.host_name).set(len([vm for vm in host_vms_list if vm.protection_type == 'RULE_PROTECTED']))
                self.__dict__["nutanix_count_vcpu"].labels(entity=host.host_name).set(sum([(vm.num_sockets * vm.num_cores_per_socket) for vm in host_vms_list]))
                self.__dict__["nutanix_count_vram_mib"].labels(entity=host.host_name).set(sum([(vm.memory_size_bytes / 1048576) for vm in host_vms_list]))
                self.__dict__["nutanix_count_vdisk"].labels(entity=host.host_name).set(sum(any(vdisk.backing_info.__class__.__name__ == 'VmDisk' for vdisk in vm.disks) for vm in host_vms_list if vm.disks))
                self.__dict__["nutanix_count_vdisk_ide"].labels(entity=host.host_name).set(sum(any((vdisk.backing_info.__class__.__name__ == 'VmDisk' and vdisk.disk_address.bus_type == 'IDE') for vdisk in vm.disks) for vm in host_vms_list if vm.disks))
                self.__dict__["nutanix_count_vdisk_sata"].labels(entity=host.host_name).set(sum(any((vdisk.backing_info.__class__.__name__ == 'VmDisk' and vdisk.disk_address.bus_type == 'SATA') for vdisk in vm.disks) for vm in host_vms_list if vm.disks))
                self.__dict__["nutanix_count_vdisk_scsi"].labels(entity=host.host_name).set(sum(any((vdisk.backing_info.__class__.__name__ == 'VmDisk' and vdisk.disk_address.bus_type == 'SCSI') for vdisk in vm.disks) for vm in host_vms_list if vm.disks))
                self.__dict__["nutanix_count_vnic"].labels(entity=host.host_name).set(sum([len(vm.nics) for vm in host_vms_list if vm.nics]))
                host_vms_with_ngt = [vm for vm in host_vms_list if vm.guest_tools]
                self.__dict__["nutanix_count_ngt_installed"].labels(entity=host.host_name).set(len([vm for vm in host_vms_with_ngt if vm.guest_tools.is_installed is True]))
                self.__dict__["nutanix_count_ngt_enabled"].labels(entity=host.host_name).set(len([vm for vm in host_vms_with_ngt if vm.guest_tools.is_enabled is True]))
                self.__dict__["nutanix_count_ngt_reachable"].labels(entity=host.host_name).set(len([vm for vm in host_vms_with_ngt if vm.guest_tools.is_reachable is True]))
                self.__dict__["nutanix_count_ngt_vss_snapshot_capable"].labels(entity=host.host_name).set(len([vm for vm in host_vms_with_ngt if vm.guest_tools.is_vss_snapshot_capable is True]))
            #endregion vm

            #region disk
            if not disk_list:
                clustermgmt_client = v4_init_api_client(module='ntnx_clustermgmt_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
                disk_list = v4_get_all_entities(module=ntnx_clustermgmt_py_client,client=clustermgmt_client,function='list_disks',limit=limit,module_entity_api='DisksApi')
            for host in host_list:
                host_disk_list = [disk for disk in disk_list if disk.node_ext_id == host.ext_id]
                self.__dict__["nutanix_count_disk"].labels(entity=host.host_name).set(len(host_disk_list))
                self.__dict__["nutanix_count_disk_ssd_pcie"].labels(entity=host.host_name).set(len([disk for disk in host_disk_list if disk.storage_tier == 'SSD_PCIE']))
                self.__dict__["nutanix_count_disk_ssd_sata"].labels(entity=host.host_name).set(len([disk for disk in host_disk_list if disk.storage_tier == 'SSD_SATA']))
                self.__dict__["nutanix_count_disk_das_sata"].labels(entity=host.host_name).set(len([disk for disk in host_disk_list if disk.storage_tier == 'DAS_SATA']))
                self.__dict__["nutanix_count_disk_ssd_mem_nvme"].labels(entity=host.host_name).set(len([disk for disk in host_disk_list if disk.storage_tier == 'SSD_MEM_NVME']))
            #endregion disk

            #endregion count
        #endregion #?hosts

        #region #?storage_containers
        if self.storage_containers_metrics:
            if not storage_container_list:
                storage_container_list = v4_get_all_entities(module=ntnx_clustermgmt_py_client,client=clustermgmt_client,function='list_storage_containers',limit=limit,module_entity_api='StorageContainersApi')

            #region stats
            #* get metrics for each storage container
            storage_container_details_list = []
            metrics=[]
            error_list=[]
            for entity in storage_container_list:
                entity_details = {
                    'entity_name': entity.name,
                    'entity_uuid': entity.container_ext_id,
                    'parent_name': entity.cluster_name,
                }
                storage_container_details_list.append(entity_details)
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(storage_container_details_list)} entities...{PrintColors.RESET}")
            with tqdm.tqdm(total=len(storage_container_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching storage containers metrics") as progress_bar:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(
                            v4_get_entity_stats,
                            client=clustermgmt_client,
                            module=ntnx_clustermgmt_py_client,
                            entity_api='StorageContainersApi',
                            function='get_storage_container_stats',
                            entity=storage_container,
                            metric_key_prefix='nutanix_clustermgmt_storage_container_stats_',
                            sampling_interval=30,
                            stat_type='LAST'
                        ) for storage_container in storage_container_details_list]
                    for future in as_completed(futures):
                        try:
                            entities = future.result()
                            if isinstance(entities, Iterable):
                                metrics.extend(entities)
                            else:
                                metrics.append(entities)
                        except ntnx_clustermgmt_py_client.rest.ApiException as e:
                            error_data = json.loads(e.body)
                            for error in error_data['data']['error']:
                                #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                error_list.append(error_message)
                        except Exception as e:
                            print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                        finally:
                            progress_bar.update(1)
            for error in error_list:
                print(error)
            for metric in metrics:
                #print(metric)
                key, entity, value = metric.split(':')
                #print(f"key: {key}, entity: {entity}, value: {value}")
                storage_container_cluster = next(iter([storage_container['parent_name'] for storage_container in storage_container_details_list if storage_container['entity_name'] == entity]))
                entity = f"{storage_container_cluster}_{entity}"
                entity = entity.replace(".","_")
                entity = entity.replace("-","_")
                self.__dict__[key].labels(storage_container=entity).set(value)
            #endregion stats
        #endregion #?storage_containers

        #region #?disks
        if self.disks_metrics:
            if not disk_list:
                disk_list = v4_get_all_entities(module=ntnx_clustermgmt_py_client,client=clustermgmt_client,function='list_disks',limit=limit,module_entity_api='DisksApi')

            #region stats
            #* get metrics for each disk
            disk_details_list = []
            metrics=[]
            error_list=[]
            for entity in disk_list:
                entity_details = {
                    'entity_name': entity.serial_number,
                    'entity_uuid': entity.ext_id,
                }
                disk_details_list.append(entity_details)
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(disk_details_list)} entities...{PrintColors.RESET}")
            with tqdm.tqdm(total=len(disk_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching disks metrics") as progress_bar:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(
                            v4_get_entity_stats,
                            client=clustermgmt_client,
                            module=ntnx_clustermgmt_py_client,
                            entity_api='DisksApi',
                            function='get_disk_stats',
                            entity=disk,
                            metric_key_prefix='nutanix_clustermgmt_disk_stats_',
                            sampling_interval=30,
                            stat_type='LAST'
                        ) for disk in disk_details_list]
                    for future in as_completed(futures):
                        try:
                            entities = future.result()
                            if isinstance(entities, Iterable):
                                metrics.extend(entities)
                            else:
                                metrics.append(entities)
                        except ntnx_clustermgmt_py_client.rest.ApiException as e:
                            error_data = json.loads(e.body)
                            for error in error_data['data']['error']:
                                #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                error_list.append(error_message)
                        except Exception as e:
                            print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                        finally:
                            progress_bar.update(1)
            for error in error_list:
                print(error)
            for metric in metrics:
                #print(metric)
                key, entity, value = metric.split(':')
                #print(f"key: {key}, entity: {entity}, value: {value}")
                self.__dict__[key].labels(disk=entity).set(value)
            #endregion stats
        #endregion #?disks

        #endregion #?clustermgmt


        #region #?networking
        if self.networking_metrics:
            #* initialize variable for API client configuration
            networking_client = v4_init_api_client(module='ntnx_networking_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)

            #region #?layer2 stretch
            if not layer2_stretch_list:
                layer2_stretch_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_layer2_stretches',limit=limit,module_entity_api='Layer2StretchesApi')

            #region stats
            #* get metrics for each layer2 stretch
            layer2_stretch_details_list = []
            metrics=[]
            error_list=[]
            for entity in layer2_stretch_list:
                entity_details = {
                    'entity_name': entity.name,
                    'entity_uuid': entity.ext_id,
                }
                layer2_stretch_details_list.append(entity_details)
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(layer2_stretch_details_list)} entities...{PrintColors.RESET}")
            if len(layer2_stretch_details_list) > 0:
                with tqdm.tqdm(total=len(layer2_stretch_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching layer2 stretch metrics") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_entity_stats,
                                client=networking_client,
                                module=ntnx_networking_py_client,
                                entity_api='Layer2StretchesStatsApi',
                                function='get_layer2_stretch_stats',
                                entity=layer2stretch,
                                metric_key_prefix='nutanix_networking_layer2_stretch_stats_',
                                sampling_interval=30,
                                stat_type='LAST'
                            ) for layer2stretch in layer2_stretch_details_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if isinstance(entities, Iterable):
                                    metrics.extend(entities)
                                else:
                                    metrics.append(entities)
                            except ntnx_networking_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                for metric in metrics:
                    #print(metric)
                    key, entity, value = metric.split(':')
                    #print(f"key: {key}, entity: {entity}, value: {value}")
                    self.__dict__[key].labels(layer2_stretch=entity).set(value)
            #endregion stats
            #endregion #?layer2 stretch

            #region #?load balancer sessions
            if not load_balancer_sessions_list:
                load_balancer_sessions_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_load_balancer_sessions',limit=limit,module_entity_api='LoadBalancerSessionsApi')

            #region stats
            #* get metrics for each load balancer sessions
            load_balancer_sessions_details_list = []
            metrics=[]
            error_list=[]
            for entity in load_balancer_sessions_list:
                entity_details = {
                    'entity_name': entity.name,
                    'entity_uuid': entity.ext_id,
                }
                load_balancer_sessions_details_list.append(entity_details)
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(load_balancer_sessions_details_list)} entities...{PrintColors.RESET}")
            if len(load_balancer_sessions_details_list) > 0:
                with tqdm.tqdm(total=len(load_balancer_sessions_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching load balancer sessions metrics") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_entity_stats,
                                client=networking_client,
                                module=ntnx_networking_py_client,
                                entity_api='LoadBalancerSessionStatsApi',
                                function='get_load_balancer_session_stats',
                                entity=session,
                                metric_key_prefix='nutanix_networking_load_balancer_session_stats_',
                                sampling_interval=30,
                                stat_type='LAST'
                            ) for session in load_balancer_sessions_details_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if isinstance(entities, Iterable):
                                    metrics.extend(entities)
                                else:
                                    metrics.append(entities)
                            except ntnx_networking_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                for metric in metrics:
                    #print(metric)
                    key, entity, value = metric.split(':')
                    #print(f"key: {key}, entity: {entity}, value: {value}")
                    self.__dict__[key].labels(load_balancer_session=entity).set(value)
            #endregion stats
            #endregion #?load balancer sessions

            #region #?traffic mirror
            if not traffic_mirrors_list:
                traffic_mirrors_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_traffic_mirrors',limit=limit,module_entity_api='TrafficMirrorsApi')

            #region stats
            #* get metrics for each load balancer sessions
            traffic_mirrors_details_list = []
            metrics=[]
            error_list=[]
            for entity in traffic_mirrors_list:
                entity_details = {
                    'entity_name': entity.name,
                    'entity_uuid': entity.ext_id,
                }
                traffic_mirrors_details_list.append(entity_details)
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(traffic_mirrors_details_list)} entities...{PrintColors.RESET}")
            if len(traffic_mirrors_details_list) > 0:
                with tqdm.tqdm(total=len(traffic_mirrors_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching traffic mirrors metrics") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_entity_stats,
                                client=networking_client,
                                module=ntnx_networking_py_client,
                                entity_api='TrafficMirrorStatsApi',
                                function='get_traffic_mirror_stats',
                                entity=mirror,
                                metric_key_prefix='nutanix_networking_traffic_mirror_stats_',
                                sampling_interval=30,
                                stat_type='LAST'
                            ) for mirror in traffic_mirrors_details_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if isinstance(entities, Iterable):
                                    metrics.extend(entities)
                                else:
                                    metrics.append(entities)
                            except ntnx_networking_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                for metric in metrics:
                    #print(metric)
                    key, entity, value = metric.split(':')
                    #print(f"key: {key}, entity: {entity}, value: {value}")
                    self.__dict__[key].labels(traffic_mirror=entity).set(value)
            #endregion stats
            #endregion #?traffic mirror

            #region #?vpc external subnets
            if not vpc_list:
                vpc_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_vpcs',limit=limit,module_entity_api='VpcsApi')

            #region stats
            #* get metrics for each vpc external subnets
            vpc_external_network_details_list = []
            metrics=[]
            error_list=[]
            for entity in vpc_list:
                if entity.external_subnets:
                    for external_subnet in entity.external_subnets:
                        entity_details = {
                            'entity_name': entity.name,
                            'entity_uuid': external_subnet.subnet_reference,
                            'entity_parent_uuid': entity.ext_id,
                        }
                        vpc_external_network_details_list.append(entity_details)
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(vpc_external_network_details_list)} entities...{PrintColors.RESET}")
            if len(vpc_external_network_details_list) > 0:
                with tqdm.tqdm(total=len(vpc_external_network_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching VPC External Subnets North/South traffic metrics") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_entity_stats,
                                client=networking_client,
                                module=ntnx_networking_py_client,
                                entity_api='VpcNsStatsApi',
                                function='get_vpc_ns_stats',
                                entity=subnet,
                                metric_key_prefix='nutanix_networking_vpc_ns_stats_',
                                sampling_interval=30,
                                stat_type='LAST'
                            ) for subnet in vpc_external_network_details_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if isinstance(entities, Iterable):
                                    metrics.extend(entities)
                                else:
                                    metrics.append(entities)
                            except ntnx_networking_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                for metric in metrics:
                    #print(metric)
                    key, entity, value = metric.split(':')
                    #print(f"key: {key}, entity: {entity}, value: {value}")
                    self.__dict__[key].labels(vpc_ns=entity).set(value)
            #endregion stats
            #endregion #?vpc external subnets

            #region #?vpn connections
            if not vpn_connection_list:
                vpn_connection_list = v4_get_all_entities(module=ntnx_networking_py_client,client=networking_client,function='list_vpn_connections',limit=limit,module_entity_api='VpnConnectionsApi')

            #region stats
            #* get metrics for each vpn connection
            vpn_connection_details_list = []
            metrics=[]
            error_list=[]
            for entity in vpn_connection_list:
                entity_details = {
                    'entity_name': entity.name,
                    'entity_uuid': entity.ext_id,
                }
                vpn_connection_details_list.append(entity_details)
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(vpn_connection_details_list)} entities...{PrintColors.RESET}")
            if len(vpn_connection_details_list) > 0:
                with tqdm.tqdm(total=len(vpn_connection_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching VPN Connections metrics") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_entity_stats,
                                client=networking_client,
                                module=ntnx_networking_py_client,
                                entity_api='VpnConnectionStatsApi',
                                function='get_vpn_connection_stats',
                                entity=connection,
                                metric_key_prefix='nutanix_networking_vpn_connection_stats_',
                                sampling_interval=30,
                                stat_type='LAST'
                            ) for connection in vpn_connection_details_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if isinstance(entities, Iterable):
                                    metrics.extend(entities)
                                else:
                                    metrics.append(entities)
                            except ntnx_networking_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                for metric in metrics:
                    #print(metric)
                    key, entity, value = metric.split(':')
                    #print(f"key: {key}, entity: {entity}, value: {value}")
                    self.__dict__[key].labels(vpn_connection=entity).set(value)
            #endregion stats
            #endregion #?vpn connections

        #endregion #?networking


        #region #?vmm
        if self.vm_list != '':
            #* initialize variable for API client configuration
            vmm_client = v4_init_api_client(module='ntnx_vmm_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)

            if not vms_list:
                vms_list = v4_get_all_entities(module=ntnx_vmm_py_client,client=vmm_client,function='list_vms',limit=limit,module_entity_api='VmApi')

            #region stats
            if (self.vm_list).lower() == 'all':
                #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Fetching VM stats...{PrintColors.RESET}")
                start_time = (datetime.now(timezone.utc) - timedelta(seconds=150)).isoformat()
                end_time = (datetime.now(timezone.utc)).isoformat()
                entity_api = ntnx_vmm_py_client.StatsApi(api_client=vmm_client)
                response = entity_api.list_vm_stats(_page=0,_limit=1,_startTime=start_time, _endTime=end_time, _samplingInterval=30, _statType='LAST', _select='*')
                total_available_results=response.metadata.total_available_results
                page_count = math.ceil(total_available_results/limit)
                stats_list=[]
                error_list=[]
                with tqdm.tqdm(total=page_count, desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching vm stats pages") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_all_vm_stats,
                                client=vmm_client,
                                page=page_number,
                                limit=limit,
                                start_time=start_time,
                                end_time=end_time,
                                sampling_interval=30,
                                stat_type='LAST'
                            ) for page_number in range(0, page_count, 1)]
                        for future in as_completed(futures):
                            try:
                                stats = future.result()
                                if isinstance(stats, Iterable):
                                    stats_list.extend(stats)
                                else:
                                    stats_list.append(stats)
                            except ntnx_vmm_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                vm_stats_list = stats_list
                exclude_list = ['timestamp','_reserved','_object_type','_unknown_fields','ext_id','links', 'container_ext_id', 'tenant_id', 'stat_type', 'cluster', 'hypervisor_type']
                for vm_stat in vm_stats_list:
                    vm_name = [vm.name for vm in vms_list if vm.ext_id == vm_stat.ext_id]
                    if vm_name:
                        for vm_stats_tuple in vm_stat.stats:
                            stats = vm_stats_tuple.to_dict()
                            for metric in stats:
                                if metric is not None:
                                    if metric not in exclude_list:
                                        metric_data = stats.get(metric)
                                        if metric_data is not None:
                                            key_string = f"nutanix_vmm_ahv_stats_vm_{metric}"
                                            key_string = key_string.replace(".","_")
                                            key_string = key_string.replace("-","_")
                                            self.__dict__[key_string].labels(vm=vm_name).set(metric_data)
            else:
                vm_list_array = self.vm_list.split(',')

                #* get metrics for each vm
                vm_details_list = []
                metrics=[]
                error_list=[]
                for entity in vm_list_array:
                    entity_details = {
                        'entity_name': entity,
                        'entity_uuid': next(iter([item.ext_id for item in vms_list if item.name == entity])),
                    }
                    vm_details_list.append(entity_details)
                #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(vm_details_list)} entities...{PrintColors.RESET}")
                with tqdm.tqdm(total=len(vm_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching vm metrics") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_entity_stats,
                                client=vmm_client,
                                module=ntnx_vmm_py_client,
                                entity_api='StatsApi',
                                function='get_vm_stats_by_id',
                                entity=vm,
                                metric_key_prefix='nutanix_vmm_ahv_stats_vm_',
                                sampling_interval=30,
                                stat_type='LAST'
                            ) for vm in vm_details_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if isinstance(entities, Iterable):
                                    metrics.extend(entities)
                                else:
                                    metrics.append(entities)
                            except ntnx_vmm_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                for metric in metrics:
                    #print(metric)
                    key, entity, value = metric.split(':')
                    #print(f"key: {key}, entity: {entity}, value: {value}")
                    self.__dict__[key].labels(vm=entity).set(value)
            #endregion stats
        #endregion #?vmm


        #region #?files
        if self.files_metrics:
            #* initialize variable for API client configuration
            files_client = v4_init_api_client(module='ntnx_files_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
            if not files_server_list:
                files_server_list = v4_get_all_entities(module=ntnx_files_py_client,client=files_client,function='list_file_servers',limit=limit,module_entity_api='FileServersApi')

            #region #?antivirus stats
            #region get entities
            #* get metrics for each files antivirus server
            antivirus_server_details_list = []
            metrics=[]
            for entity in files_server_list:
                #get antivirus servers for each file server
                entity_api = ntnx_files_py_client.AntivirusServersApi(api_client=files_client)
                #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Fetching list of external antivirus servers for Files server instance {entity.name}...{PrintColors.RESET}")
                response = entity_api.list_antivirus_servers(fileServerExtId=entity.ext_id,_page=0,_limit=100)
                antivirus_server_list = response.data
                for av_server in antivirus_server_list:
                    #populate the list with the file server antivirus details
                    entity_details = {
                        'entity_name': av_server.name,
                        'entity_uuid': av_server.ext_id,
                        'entity_parent_name': entity.name,
                        'entity_parent_uuid': entity.ext_id,
                    }
                    antivirus_server_details_list.append(entity_details)
            #endregion get entities

            #region stats
            if len(antivirus_server_details_list) > 0:
                metrics=[]
                error_list=[]
                #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(antivirus_server_details_list)} entities...{PrintColors.RESET}")
                with tqdm.tqdm(total=len(antivirus_server_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching Files Server antivirus metrics") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_files_analytics_stats,
                                client=files_client,
                                module=ntnx_files_py_client,
                                entity_api='AnalyticsApi',
                                function='get_antivirus_server_stats',
                                entity=antivirus_server,
                                metric_key_prefix=f'nutanix_files_antivirus_stats_'
                            ) for antivirus_server in antivirus_server_details_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if isinstance(entities, Iterable):
                                    metrics.extend(entities)
                                else:
                                    metrics.append(entities)
                            except ntnx_files_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                for metric in metrics:
                    #print(metric)
                    key, entity, value = metric.split(':')
                    #print(f"key: {key}, entity: {entity}, value: {value}")
                    entity_parent = next(iter([item['entity_parent_name'] for item in antivirus_server_details_list if item['entity_name'] == entity]))
                    entity = f"{entity_parent}_{entity}"
                    entity = entity.replace(".","_")
                    entity = entity.replace("-","_")
                    self.__dict__[key].labels(antivirus=entity).set(value)
            #endregion stats
            #endregion #?antivirus stats

            #region #?file_server stats
            #region get entities
            #* get metrics for each files antivirus server
            files_server_details_list = []
            metrics=[]
            error_list=[]
            for entity in files_server_list:
                entity_details = {
                    'entity_name': entity.name,
                    'entity_uuid': entity.ext_id,
                }
                files_server_details_list.append(entity_details)
            #endregion get entities

            #region stats
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(files_server_details_list)} entities...{PrintColors.RESET}")
            if len(files_server_details_list) >0:
                with tqdm.tqdm(total=len(files_server_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching Files Server metrics") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_files_analytics_stats,
                                client=files_client,
                                module=ntnx_files_py_client,
                                entity_api='AnalyticsApi',
                                function='get_file_server_stats',
                                entity=file_server,
                                metric_key_prefix='nutanix_files_file_server_stats_'
                            ) for file_server in files_server_details_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if isinstance(entities, Iterable):
                                    metrics.extend(entities)
                                else:
                                    metrics.append(entities)
                            except ntnx_files_analytics_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                for metric in metrics:
                    #print(metric)
                    key, entity, value = metric.split(':')
                    #print(f"key: {key}, entity: {entity}, value: {value}")
                    self.__dict__[key].labels(file_server=entity).set(value)
            #endregion stats
            #endregion #?file_server stats

            #region #?mount_target stats
            #region get entities
            #* get metrics for each mount target
            mount_target_details_list = []
            metrics=[]
            error_list=[]
            for entity in files_server_list:
                #get antivirus servers for each file server
                entity_api = ntnx_files_py_client.MountTargetsApi(api_client=files_client)
                #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Fetching list of mount targets for Files server instance {entity.name}...{PrintColors.RESET}")
                response = entity_api.list_mount_targets(fileServerExtId=entity.ext_id,_page=0,_limit=100)
                mount_target_list = response.data
                for mount_target in mount_target_list:
                    #populate the list with the file server antivirus details
                    entity_details = {
                        'entity_name': mount_target.name,
                        'entity_uuid': mount_target.ext_id,
                        'entity_parent_name': entity.name,
                        'entity_parent_uuid': entity.ext_id,
                    }
                    mount_target_details_list.append(entity_details)
            #endregion get entities

            #region stats
            if mount_target_details_list:
                #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(mount_target_details_list)} entities...{PrintColors.RESET}")
                with tqdm.tqdm(total=len(mount_target_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching Files Server mount target metrics") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_files_analytics_stats,
                                client=files_client,
                                module=ntnx_files_py_client,
                                entity_api='AnalyticsApi',
                                function='get_mount_target_stats',
                                entity=mount_target,
                                metric_key_prefix='nutanix_files_mount_target_stats_'
                            ) for mount_target in mount_target_details_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if isinstance(entities, Iterable):
                                    metrics.extend(entities)
                                else:
                                    metrics.append(entities)
                            except ntnx_files_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                for metric in metrics:
                    #print(metric)
                    key, entity, value = metric.split(':')
                    #print(f"key: {key}, entity: {entity}, value: {value}")
                    entity_parent = next(iter([item['entity_parent_name'] for item in mount_target_details_list if item['entity_name'] == entity]))
                    entity = f"{entity_parent}_{entity}"
                    entity = entity.replace(".","_")
                    entity = entity.replace("-","_")
                    self.__dict__[key].labels(mount_target=entity).set(value)
            #endregion stats
            #endregion #?mount_target stats

        #endregion #?files


        #region #?objects
        if self.object_metrics:
            #* initialize variable for API client configuration
            objects_client = v4_init_api_client(module='ntnx_objects_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
            if not object_store_list:
                object_store_list = v4_get_all_entities(module=ntnx_objects_py_client,client=objects_client,function='list_objectstores',limit=limit,module_entity_api='ObjectStoresApi')

            #region #?object_store stats
            #* get metrics for each files antivirus server
            object_store_details_list = []
            metrics=[]
            for entity in object_store_list:
                entity_details = {
                    'entity_name': entity.name,
                    'entity_uuid': entity.ext_id,
                }
                object_store_details_list.append(entity_details)
            #print(object_store_details_list)
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(object_store_details_list)} entities...{PrintColors.RESET}")
            metrics=[]
            error_list=[]
            with tqdm.tqdm(total=len(object_store_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching object store metrics") as progress_bar:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(
                            v4_get_objectstore_stats,
                            client=objects_client,
                            module=ntnx_objects_py_client,
                            entity_api='StatsApi',
                            function='get_objectstore_stats_by_id',
                            entity=object_store,
                            metric_key_prefix='nutanix_objects_objectstore_stats_',
                            sampling_interval=30,
                            stat_type='LAST'
                        ) for object_store in object_store_details_list]
                    for future in as_completed(futures):
                        try:
                            entities = future.result()
                            if isinstance(entities, Iterable):
                                metrics.extend(entities)
                            else:
                                metrics.append(entities)
                        except ntnx_objects_py_client.rest.ApiException as e:
                            error_data = json.loads(e.body)
                            for error in error_data['data']['error']:
                                #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                error_list.append(error_message)
                        except Exception as e:
                            print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                        finally:
                            progress_bar.update(1)
            for error in error_list:
                print(error)
            for metric in metrics:
                #print(metric)
                key, entity, value = metric.split(':')
                #print(f"key: {key}, entity: {entity}, value: {value}")
                self.__dict__[key].labels(objectstore=entity).set(value)
            #endregion #?object_store stats

        #endregion #?objects


        #region #?volumes
        if self.volumes_metrics:
            #* initialize variable for API client configuration
            volumes_client = v4_init_api_client(module='ntnx_volumes_py_client', prism=self.prism, user=self.user, pwd=self.pwd, prism_secure=self.prism_secure)
            if not volume_group_list:
                volume_group_list = v4_get_all_entities(module=ntnx_volumes_py_client,client=volumes_client,function='list_volume_groups',limit=limit,module_entity_api='VolumeGroupsApi')

            #region #?volume_group stats
            volume_group_details_list = []
            metrics=[]
            error_list=[]
            for entity in volume_group_list:
                entity_details = {
                    'entity_name': entity.name,
                    'entity_uuid': entity.ext_id,
                }
                volume_group_details_list.append(entity_details)
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(volume_group_details_list)} entities...{PrintColors.RESET}")

            with tqdm.tqdm(total=len(volume_group_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching volume group metrics") as progress_bar:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(
                            v4_get_entity_stats,
                            client=volumes_client,
                            module=ntnx_volumes_py_client,
                            entity_api='VolumeGroupsApi',
                            function='get_volume_group_stats',
                            entity=volume_group,
                            metric_key_prefix='nutanix_volumes_volume_group_stats_',
                            sampling_interval=30,
                            stat_type='LAST'
                        ) for volume_group in volume_group_details_list]
                    for future in as_completed(futures):
                        try:
                            entities = future.result()
                            if isinstance(entities, Iterable):
                                metrics.extend(entities)
                            else:
                                metrics.append(entities)
                        except ntnx_volumes_py_client.rest.ApiException as e:
                            error_data = json.loads(e.body)
                            for error in error_data['data']['error']:
                                #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                error_list.append(error_message)
                        except Exception as e:
                            print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                        finally:
                            progress_bar.update(1)
            for error in error_list:
                print(error)
            for metric in metrics:
                #print(metric)
                key, entity, value = metric.split(':')
                #print(f"key: {key}, entity: {entity}, value: {value}")
                self.__dict__[key].labels(volume_group=entity).set(value)
            #endregion #?volume_group stats

            #region #?volume disks
            #region get entities
            volume_disk_details_list = []
            metrics=[]
            for entity in volume_group_list:
                #get volume disks for each volume group
                entity_list=[]
                error_list=[]
                entity_api = ntnx_volumes_py_client.VolumeGroupsApi(api_client=volumes_client)
                response = entity_api.list_volume_disks_by_volume_group_id(volumeGroupExtId=entity.ext_id,_page=0,_limit=1)
                total_available_results=response.metadata.total_available_results
                if total_available_results:
                    page_count = math.ceil(total_available_results/limit)
                if page_count > 0:
                    with tqdm.tqdm(total=page_count, desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching pages of Nutanix Volume volume disk entities for volume group {entity.name}") as progress_bar:
                        with ThreadPoolExecutor(max_workers=10) as executor:
                            futures = [executor.submit(
                                    entity_api.list_volume_disks_by_volume_group_id,
                                    volumeGroupExtId=entity.ext_id,
                                    page=page_number,
                                    limit=limit
                                ) for page_number in range(0, page_count, 1)]
                            for future in as_completed(futures):
                                try:
                                    entities = future.result()
                                    if hasattr(entities, 'data'):
                                        if isinstance(entities.data, Iterable):
                                            entity_list.extend(entities.data)
                                        else:
                                            entity_list.append(entities.data)
                                except ntnx_volumes_py_client.rest.ApiException as e:
                                    error_data = json.loads(e.body)
                                    for error in error_data['data']['error']:
                                        #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                        error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                        error_list.append(error_message)
                                except Exception as e:
                                    print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                                finally:
                                    progress_bar.update(1)
                    for error in error_list:
                        print(error)
                    volume_disk_list = entity_list
                #endregion get entities

            #region stats
                for volume_disk in volume_disk_list:
                    #populate the list with the volume disk details
                    entity_details = {
                        'entity_name': f"{entity.name}_{volume_disk.index}",
                        'entity_uuid': volume_disk.ext_id,
                        'entity_parent_name': entity.name,
                        'entity_parent_uuid': entity.ext_id,
                    }
                    volume_disk_details_list.append(entity_details)

            if len(volume_disk_details_list) > 0:
                #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Processing {len(volume_disk_details_list)} entities...{PrintColors.RESET}")
                metrics=[]
                error_list=[]
                with tqdm.tqdm(total=len(volume_disk_details_list), desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching volume disk metrics") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                            v4_get_entity_stats,
                            client=volumes_client,
                            module=ntnx_volumes_py_client,
                            entity_api='VolumeGroupsApi',
                            function='get_volume_disk_stats',
                            entity=volume_disk,
                            metric_key_prefix='nutanix_volumes_volume_disk_stats_',
                            sampling_interval=30,
                            stat_type='LAST'
                        ) for volume_disk in volume_disk_details_list]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if isinstance(entities, Iterable):
                                    metrics.extend(entities)
                                else:
                                    metrics.append(entities)
                            except ntnx_volumes_py_client.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
                for error in error_list:
                    print(error)
                for metric in metrics:
                    #print(metric)
                    key, entity, value = metric.split(':')
                    #print(f"key: {key}, entity: {entity}, value: {value}")
                    #print(volume_disk_details_list)
                    entity_parent = next(iter([item['entity_parent_name'] for item in volume_disk_details_list if item['entity_name'] == entity]))
                    entity = f"{entity_parent}_{entity}"
                    entity = entity.replace(".","_")
                    entity = entity.replace("-","_")
                    self.__dict__[key].labels(volume_disk=entity).set(value)
            #endregion stats

            #endregion #?volume disks

        #endregion #?volumes


class NutanixMetricsLegacy:
    """
    Representation of Prometheus metrics and loop to fetch and transform
    application metrics into Prometheus metrics.
    """
    def __init__(self,
                 ipmi_username='ADMIN', ipmi_secret=None,
                 app_port=9440, polling_interval_seconds=30, api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,
                 prism='127.0.0.1', user='admin', pwd='Nutanix/4u', prism_secure=False,
                 vm_list='',
                 cluster_metrics=True, storage_containers_metrics=True, ipmi_metrics=True, prism_central_metrics=False, ncm_ssp_metrics=False):
        self.ipmi_username = ipmi_username
        self.ipmi_secret = ipmi_secret
        self.app_port = app_port
        self.polling_interval_seconds = polling_interval_seconds
        self.api_requests_timeout_seconds = api_requests_timeout_seconds
        self.api_requests_retries = api_requests_retries
        self.api_sleep_seconds_between_retries = api_sleep_seconds_between_retries
        self.prism = prism
        self.user = user
        self.pwd = pwd
        self.prism_secure = prism_secure
        self.vm_list = vm_list
        self.cluster_metrics = cluster_metrics
        self.storage_containers_metrics = storage_containers_metrics
        self.ipmi_metrics = ipmi_metrics
        self.prism_central_metrics = prism_central_metrics
        self.ncm_ssp_metrics = ncm_ssp_metrics

        if self.cluster_metrics:
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [INFO] Initializing metrics for clusters...{PrintColors.RESET}")

            cluster_uuid, cluster_details = prism_get_cluster(api_server=prism,username=user,secret=pwd,secure=self.prism_secure,api_requests_timeout_seconds=self.api_requests_timeout_seconds, api_requests_retries=self.api_requests_retries, api_sleep_seconds_between_retries=self.api_sleep_seconds_between_retries)
            hosts_details = prism_get_hosts(api_server=self.prism,username=self.user,secret=self.pwd,secure=self.prism_secure,api_requests_timeout_seconds=self.api_requests_timeout_seconds, api_requests_retries=self.api_requests_retries, api_sleep_seconds_between_retries=self.api_sleep_seconds_between_retries)

            #creating host stats metrics
            for key,value in hosts_details[0]['stats'].items():
                #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                key_string = f"nutanix_host_stats_{key}"
                key_string = key_string.replace(".","_")
                key_string = key_string.replace("-","_")
                setattr(self, key_string, Gauge(key_string, key_string, ['host']))
            for key,value in hosts_details[0]['usage_stats'].items():
                #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                key_string = f"nutanix_host_usage_stats_{key}"
                key_string = key_string.replace(".","_")
                key_string = key_string.replace("-","_")
                setattr(self, key_string, Gauge(key_string, key_string, ['host']))

            #creating cluster stats metrics
            for key,value in cluster_details['stats'].items():
                #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                key_string = f"nutanix_cluster_stats_{key}"
                key_string = key_string.replace(".","_")
                key_string = key_string.replace("-","_")
                setattr(self, key_string, Gauge(key_string, key_string, ['cluster']))
            for key,value in cluster_details['usage_stats'].items():
                #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                key_string = f"nutanix_cluster_usage_stats_{key}"
                key_string = key_string.replace(".","_")
                key_string = key_string.replace("-","_")
                setattr(self, key_string, Gauge(key_string, key_string, ['cluster']))

            #creating cluster counts metrics
            key_strings = [
                "nutanix_count_vg",
                "nutanix_count_vm",
                "nutanix_count_vm_on",
                "nutanix_count_vm_off",
                "nutanix_count_vcpu",
                "nutanix_count_vram_mib",
                "nutanix_count_vdisk",
                "nutanix_count_vdisk_ide",
                "nutanix_count_vdisk_sata",
                "nutanix_count_vdisk_scsi",
                "nutanix_count_vnic"
            ]
            for key_string in key_strings:
                setattr(self, key_string, Gauge(key_string, key_string, ['entity']))

            #other misc info based metrics
            setattr(self, 'nutanix_cluster', Info('nutanix_cluster', 'Misc cluster information'))

        if self.vm_list:
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [INFO] Initializing metrics for virtual machines...{PrintColors.RESET}")
            vm_list_array = self.vm_list.split(',')
            vm_details = prism_get_vm(vm_name=vm_list_array[0],api_server=prism,username=user,secret=pwd,secure=self.prism_secure,api_requests_timeout_seconds=self.api_requests_timeout_seconds, api_requests_retries=self.api_requests_retries, api_sleep_seconds_between_retries=self.api_sleep_seconds_between_retries)
            if len(vm_details) > 0:
                for key,value in vm_details['stats'].items():
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_vms_stats_{key}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    setattr(self, key_string, Gauge(key_string, key_string, ['vm']))
                for key,value in vm_details['usageStats'].items():
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_vms_usage_stats_{key}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    setattr(self, key_string, Gauge(key_string, key_string, ['vm']))
            else:
                print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [ERROR] Specified VM {vm_list_array[0]} does not exist on Prism Element {prism}...{PrintColors.RESET}")
                exit(1)

        if self.storage_containers_metrics:
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [INFO] Initializing metrics for storage containers...{PrintColors.RESET}")
            storage_containers_details = prism_get_storage_containers(api_server=prism,username=user,secret=pwd,secure=self.prism_secure,api_requests_timeout_seconds=self.api_requests_timeout_seconds, api_requests_retries=self.api_requests_retries, api_sleep_seconds_between_retries=self.api_sleep_seconds_between_retries)
            for key,value in storage_containers_details[0]['stats'].items():
                #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                key_string = f"nutanix_storage_container_stats_{key}"
                key_string = key_string.replace(".","_")
                key_string = key_string.replace("-","_")
                setattr(self, key_string, Gauge(key_string, key_string, ['storage_container']))
            for key,value in storage_containers_details[0]['usage_stats'].items():
                #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                key_string = f"nutanix_storage_container_usage_stats_{key}"
                key_string = key_string.replace(".","_")
                key_string = key_string.replace("-","_")
                setattr(self, key_string, Gauge(key_string, key_string, ['storage_container']))

        if self.ipmi_metrics:
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [INFO] Initializing metrics for IPMI adapters...{PrintColors.RESET}")
            key_strings = [
                "nutanix_power_consumption_power_consumed_watts",
                "nutanix_power_consumption_min_consumed_watts",
                "nutanix_power_consumption_max_consumed_watts",
                "nutanix_power_consumption_average_consumed_watts",
                "nutanix_thermal_cpu_temp_celsius",
                "nutanix_thermal_pch_temp_celcius",
                "nutanix_thermal_system_temp_celcius",
                "nutanix_thermal_peripheral_temp_celcius",
                "nutanix_thermal_inlet_temp_celcius",
                "nutanix_power_state",
                "nutanix_cpu_utilization",
                "nutanix_memory_utilization"
            ]
            for key_string in key_strings:
                setattr(self, key_string, Gauge(key_string, key_string, ['node']))

        if self.prism_central_metrics:
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [INFO] Initializing metrics for Prism Central...{PrintColors.RESET}")
            key_strings = [
                "nutanix_count_vg",
                "nutanix_count_vm",
                "nutanix_count_vm_on",
                "nutanix_count_vm_off",
                "nutanix_count_vcpu",
                "nutanix_count_vram_mib",
                "nutanix_count_vdisk",
                "nutanix_count_vdisk_ide",
                "nutanix_count_vdisk_sata",
                "nutanix_count_vdisk_scsi",
                "nutanix_count_vnic",
                "nutanix_count_category",
                "nutanix_count_vm_protected",
                "nutanix_count_vm_protected_compliant",
                "nutanix_count_vm_protected_synced",
                "nutanix_count_ngt_installed",
                "nutanix_count_ngt_enabled"
            ]
            for key_string in key_strings:
                setattr(self, key_string, Gauge(key_string, key_string, ['prism_central']))

        if self.ncm_ssp_metrics:
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [INFO] Initializing metrics for NCM SSP...{PrintColors.RESET}")
            key_strings = [
                "nutanix_ncm_count_applications",
                "nutanix_ncm_count_applications_provisioning",
                "nutanix_ncm_count_applications_running",
                "nutanix_ncm_count_applications_error",
                "nutanix_ncm_count_applications_deleting",
                "nutanix_ncm_count_blueprints",
                "nutanix_ncm_count_runbooks",
                "nutanix_ncm_count_projects",
                "nutanix_ncm_count_marketplace_items"
            ]
            for key_string in key_strings:
                setattr(self, key_string, Gauge(key_string, key_string, ['ncm_ssp']))


    def run_metrics_loop(self):
        """Metrics fetching loop"""
        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Starting metrics loop {PrintColors.RESET}")
        while True:
            self.fetch()
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Waiting for {self.polling_interval_seconds} seconds...{PrintColors.RESET}")
            time.sleep(self.polling_interval_seconds)


    def fetch(self):
        """
        Get metrics from application and refresh Prometheus metrics with
        new values.
        """

        if self.cluster_metrics:
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting clusters metrics{PrintColors.RESET}")
            cluster_uuid, cluster_details = prism_get_cluster(api_server=self.prism,username=self.user,secret=self.pwd,secure=self.prism_secure,api_requests_timeout_seconds=self.api_requests_timeout_seconds, api_requests_retries=self.api_requests_retries, api_sleep_seconds_between_retries=self.api_sleep_seconds_between_retries)
            vm_details = prism_get_vms(api_server=self.prism,username=self.user,secret=self.pwd,secure=self.prism_secure,api_requests_timeout_seconds=self.api_requests_timeout_seconds, api_requests_retries=self.api_requests_retries, api_sleep_seconds_between_retries=self.api_sleep_seconds_between_retries)
            hosts_details = prism_get_hosts(api_server=self.prism,username=self.user,secret=self.pwd,secure=self.prism_secure,api_requests_timeout_seconds=self.api_requests_timeout_seconds, api_requests_retries=self.api_requests_retries, api_sleep_seconds_between_retries=self.api_sleep_seconds_between_retries)
            vg_details = prism_get_volume_groups(api_server=self.prism,username=self.user,secret=self.pwd,secure=self.prism_secure,api_requests_timeout_seconds=self.api_requests_timeout_seconds, api_requests_retries=self.api_requests_retries, api_sleep_seconds_between_retries=self.api_sleep_seconds_between_retries)

            vms_powered_on = [vm for vm in vm_details if vm['power_state'] == "on"]

            for host in hosts_details:
                #populating values for host stats metrics
                for key, value in host['stats'].items():
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_host_stats_{key}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    self.__dict__[key_string].labels(host=host['name']).set(value)
                for key, value in host['usage_stats'].items():
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_host_usage_stats_{key}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    self.__dict__[key_string].labels(host=host['name']).set(value)
                #populating values for host count metrics
                host_vms_list = [vm for vm in vms_powered_on if vm['host_uuid'] == host['uuid']]
                key_string = "nutanix_count_vm"
                self.__dict__[key_string].labels(entity=host['name']).set(len(host_vms_list))
                key_string = "nutanix_count_vcpu"
                self.__dict__[key_string].labels(entity=host['name']).set(sum([(vm['num_vcpus'] * vm['num_cores_per_vcpu']) for vm in host_vms_list]))
                key_string = "nutanix_count_vram_mib"
                self.__dict__[key_string].labels(entity=host['name']).set(sum([vm['memory_mb'] for vm in host_vms_list]))
                key_string = "nutanix_count_vdisk"
                self.__dict__[key_string].labels(entity=host['name']).set(sum([len([vdisk for vdisk in vm['vm_disk_info'] if vdisk['is_cdrom'] is False]) for vm in host_vms_list]))
                key_string = "nutanix_count_vdisk_ide"
                self.__dict__[key_string].labels(entity=host['name']).set(sum([len([vdisk for vdisk in vm['vm_disk_info'] if (vdisk['is_cdrom'] is False) and (vdisk['disk_address']['device_bus'] == 'ide')]) for vm in host_vms_list]))
                key_string = "nutanix_count_vdisk_sata"
                self.__dict__[key_string].labels(entity=host['name']).set(sum([len([vdisk for vdisk in vm['vm_disk_info'] if (vdisk['is_cdrom'] is False) and (vdisk['disk_address']['device_bus'] == 'sata')]) for vm in host_vms_list]))
                key_string = "nutanix_count_vdisk_scsi"
                self.__dict__[key_string].labels(entity=host['name']).set(sum([len([vdisk for vdisk in vm['vm_disk_info'] if (vdisk['is_cdrom'] is False) and (vdisk['disk_address']['device_bus'] == 'scsi')]) for vm in host_vms_list]))
                key_string = "nutanix_count_vnic"
                self.__dict__[key_string].labels(entity=host['name']).set(sum([len(vm['vm_nics']) for vm in host_vms_list]))

            #populating values for cluster stats metrics
            for key, value in cluster_details['stats'].items():
                #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                key_string = f"nutanix_cluster_stats_{key}"
                key_string = key_string.replace(".","_")
                key_string = key_string.replace("-","_")
                self.__dict__[key_string].labels(cluster=cluster_details['name']).set(value)
            for key, value in cluster_details['usage_stats'].items():
                #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                key_string = f"nutanix_cluster_usage_stats_{key}"
                key_string = key_string.replace(".","_")
                key_string = key_string.replace("-","_")
                self.__dict__[key_string].labels(cluster=cluster_details['name']).set(value)

            #populating values for cluster count metrics
            key_string = "nutanix_count_vg"
            self.__dict__[key_string].labels(entity=cluster_details['name']).set(len(vg_details))
            key_string = "nutanix_count_vm"
            self.__dict__[key_string].labels(entity=cluster_details['name']).set(len(vm_details))
            key_string = "nutanix_count_vm_on"
            self.__dict__[key_string].labels(entity=cluster_details['name']).set(len([vm for vm in vm_details if vm['power_state'] == "on"]))
            key_string = "nutanix_count_vm_off"
            self.__dict__[key_string].labels(entity=cluster_details['name']).set(len([vm for vm in vm_details if vm['power_state'] == "off"]))
            key_string = "nutanix_count_vcpu"
            self.__dict__[key_string].labels(entity=cluster_details['name']).set(sum([(vm['num_vcpus'] * vm['num_cores_per_vcpu']) for vm in vm_details]))
            key_string = "nutanix_count_vram_mib"
            self.__dict__[key_string].labels(entity=cluster_details['name']).set(sum([vm['memory_mb'] for vm in vm_details]))
            key_string = "nutanix_count_vdisk"
            self.__dict__[key_string].labels(entity=cluster_details['name']).set(sum([len([vdisk for vdisk in vm['vm_disk_info'] if vdisk['is_cdrom'] is False]) for vm in vm_details]))
            key_string = "nutanix_count_vdisk_ide"
            self.__dict__[key_string].labels(entity=cluster_details['name']).set(sum([len([vdisk for vdisk in vm['vm_disk_info'] if (vdisk['is_cdrom'] is False) and (vdisk['disk_address']['device_bus'] == 'ide')]) for vm in vm_details]))
            key_string = "nutanix_count_vdisk_sata"
            self.__dict__[key_string].labels(entity=cluster_details['name']).set(sum([len([vdisk for vdisk in vm['vm_disk_info'] if (vdisk['is_cdrom'] is False) and (vdisk['disk_address']['device_bus'] == 'sata')]) for vm in vm_details]))
            key_string = "nutanix_count_vdisk_scsi"
            self.__dict__[key_string].labels(entity=cluster_details['name']).set(sum([len([vdisk for vdisk in vm['vm_disk_info'] if (vdisk['is_cdrom'] is False) and (vdisk['disk_address']['device_bus'] == 'scsi')]) for vm in vm_details]))
            key_string = "nutanix_count_vnic"
            self.__dict__[key_string].labels(entity=cluster_details['name']).set(sum([len(vm['vm_nics']) for vm in vm_details]))

            #populating values for other misc info based metrics
            #self.lts.labels(cluster=cluster_details['name']).state(str(cluster_details['is_lts']))
            key_string = "nutanix_cluster"
            labels = {
                'entity': cluster_details['name'],
                'is_lts': str(cluster_details['is_lts']),
                'num_nodes': str(cluster_details['num_nodes']),
                'model_name': str(cluster_details['rackable_units'][0]['model_name']),
                'storage_type': str(cluster_details['storage_type']),
                'version': str(cluster_details['version']),
                'is_nsenabled': str(cluster_details['is_nsenabled']),
                'encrypted': str(cluster_details['encrypted']),
                'timezone': str(cluster_details['timezone']),
                'operation_mode': str(cluster_details['operation_mode']),
                'enable_shadow_clones': str(cluster_details['enable_shadow_clones']),
                'desired_redundancy_factor': str(cluster_details['cluster_redundancy_state']['desired_redundancy_factor']),
                'enable_rebuild_reservation': str(cluster_details['enable_rebuild_reservation']),
                'fault_tolerance_domain_type': str(cluster_details['fault_tolerance_domain_type']),
                'data_in_transit_encryption_dto': str(cluster_details['data_in_transit_encryption_dto']['enabled'])
            }
            self.__dict__[key_string].info(labels)

        if self.vm_list:
            vm_list_array = self.vm_list.split(',')
            for vm in vm_list_array:
                print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting vm metrics for {vm}{PrintColors.RESET}")
                vm_details = prism_get_vm(vm_name=vm,api_server=self.prism,username=self.user,secret=self.pwd,secure=self.prism_secure,api_requests_timeout_seconds=self.api_requests_timeout_seconds, api_requests_retries=self.api_requests_retries, api_sleep_seconds_between_retries=self.api_sleep_seconds_between_retries)
                for key, value in vm_details['stats'].items():
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_vms_stats_{key}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    self.__dict__[key_string].labels(vm=vm_details['vmName']).set(value)
                for key, value in vm_details['usageStats'].items():
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_vms_usage_stats_{key}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    self.__dict__[key_string].labels(vm=vm_details['vmName']).set(value)

        if self.storage_containers_metrics:
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting storage containers metrics{PrintColors.RESET}")
            storage_containers_details = prism_get_storage_containers(api_server=self.prism,username=self.user,secret=self.pwd,secure=self.prism_secure,api_requests_timeout_seconds=self.api_requests_timeout_seconds, api_requests_retries=self.api_requests_retries, api_sleep_seconds_between_retries=self.api_sleep_seconds_between_retries)
            for container in storage_containers_details:
                for key, value in container['stats'].items():
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_storage_container_stats_{key}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    self.__dict__[key_string].labels(storage_container=container['name']).set(value)
                for key, value in container['usage_stats'].items():
                    #making sure we are compliant with the data model (https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
                    key_string = f"nutanix_storage_container_usage_stats_{key}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    self.__dict__[key_string].labels(storage_container=container['name']).set(value)

        if self.ipmi_metrics:
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting IPMI metrics{PrintColors.RESET}")
            if not self.cluster_metrics:
                hosts_details = prism_get_hosts(api_server=self.prism,username=self.user,secret=self.pwd,secure=self.prism_secure,api_requests_timeout_seconds=self.api_requests_timeout_seconds, api_requests_retries=self.api_requests_retries, api_sleep_seconds_between_retries=self.api_sleep_seconds_between_retries)
            for node in hosts_details:
                #* figuring out management module creds
                if self.ipmi_username is not None:
                    ipmi_username = self.ipmi_username
                else:
                    ipmi_username = 'ADMIN'
                if self.ipmi_secret is not None and self.ipmi_secret != 'null':
                    ipmi_secret = self.ipmi_secret
                else:
                    ipmi_secret = node['serial']

                #* getting node name for labels
                node_name = node['name']
                node_name = node_name.replace(".","_")
                node_name = node_name.replace("-","_")

                #* collection power consumption metrics
                power_control = ipmi_get_powercontrol(node['ipmi_address'],secret=ipmi_secret,username=ipmi_username,secure=self.prism_secure)
                key_string = "nutanix_power_consumption_power_consumed_watts"
                self.__dict__[key_string].labels(node=node_name).set(power_control['PowerConsumedWatts'])
                key_string = "nutanix_power_consumption_min_consumed_watts"
                self.__dict__[key_string].labels(node=node_name).set(power_control['PowerMetrics']['MinConsumedWatts'])
                key_string = "nutanix_power_consumption_max_consumed_watts"
                self.__dict__[key_string].labels(node=node_name).set(power_control['PowerMetrics']['MaxConsumedWatts'])
                key_string = "nutanix_power_consumption_average_consumed_watts"
                self.__dict__[key_string].labels(node=node_name).set(power_control['PowerMetrics']['AverageConsumedWatts'])

                #* collection thermal metrics
                thermal = ipmi_get_thermal(node['ipmi_address'],secret=ipmi_secret,username=ipmi_username,secure=self.prism_secure)
                cpu_temps = []
                for temperature in thermal:
                    if re.match(r"CPU\d+ Temp", temperature['Name']) and temperature['ReadingCelsius']:
                        #key_string = "nutanix_thermal_cpu_temp_celsius"
                        #self.__dict__[key_string].labels(node=node_name).set(temperature['ReadingCelsius'])
                        cpu_temps.append(float(temperature['ReadingCelsius']))
                    elif temperature['Name'] == 'PCH Temp' and temperature['ReadingCelsius']:
                        key_string = "nutanix_thermal_pch_temp_celcius"
                        self.__dict__[key_string].labels(node=node_name).set(temperature['ReadingCelsius'])
                    elif temperature['Name'] == 'System Temp' and temperature['ReadingCelsius']:
                        key_string = "nutanix_thermal_system_temp_celcius"
                        self.__dict__[key_string].labels(node=node_name).set(temperature['ReadingCelsius'])
                    elif temperature['Name'] == 'Peripheral Temp' and temperature['ReadingCelsius']:
                        key_string = "nutanix_thermal_peripheral_temp_celcius"
                        self.__dict__[key_string].labels(node=node_name).set(temperature['ReadingCelsius'])
                    elif temperature['Name'] == 'Inlet Temp' and temperature['ReadingCelsius']:
                        key_string = "nutanix_thermal_inlet_temp_celcius"
                        self.__dict__[key_string].labels(node=node_name).set(temperature['ReadingCelsius'])
                if cpu_temps:
                    cpu_temp = sum(cpu_temps) / len(cpu_temps)
                    key_string = "nutanix_thermal_cpu_temp_celsius"
                    self.__dict__[key_string].labels(node=node_name).set(cpu_temp)

        if self.prism_central_metrics:
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting Prism Central metrics{PrintColors.RESET}")

            if ipaddress.ip_address(self.prism):
                try:
                    prism_central_hostname = socket.gethostbyaddr(self.prism)[0]
                except:
                    prism_central_hostname = self.prism
            else:
                prism_central_hostname = self.prism

            length=500
            vm_details=[]

            vm_count = get_total_entities(
                api_server=self.prism,
                username=self.user,
                password=self.pwd,
                entity_type='vm',
                entity_api_root='vms',
                secure=self.prism_secure
            )

            vg_count = get_total_entities(
                api_server=self.prism,
                username=self.user,
                password=self.pwd,
                entity_type='volume_group',
                entity_api_root='volume_groups',
                secure=self.prism_secure
            )

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(
                    get_entities_batch,
                    api_server=self.prism,
                    username=self.user,
                    password=self.pwd,
                    entity_type='vm',
                    entity_api_root='vms',
                    offset= offset,
                    length=length
                    ) for offset in range(0, vm_count, length)]
                for future in as_completed(futures):
                    vms = future.result()
                    vm_details.extend(vms)

            #* volume groups metrics
            key_string = "nutanix_count_vg"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(vg_count)

            #* general vm count metrics
            key_string = "nutanix_count_vm"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(len(vm_details))
            key_string = "nutanix_count_vm_on"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(len([vm for vm in vm_details if vm['status']['resources']['power_state'] == "ON"]))
            key_string = "nutanix_count_vm_off"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(len([vm for vm in vm_details if vm['status']['resources']['power_state'] == "OFF"]))
            key_string = "nutanix_count_vcpu"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(sum([(vm['status']['resources']['num_sockets'] * vm['status']['resources']['num_threads_per_core']) for vm in vm_details]))
            key_string = "nutanix_count_vram_mib"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(sum([vm['status']['resources']['memory_size_mib'] for vm in vm_details]))
            key_string = "nutanix_count_vdisk"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(sum([len([vdisk for vdisk in vm['status']['resources']['disk_list'] if vdisk['device_properties']['device_type'] == 'DISK']) for vm in vm_details]))
            key_string = "nutanix_count_vdisk_ide"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(sum([len([vdisk for vdisk in vm['status']['resources']['disk_list'] if (vdisk['device_properties']['device_type'] == 'DISK') and (vdisk['device_properties']['disk_address']['adapter_type'] == 'IDE')]) for vm in vm_details]))
            key_string = "nutanix_count_vdisk_sata"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(sum([len([vdisk for vdisk in vm['status']['resources']['disk_list'] if (vdisk['device_properties']['device_type'] == 'DISK') and (vdisk['device_properties']['disk_address']['adapter_type'] == 'SATA')]) for vm in vm_details]))
            key_string = "nutanix_count_vdisk_scsi"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(sum([len([vdisk for vdisk in vm['status']['resources']['disk_list'] if (vdisk['device_properties']['device_type'] == 'DISK') and (vdisk['device_properties']['disk_address']['adapter_type'] == 'SCSI')]) for vm in vm_details]))
            key_string = "nutanix_count_vnic"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(sum([len([vnic for vnic in vm['status']['resources']['nic_list']]) for vm in vm_details]))

            #* categories count metrics
            #todo: keep count of entities for each category
            key_string = "nutanix_count_category"

            #* DR protected vm count metrics
            key_string = "nutanix_count_vm_protected"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(len([vm for vm in vm_details if vm['status']['resources']['protection_type'] == "RULE_PROTECTED"]))
            key_string = "nutanix_count_vm_protected_synced"
            protected_vms_list = [vm for vm in vm_details if vm.get('status', {}).get('resources', {}).get('protection_policy_state') is not None]
            protected_vms_with_status_list = [vm for vm in protected_vms_list if vm.get('status', {}).get('resources', {}).get('protection_policy_state').get('policy_info').get('replication_status') is not None]
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(len([protected_vm for protected_vm in protected_vms_with_status_list if protected_vm['status']['resources']['protection_policy_state']['policy_info']['replication_status'] == "SYNCED"]))
            key_string = "nutanix_count_vm_protected_compliant"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(len([protected_vm for protected_vm in protected_vms_list if protected_vm['status']['resources']['protection_policy_state']['compliance_status'] == "COMPLIANT"]))

            #* NGT vm count metrics
            ngt_vms_list = [vm for vm in vm_details if vm.get('status', {}).get('resources', {}).get('guest_tools') is not None]
            key_string = "nutanix_count_ngt_installed"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(len([ngt_vm for ngt_vm in ngt_vms_list if ngt_vm['status']['resources']['guest_tools']['nutanix_guest_tools']['ngt_state'] == "INSTALLED"]))
            key_string = "nutanix_count_ngt_enabled"
            self.__dict__[key_string].labels(prism_central=prism_central_hostname).set(len([ngt_vm for ngt_vm in ngt_vms_list if ngt_vm['status']['resources']['guest_tools']['nutanix_guest_tools']['is_reachable'] is True]))

        if self.ncm_ssp_metrics:
            #print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting NCM SSP metrics{PrintColors.RESET}")

            if ipaddress.ip_address(self.prism):
                try:
                    ncm_ssp_hostname = socket.gethostbyaddr(self.prism)[0]
                except:
                    ncm_ssp_hostname = self.prism
            else:
                ncm_ssp_hostname = self.prism

            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting NCM SSP apps metrics{PrintColors.RESET}")
            ncm_applications = get_total_entities(
                api_server=self.prism,
                username=self.user,
                password=self.pwd,
                entity_type='app',
                entity_api_root='apps',
                fiql_filter="(name!=Infrastructure;name!=Self%20Service);_state==running,_state==deleting,_state==error,_state==provisioning",
                secure=self.prism_secure
            )

            ncm_applications_running = get_total_entities(
                api_server=self.prism,
                username=self.user,
                password=self.pwd,
                entity_type='app',
                entity_api_root='apps',
                fiql_filter="_state==running;(name!=Infrastructure;name!=Self%20Service)",
                secure=self.prism_secure
            )

            ncm_applications_provisioning = get_total_entities(
                api_server=self.prism,
                username=self.user,
                password=self.pwd,
                entity_type='app',
                entity_api_root='apps',
                fiql_filter="_state==provisioning;(name!=Infrastructure;name!=Self%20Service)",
                secure=self.prism_secure
            )

            ncm_applications_error = get_total_entities(
                api_server=self.prism,
                username=self.user,
                password=self.pwd,
                entity_type='app',
                entity_api_root='apps',
                fiql_filter="_state==error;(name!=Infrastructure;name!=Self%20Service)",
                secure=self.prism_secure
            )

            ncm_applications_deleting = get_total_entities(
                api_server=self.prism,
                username=self.user,
                password=self.pwd,
                entity_type='app',
                entity_api_root='apps',
                fiql_filter="_state==deleting;(name!=Infrastructure;name!=Self%20Service)",
                secure=self.prism_secure
            )

            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting NCM SSP projects metrics{PrintColors.RESET}")
            ncm_projects_count = get_total_entities(
                api_server=self.prism,
                username=self.user,
                password=self.pwd,
                entity_type='project',
                entity_api_root='projects',
                secure=self.prism_secure
            )
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting NCM SSP marketplace metrics{PrintColors.RESET}")
            ncm_marketplace_items_count = get_total_entities(
                api_server=self.prism,
                username=self.user,
                password=self.pwd,
                entity_type='marketplace_item',
                entity_api_root='marketplace_items',
                secure=self.prism_secure
            )
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting NCM SSP blueprints metrics{PrintColors.RESET}")
            ncm_blueprints_count = get_total_entities(
                api_server=self.prism,
                username=self.user,
                password=self.pwd,
                entity_type='blueprint',
                entity_api_root='blueprints',
                secure=self.prism_secure
            )
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting NCM SSP runbooks metrics{PrintColors.RESET}")
            ncm_runbooks_count = get_total_entities(
                api_server=self.prism,
                username=self.user,
                password=self.pwd,
                entity_type='runbook',
                entity_api_root='runbooks',
                secure=self.prism_secure
            )

            key_string = "nutanix_ncm_count_applications"
            self.__dict__[key_string].labels(ncm_ssp=ncm_ssp_hostname).set(ncm_applications)
            key_string = "nutanix_ncm_count_applications_provisioning"
            self.__dict__[key_string].labels(ncm_ssp=ncm_ssp_hostname).set(ncm_applications_provisioning)
            key_string = "nutanix_ncm_count_applications_running"
            self.__dict__[key_string].labels(ncm_ssp=ncm_ssp_hostname).set(ncm_applications_running)
            key_string = "nutanix_ncm_count_applications_error"
            self.__dict__[key_string].labels(ncm_ssp=ncm_ssp_hostname).set(ncm_applications_error)
            key_string = "nutanix_ncm_count_applications_deleting"
            self.__dict__[key_string].labels(ncm_ssp=ncm_ssp_hostname).set(ncm_applications_deleting)
            key_string = "nutanix_ncm_count_blueprints"
            self.__dict__[key_string].labels(ncm_ssp=ncm_ssp_hostname).set(ncm_blueprints_count)
            key_string = "nutanix_ncm_count_runbooks"
            self.__dict__[key_string].labels(ncm_ssp=ncm_ssp_hostname).set(ncm_runbooks_count)
            key_string = "nutanix_ncm_count_marketplace_items"
            self.__dict__[key_string].labels(ncm_ssp=ncm_ssp_hostname).set(ncm_marketplace_items_count)
            key_string = "nutanix_ncm_count_projects"
            self.__dict__[key_string].labels(ncm_ssp=ncm_ssp_hostname).set(ncm_projects_count)


class NutanixMetricsRedfish:
    """
    Representation of Prometheus metrics and loop to fetch and transform
    application metrics into Prometheus metrics.
    """
    def __init__(self,
                 ipmi_config,
                 polling_interval_seconds=30, api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,
                 ipmi_secure=False,ipmi_additional_metrics=False,
                 ):
        self.ipmi_config = ipmi_config
        self.polling_interval_seconds = polling_interval_seconds
        self.api_requests_timeout_seconds = api_requests_timeout_seconds
        self.api_requests_retries = api_requests_retries
        self.api_sleep_seconds_between_retries = api_sleep_seconds_between_retries
        self.ipmi_secure = ipmi_secure
        self.ipmi_additional_metrics = ipmi_additional_metrics

        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [INFO] Initializing metrics for IPMI adapters...{PrintColors.RESET}")
        key_strings = [
            "nutanix_power_consumption_power_consumed_watts",
            "nutanix_power_consumption_min_consumed_watts",
            "nutanix_power_consumption_max_consumed_watts",
            "nutanix_power_consumption_average_consumed_watts",
            "nutanix_thermal_cpu_temp_celsius",
            "nutanix_thermal_pch_temp_celcius",
            "nutanix_thermal_system_temp_celcius",
            "nutanix_thermal_peripheral_temp_celcius",
            "nutanix_thermal_inlet_temp_celcius",
            "nutanix_power_state",
            "nutanix_cpu_utilization",
            "nutanix_memory_utilization"
        ]
        for key_string in key_strings:
            setattr(self, key_string, Gauge(key_string, key_string, ['ipmi']))


    def run_metrics_loop(self):
        """Metrics fetching loop"""
        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Starting metrics loop {PrintColors.RESET}")
        while True:
            self.fetch()
            print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Waiting for {self.polling_interval_seconds} seconds...{PrintColors.RESET}")
            time.sleep(self.polling_interval_seconds)

    def process_redfish_entity(self,ipmi_entity):
        """Retrieves metrics from a single IPMI entity and updates Prometheus metrics."""
        ipmi = ipmi_entity['ip']
        ipmi_name = ipmi_entity['name']
        ipmi_username = ipmi_entity['username']
        ipmi_secret = ipmi_entity['password']

        #* collection power consumption metrics
        power_control = ipmi_get_powercontrol(ipmi,secret=ipmi_secret,username=ipmi_username,secure=self.ipmi_secure)
        key_string = "nutanix_power_consumption_power_consumed_watts"
        power = float(power_control.get('PowerConsumedWatts', 0))
        self.__dict__[key_string].labels(ipmi=ipmi_name).set(power)

        key_string = "nutanix_power_consumption_min_consumed_watts"
        power = float(power_control.get('PowerMetrics', {}).get('MinConsumedWatts', 0))
        self.__dict__[key_string].labels(ipmi=ipmi_name).set(power_control['PowerMetrics']['MinConsumedWatts'])

        key_string = "nutanix_power_consumption_max_consumed_watts"
        power = float(power_control.get('PowerMetrics', {}).get('MaxConsumedWatts', 0))
        self.__dict__[key_string].labels(ipmi=ipmi_name).set(power_control['PowerMetrics']['MaxConsumedWatts'])

        key_string = "nutanix_power_consumption_average_consumed_watts"
        power = float(power_control.get('PowerMetrics', {}).get('AverageConsumedWatts', 0))
        self.__dict__[key_string].labels(ipmi=ipmi_name).set(power_control['PowerMetrics']['AverageConsumedWatts'])

        #* collection thermal metrics
        thermal = ipmi_get_thermal(ipmi,secret=ipmi_secret,username=ipmi_username,secure=self.ipmi_secure)
        cpu_temps = []
        for temperature in thermal:
            #print(f"{ipmi_entity['name']}: {type(temperature['Name'])}: {type(temperature['ReadingCelsius'])}")
            if temperature['ReadingCelsius'] is None:
                temp = 0
            else:
                try:
                    temp = float(temperature.get('ReadingCelsius', 0))
                except TypeError as e:
                    print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] TypeError: {e} for {ipmi_entity['name']} when retrieving {temperature['ReadingCelsius']} for {temperature['Name']}. Setting value to 0. {PrintColors.RESET}")
                    temp = 0
            if re.match(r"CPU\d+ Temp", temperature['Name']):
                cpu_temps.append(temp)
            elif temperature['Name'] == 'PCH Temp':
                key_string = "nutanix_thermal_pch_temp_celcius"
                self.__dict__[key_string].labels(ipmi=ipmi_name).set(temp)
            elif temperature['Name'] == 'System Temp':
                key_string = "nutanix_thermal_system_temp_celcius"
                self.__dict__[key_string].labels(ipmi=ipmi_name).set(temp)
            elif temperature['Name'] == 'Peripheral Temp':
                key_string = "nutanix_thermal_peripheral_temp_celcius"
                self.__dict__[key_string].labels(ipmi=ipmi_name).set(temp)
            elif temperature['Name'] == 'Inlet Temp':
                key_string = "nutanix_thermal_inlet_temp_celcius"
                self.__dict__[key_string].labels(ipmi=ipmi_name).set(temp)
        if cpu_temps:
            cpu_temp = sum(cpu_temps) / len(cpu_temps)
            key_string = "nutanix_thermal_cpu_temp_celsius"
            self.__dict__[key_string].labels(ipmi=ipmi_name).set(cpu_temp)

        # * collection additional metrics based on env variable
        if self.ipmi_additional_metrics is not False:
            #* collection power state
            power_state_str = ipmi_get_power_state(ipmi, secret=ipmi_secret, username=ipmi_username, secure=self.ipmi_secure)
            key_string = "nutanix_power_state"
            power_state = 1 if power_state_str == 'On' else 0
            self.__dict__[key_string].labels(ipmi=ipmi_name).set(power_state)

            #* collection cpu util
            cpu_util = ipmi_get_cpu_utilization(ipmi, secret=ipmi_secret, username=ipmi_username, secure=self.ipmi_secure)
            key_string = "nutanix_cpu_utilization"
            self.__dict__[key_string].labels(ipmi=ipmi_name).set(cpu_util)

            #* collection mem util
            mem_util = ipmi_get_memory_utilization(ipmi, secret=ipmi_secret, username=ipmi_username, secure=self.ipmi_secure)
            key_string = "nutanix_memory_utilization"
            self.__dict__[key_string].labels(ipmi=ipmi_name).set(mem_util)

    def fetch(self):
        """
        Get metrics from application and refresh Prometheus metrics with
        new values.
        """

        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Collecting IPMI metrics{PrintColors.RESET}")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.process_redfish_entity,ipmi_entity=ipmi_entity) for ipmi_entity in self.ipmi_config]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] A task failed with error: {e} {type(e)} {PrintColors.RESET}")
                traceback.print_exc()
#endregion #*CLASS


#region #*FUNCTIONS
def process_request(url, method, user, password, headers, api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15, payload=None, secure=False):
    """
    Processes a web request and handles result appropriately with retries.
    Returns the content of the web request if successfull.
    """
    if payload is not None:
        payload = json.dumps(payload)

    #configuring web request behavior
    timeout = api_requests_timeout_seconds
    retries = api_requests_retries
    sleep_between_retries = api_sleep_seconds_between_retries

    while retries > 0:
        try:

            if method == 'GET':
                #print("secure is {}".format(secure))
                response = requests.get(
                    url,
                    headers=headers,
                    auth=(user, password),
                    verify=secure,
                    timeout=timeout
                )
            elif method == 'POST':
                response = requests.post(
                    url,
                    headers=headers,
                    data=payload,
                    auth=(user, password),
                    verify=secure,
                    timeout=timeout
                )
            elif method == 'PUT':
                response = requests.put(
                    url,
                    headers=headers,
                    data=payload,
                    auth=(user, password),
                    verify=secure,
                    timeout=timeout
                )
            elif method == 'PATCH':
                response = requests.patch(
                    url,
                    headers=headers,
                    data=payload,
                    auth=(user, password),
                    verify=secure,
                    timeout=timeout
                )
            elif method == 'DELETE':
                response = requests.delete(
                    url,
                    headers=headers,
                    data=payload,
                    auth=(user, password),
                    verify=secure,
                    timeout=timeout
                )

        except requests.exceptions.HTTPError:
            print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Http Error! Status code: {response.status_code}{PrintColors.RESET}")
            print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {response.reason}{PrintColors.RESET}")
            print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {response.text}{PrintColors.RESET}")
            print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {response.elapsed}{PrintColors.RESET}")
            print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {response.headers}{PrintColors.RESET}")
            if payload is not None:
                print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] payload: {payload}{PrintColors.RESET}")
            print(json.dumps(
                json.loads(response.content),
                indent=4
            ))
            error_message = f"HTTPError {url} {response.status_code} {response.reason} {response.text}"
            raise Exception(error_message)
        except requests.exceptions.ConnectionError as error_code:
            if retries == 1:
                error_message = f"ConnectionError {url} {type(error_code).__name__} {str(error_code)}"
                print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] ConnectionError {url} {type(error_code).__name__} {str(error_code)} {PrintColors.RESET}")
                raise Exception(error_message)
            else:
                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {url} {type(error_code).__name__} {str(error_code)} {PrintColors.RESET}")
                time.sleep(sleep_between_retries)
                retries -= 1
                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {url} Retries left: {retries}{PrintColors.RESET}")
                continue
        except requests.exceptions.Timeout as error_code:
            if retries == 1:
                error_message = f"Timeout {url} {type(error_code).__name__} {str(error_code)}"
                print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Timeout {url} {type(error_code).__name__} {str(error_code)} {PrintColors.RESET}")
                raise Exception(error_message)
            else:
                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {url} {type(error_code).__name__} {str(error_code)} {PrintColors.RESET}")
                time.sleep(sleep_between_retries)
                retries -= 1
                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {url} Retries left: {retries}{PrintColors.RESET}")
                continue
        except requests.exceptions.RequestException as error_code:
            print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] {url} {response.status_code} {PrintColors.RESET}")
            error_message = f"{url} {response.status_code}"
            raise Exception(error_message)
        break

    if response.ok:
        return response
    if response.status_code == 401:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] {url} {response.status_code} {response.reason} {PrintColors.RESET}")
        error_message = f"{url} {response.status_code} {response.reason}"
        raise Exception(error_message)
    elif response.status_code == 500:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] {url} {response.status_code} {response.reason} {response.text} {PrintColors.RESET}")
        error_message = f"{url} {response.status_code} {response.reason} {response.text}"
        raise Exception(error_message)
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [ERROR] Request failed! Status code: {response.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [ERROR] reason: {response.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [ERROR] text: {response.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [ERROR] raise_for_status: {response.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [ERROR] elapsed: {response.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [ERROR] headers: {response.headers}{PrintColors.RESET}")
        if payload is not None:
            print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [ERROR] payload: {payload}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(response.content),
            indent=4
        ))
        error_message = f"{url} {response.status_code} {response.reason} {response.text}"
        raise Exception(error_message)


def prism_get_cluster(api_server,username,secret,api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,secure=False):
    """Retrieves data from the Prism Element v2 REST API endpoint /clusters.

    Args:
        api_server: The IP or FQDN of Prism.
        username: The Prism user name.
        secret: The Prism user name password.
        
    Returns:
        Cluster uuid as cluster_uuid. Cluster details as cluster_details
    """

    #region prepare the api call
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }
    api_server_port = int(os.getenv("APP_PORT", "9440"))
    api_server_endpoint = "/PrismGateway/services/rest/v2.0/clusters/"
    url = "https://{}:{}{}".format(
        api_server,
        api_server_port,
        api_server_endpoint
    )
    method = "GET"
    #endregion

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Making a {method} API call to {url} with secure set to {secure}{PrintColors.RESET}")
    resp = process_request(url,method,username,secret,headers,secure=secure,api_requests_timeout_seconds=api_requests_timeout_seconds, api_requests_retries=api_requests_retries, api_sleep_seconds_between_retries=api_sleep_seconds_between_retries)

    # deal with the result/response
    if resp.ok:
        json_resp = json.loads(resp.content)
        cluster_uuid = json_resp['entities'][0]['uuid']
        cluster_details = json_resp['entities'][0]
        return cluster_uuid, cluster_details
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Request failed! Status code: {resp.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {resp.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {resp.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] raise_for_status: {resp.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {resp.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {resp.headers}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(resp.content),
            indent=4
        ))
        error_message = f"{url} {resp.status_code} {resp.reason} {resp.text}"
        raise Exception(error_message)


def prism_get_vm(vm_name,api_server,username,secret,api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,secure=False):
    """Retrieves data from the Prism Element v2 REST API endpoint /vms using a vm name as a filter criteria.

    Args:
        vm_name: The VM name to search for.
        api_server: The IP or FQDN of Prism.
        username: The Prism user name.
        secret: The Prism user name password.
        
    Returns:
        VM details as vm_details
    """

    #region prepare the api call
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }
    api_server_port = int(os.getenv("APP_PORT", "9440"))
    api_server_endpoint = f"/PrismGateway/services/rest/v1/vms/?filterCriteria=vm_name%3D%3D{vm_name}"
    url = "https://{}:{}{}".format(
        api_server,
        api_server_port,
        api_server_endpoint
    )
    method = "GET"
    #endregion

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Making a {method} API call to {url} with secure set to {secure}{PrintColors.RESET}")
    resp = process_request(url,method,username,secret,headers,secure=secure,api_requests_timeout_seconds=api_requests_timeout_seconds, api_requests_retries=api_requests_retries, api_sleep_seconds_between_retries=api_sleep_seconds_between_retries)

    # deal with the result/response
    if resp.ok:
        json_resp = json.loads(resp.content)
        vm_details = json_resp['entities']
        if len(vm_details) > 0:
            return vm_details[0]
        else:
            print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d_%H:%M:%S')} [ERROR] Specified VM {vm_name} does not exist on Prism Element {api_server}...{PrintColors.RESET}")
            exit(1)
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Request failed! Status code: {resp.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {resp.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {resp.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] raise_for_status: {resp.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {resp.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {resp.headers}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(resp.content),
            indent=4
        ))
        error_message = f"{url} {resp.status_code} {resp.reason} {resp.text}"
        raise Exception(error_message)


def prism_get_storage_containers(api_server,username,secret,api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,secure=False):
    """Retrieves data from the Prism Element v2 REST API endpoint /storage_containers.

    Args:
        api_server: The IP or FQDN of Prism.
        username: The Prism user name.
        secret: The Prism user name password.
        
    Returns:
        Storage containers details as storage_containers_details
    """

    #region prepare the api call
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }
    api_server_port = int(os.getenv("APP_PORT", "9440"))
    api_server_endpoint = "/PrismGateway/services/rest/v2.0/storage_containers/"
    url = "https://{}:{}{}".format(
        api_server,
        api_server_port,
        api_server_endpoint
    )
    method = "GET"
    #endregion

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Making a {method} API call to {url} with secure set to {secure}{PrintColors.RESET}")
    resp = process_request(url,method,username,secret,headers,secure=secure,api_requests_timeout_seconds=api_requests_timeout_seconds, api_requests_retries=api_requests_retries, api_sleep_seconds_between_retries=api_sleep_seconds_between_retries)

    # deal with the result/response
    if resp.ok:
        json_resp = json.loads(resp.content)
        storage_containers_details = json_resp['entities']
        return storage_containers_details
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Request failed! Status code: {resp.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {resp.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {resp.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] raise_for_status: {resp.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {resp.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {resp.headers}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(resp.content),
            indent=4
        ))
        error_message = f"{url} {resp.status_code} {resp.reason} {resp.text}"
        raise Exception(error_message)


def prism_get_hosts(api_server,username,secret,api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,secure=False):
    """Retrieves data from the Prism Element v2 REST API endpoint /hosts.

    Args:
        api_server: The IP or FQDN of Prism.
        username: The Prism user name.
        secret: The Prism user name password.
        
    Returns:
        Hosts details as hosts_details
    """

    #region prepare the api call
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }
    api_server_port = int(os.getenv("APP_PORT", "9440"))
    api_server_endpoint = "/PrismGateway/services/rest/v2.0/hosts/"
    url = "https://{}:{}{}".format(
        api_server,
        api_server_port,
        api_server_endpoint
    )
    method = "GET"
    #endregion

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Making a {method} API call to {url} with secure set to {secure}{PrintColors.RESET}")
    resp = process_request(url,method,username,secret,headers,secure=secure,api_requests_timeout_seconds=api_requests_timeout_seconds, api_requests_retries=api_requests_retries, api_sleep_seconds_between_retries=api_sleep_seconds_between_retries)

    # deal with the result/response
    if resp.ok:
        json_resp = json.loads(resp.content)
        hosts_details = json_resp['entities']
        return hosts_details
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Request failed! Status code: {resp.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {resp.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {resp.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] raise_for_status: {resp.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {resp.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {resp.headers}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(resp.content),
            indent=4
        ))
        error_message = f"{url} {resp.status_code} {resp.reason} {resp.text}"
        raise Exception(error_message)


def prism_get_volume_groups(api_server,username,secret,api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,secure=False):
    """Retrieves data from the Prism Element v2 REST API endpoint /volume_groups.

    Args:
        api_server: The IP or FQDN of Prism.
        username: The Prism user name.
        secret: The Prism user name password.
        
    Returns:
        VG details as vg_details
    """

    #region prepare the api call
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }
    api_server_port = int(os.getenv("APP_PORT", "9440"))
    api_server_endpoint = "/PrismGateway/services/rest/v2.0/volume_groups/"
    url = "https://{}:{}{}".format(
        api_server,
        api_server_port,
        api_server_endpoint
    )
    method = "GET"
    #endregion

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Making a {method} API call to {url} with secure set to {secure}{PrintColors.RESET}")
    resp = process_request(url,method,username,secret,headers,secure=secure,api_requests_timeout_seconds=api_requests_timeout_seconds, api_requests_retries=api_requests_retries, api_sleep_seconds_between_retries=api_sleep_seconds_between_retries)

    # deal with the result/response
    if resp.ok:
        json_resp = json.loads(resp.content)
        vg_details = json_resp['entities']
        return vg_details
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Request failed! Status code: {resp.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {resp.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {resp.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] raise_for_status: {resp.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {resp.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {resp.headers}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(resp.content),
            indent=4
        ))
        error_message = f"{url} {resp.status_code} {resp.reason} {resp.text}"
        raise Exception(error_message)


def prism_get_vms(api_server,username,secret,api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,secure=False):
    """Retrieves data from the Prism Element v2 REST API endpoint /hosts.

    Args:
        api_server: The IP or FQDN of Prism.
        username: The Prism user name.
        secret: The Prism user name password.
        
    Returns:
        Hosts details as vms_details
    """

    #region prepare the api call
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }
    api_server_port = int(os.getenv("APP_PORT", "9440"))
    api_server_endpoint = "/PrismGateway/services/rest/v2.0/vms/?include_vm_disk_config=true&include_vm_nic_config=true"
    url = "https://{}:{}{}".format(
        api_server,
        api_server_port,
        api_server_endpoint
    )
    method = "GET"
    #endregion

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Making a {method} API call to {url} with secure set to {secure}{PrintColors.RESET}")
    resp = process_request(url,method,username,secret,headers,secure=secure,api_requests_timeout_seconds=api_requests_timeout_seconds, api_requests_retries=api_requests_retries, api_sleep_seconds_between_retries=api_sleep_seconds_between_retries)

    # deal with the result/response
    if resp.ok:
        json_resp = json.loads(resp.content)
        vms_details = json_resp['entities']
        return vms_details
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Request failed! Status code: {resp.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {resp.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {resp.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] raise_for_status: {resp.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {resp.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {resp.headers}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(resp.content),
            indent=4
        ))
        error_message = f"{url} {resp.status_code} {resp.reason} {resp.text}"
        raise Exception(error_message)


def ipmi_get_powercontrol(api_server,secret,username='ADMIN',api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,secure=False):
    """Retrieves data from the IPMI RedFisk REST API endpoint /PowerControl.

    Args:
        api_server: The IP or FQDN of the IPMI.
        username: The IPMI user name (defaults to ADMIN).
        secret: The IPMI user name password.
        
    Returns:
        PowerControl metrics object as power_control
    """

    #region prepare the api call
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }
    api_server_endpoint = "/redfish/v1/Chassis/1/Power"
    url = "https://{}{}".format(
        api_server,
        api_server_endpoint
    )
    method = "GET"
    #endregion

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Making a {method} API call to {url} with secure set to {secure}{PrintColors.RESET}")
    resp = process_request(url,method,username,secret,headers,secure=secure,api_requests_timeout_seconds=api_requests_timeout_seconds, api_requests_retries=api_requests_retries, api_sleep_seconds_between_retries=api_sleep_seconds_between_retries)

    # deal with the result/response
    if resp.ok:
        json_resp = json.loads(resp.content)
        power_control = json_resp['PowerControl'][0]
        return power_control
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Request failed! Status code: {resp.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {resp.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {resp.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] raise_for_status: {resp.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {resp.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {resp.headers}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(resp.content),
            indent=4
        ))
        raise

def ipmi_get_thermal(api_server,secret,username='ADMIN',api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,secure=False):
    """Retrieves data from the IPMI RedFisk REST API endpoint /Thermal.

    Args:
        api_server: The IP or FQDN of the IPMI.
        username: The IPMI user name (defaults to ADMIN).
        secret: The IPMI user name password.
        
    Returns:
        Thermal metrics object as thermal
    """

    #region prepare the api call
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }
    api_server_endpoint = "/redfish/v1/Chassis/1/Thermal"
    url = "https://{}{}".format(
        api_server,
        api_server_endpoint
    )
    method = "GET"
    #endregion

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Making a {method} API call to {url} with secure set to {secure}{PrintColors.RESET}")
    resp = process_request(url,method,username,secret,headers,secure=secure,api_requests_timeout_seconds=api_requests_timeout_seconds, api_requests_retries=api_requests_retries, api_sleep_seconds_between_retries=api_sleep_seconds_between_retries)

    # deal with the result/response
    if resp.ok:
        json_resp = json.loads(resp.content)
        thermal = json_resp['Temperatures']
        return thermal
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Request failed! Status code: {resp.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {resp.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {resp.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] raise_for_status: {resp.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {resp.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {resp.headers}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(resp.content),
            indent=4
        ))
        raise

#todo: add get cpu and memory metrics from redfish
def ipmi_get_cpu_utilization(api_server,secret,username='ADMIN',api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,secure=False):
    """Retrieves data from the IPMI RedFisk REST API endpoint /Systems.

    Args:
        api_server: The IP or FQDN of the IPMI.
        username: The IPMI user name (defaults to ADMIN).
        secret: The IPMI user name password.
        
    Returns:
        CPU utilization metrics object as cpu_utilization
    """

    #region prepare the api call
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }
    api_server_endpoint = "/redfish/v1/Systems/1/ProcessorSummary/ProcessorMetrics"
    url = "https://{}{}".format(
        api_server,
        api_server_endpoint
    )
    method = "GET"
    #endregion

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Making a {method} API call to {url} with secure set to {secure}{PrintColors.RESET}")
    resp = process_request(url,method,username,secret,headers,secure=secure,api_requests_timeout_seconds=api_requests_timeout_seconds, api_requests_retries=api_requests_retries, api_sleep_seconds_between_retries=api_sleep_seconds_between_retries)

    # deal with the result/response
    if resp.ok:
        json_resp = json.loads(resp.content)
        cpu_utilization = json_resp['BandwidthPercent']
        return cpu_utilization
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Request failed! Status code: {resp.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {resp.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {resp.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] raise_for_status: {resp.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {resp.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {resp.headers}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(resp.content),
            indent=4
        ))
        raise

def ipmi_get_memory_utilization(api_server,secret,username='ADMIN',api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,secure=False):
    """Retrieves data from the IPMI RedFisk REST API endpoint /Systems.

    Args:
        api_server: The IP or FQDN of the IPMI.
        username: The IPMI user name (defaults to ADMIN).
        secret: The IPMI user name password.
        
    Returns:
        Memory utilization metrics object as memory_utilization
    """

    #region prepare the api call
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }
    api_server_endpoint = "/redfish/v1/Systems/1/MemorySummary/MemoryMetrics"
    url = "https://{}{}".format(
        api_server,
        api_server_endpoint
    )
    method = "GET"
    #endregion

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Making a {method} API call to {url} with secure set to {secure}{PrintColors.RESET}")
    resp = process_request(url,method,username,secret,headers,secure=secure,api_requests_timeout_seconds=api_requests_timeout_seconds, api_requests_retries=api_requests_retries, api_sleep_seconds_between_retries=api_sleep_seconds_between_retries)

    # deal with the result/response
    if resp.ok:
        json_resp = json.loads(resp.content)
        memory_utilization = json_resp['BandwidthPercent']
        return memory_utilization
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Request failed! Status code: {resp.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {resp.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {resp.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] raise_for_status: {resp.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {resp.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {resp.headers}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(resp.content),
            indent=4
        ))
        raise

def ipmi_get_power_state(api_server,secret,username='ADMIN',api_requests_timeout_seconds=30, api_requests_retries=5, api_sleep_seconds_between_retries=15,secure=False):
    """Retrieves data from the IPMI RedFisk REST API endpoint /Systems.

    Args:
        api_server: The IP or FQDN of the IPMI.
        username: The IPMI user name (defaults to ADMIN).
        secret: The IPMI user name password.
        
    Returns:
        Power state metrics object as power_state
    """

    #region prepare the api call
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }
    api_server_endpoint = "/redfish/v1/Systems/1"
    url = "https://{}{}".format(
        api_server,
        api_server_endpoint
    )
    method = "GET"
    #endregion

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Making a {method} API call to {url} with secure set to {secure}{PrintColors.RESET}")
    resp = process_request(url,method,username,secret,headers,secure=secure,api_requests_timeout_seconds=api_requests_timeout_seconds, api_requests_retries=api_requests_retries, api_sleep_seconds_between_retries=api_sleep_seconds_between_retries)

    # deal with the result/response
    if resp.ok:
        json_resp = json.loads(resp.content)
        power_state = json_resp['PowerState']
        return power_state
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Request failed! Status code: {resp.status_code}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] reason: {resp.reason}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] text: {resp.text}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] raise_for_status: {resp.raise_for_status()}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] elapsed: {resp.elapsed}{PrintColors.RESET}")
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] headers: {resp.headers}{PrintColors.RESET}")
        print(json.dumps(
            json.loads(resp.content),
            indent=4
        ))
        raise
#endtodo: get cpu and memory metrics from redfish

def get_total_entities(api_server, username, password, entity_type, entity_api_root, fiql_filter=None, secure=False):

    """Retrieve the total number of entities from Prism Central.

    Args:
        api_server: The IP or FQDN of Prism.
        username: The Prism user name.
        password: The Prism user name password.
        entity_type: kind (type) of entity as referenced in the entity json object
        entity_api_root: v3 apis root for this entity type. for example. for projects the list api is ".../api/nutanix/v3/projects/list".
                         the entity api root here is "projects"
        secure: boolean to verify or not the api server's certificate (True/False)
        
    Returns:
        total number of entities as integer.
    """

    url = f'https://{api_server}:9440/api/nutanix/v3/{entity_api_root}/list'
    headers = {'Content-Type': 'application/json'}
    payload = {'kind': entity_type, 'length': 1, 'offset': 0}
    if fiql_filter:
        payload["filter"] = fiql_filter

    try:
        response = requests.post(
            url=url,
            headers=headers,
            auth=(username, password),
            json=payload,
            verify=secure,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get('metadata', {}).get('total_matches', 0)
    except requests.exceptions.RequestException:
        return 0


def get_entities_batch(api_server, username, password, offset, entity_type, entity_api_root, length=100, fiql_filter=None, secure=False):

    """Retrieve the list of entities from Prism Central.

    Args:
        api_server: The IP or FQDN of Prism.
        username: The Prism user name.
        password: The Prism user name password.
        offset: Offset on object count.
        length: Page length (defaults to 100).
        entity_type: kind (type) of entity as referenced in the entity json object
        entity_api_root: v3 apis root for this entity type. for example. for projects the list api is ".../api/nutanix/v3/projects/list".
                         the entity api root here is "projects"
        secure: boolean to verify or not the api server's certificate (True/False)
        
    Returns:
        An array of entities (entities part of the json response).
    """

    url = f'https://{api_server}:9440/api/nutanix/v3/{entity_api_root}/list'
    headers = {'Content-Type': 'application/json'}
    payload = {'kind': entity_type, 'length': length, 'offset': offset}
    if fiql_filter:
        payload["filter"] = fiql_filter

    try:
        response = requests.post(
            url=url,
            headers=headers,
            auth=(username, password),
            json=payload,
            verify=secure,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get('entities', [])
    except requests.exceptions.RequestException:
        return []


def v4_get_entities(client,module,entity_api,function,page,limit=50,parent_entity_ext_id=None,query_filter=None,select='*'):
    '''v4_get_entities function.
        Args:
            client: a v4 Python SDK client object.
            module: name of the v4 Python SDK module to use.
            entity_api: name of the entity API to use.
            function: name of the function to use.
            page: page number to fetch.
            limit: number of entities to fetch.
        Returns:
    '''
    entity_api_module = getattr(module, entity_api)
    entity_api = entity_api_module(api_client=client)
    list_function = getattr(entity_api, function)
    if parent_entity_ext_id is not None:
        response = list_function(parent_entity_ext_id,_page=page,_limit=limit,_filter=query_filter,_select=select)
    else:
        response = list_function(_page=page,_limit=limit,_filter=query_filter,_select=select)
    return response


def v4_get_all_entities(module,client,function,limit,module_entity_api,parent_entity_ext_id=None,query_filter=None,select='*'):
    '''v4_get_all_entities function.
        Args:
            client: a v4 Python SDK client object.
            module: name of the v4 Python SDK module to use.
            entity_api: name of the entity API to use.
            function: name of the function to use.
            limit: number of entities to fetch.
        Returns:
    '''

    entity_api_module = getattr(module, module_entity_api)
    entity_api = entity_api_module(api_client=client)
    list_function = getattr(entity_api, function)
    """ if parent_entity_ext_id is None:
        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Using {function} in {module_entity_api}...{PrintColors.RESET}") """
    entity_list=[]
    error_list=[]
    if parent_entity_ext_id is not None:
        response = list_function(parent_entity_ext_id,_page=0,_limit=1,_filter=query_filter,_select=select)
    else:
        response = list_function(_page=0,_limit=1,_filter=query_filter,_select=select)
    total_available_results=response.metadata.total_available_results
    if total_available_results:
        page_count = math.ceil(total_available_results/limit)
        if page_count > 0:
            if parent_entity_ext_id is not None: 
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(
                            v4_get_entities,
                            module=module,
                            entity_api=module_entity_api,
                            client=client,
                            function=function,
                            page=page_number,
                            limit=limit,
                            parent_entity_ext_id=parent_entity_ext_id,
                            query_filter=query_filter,
                            select=select
                        ) for page_number in range(0, page_count, 1)]
                    for future in as_completed(futures):
                        try:
                            entities = future.result()
                            if hasattr(entities, 'data'):
                                if isinstance(entities.data, Iterable):
                                    entity_list.extend(entities.data)
                                else:
                                    entity_list.append(entities.data)
                        except module.rest.ApiException as e:
                            error_data = json.loads(e.body)
                            for error in error_data['data']['error']:
                                #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                error_list.append(error_message)
                        except Exception as e:
                            print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
            else:
                with tqdm.tqdm(total=page_count, desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching pages {function} in {module_entity_api}") as progress_bar:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(
                                v4_get_entities,
                                module=module,
                                entity_api=module_entity_api,
                                client=client,
                                function=function,
                                page=page_number,
                                limit=limit,
                                parent_entity_ext_id=parent_entity_ext_id,
                                query_filter=query_filter,
                                select=select
                            ) for page_number in range(0, page_count, 1)]
                        for future in as_completed(futures):
                            try:
                                entities = future.result()
                                if hasattr(entities, 'data'):
                                    if isinstance(entities.data, Iterable):
                                        entity_list.extend(entities.data)
                                    else:
                                        entity_list.append(entities.data)
                            except module.rest.ApiException as e:
                                error_data = json.loads(e.body)
                                for error in error_data['data']['error']:
                                    #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                    error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                    error_list.append(error_message)
                            except Exception as e:
                                print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                            finally:
                                progress_bar.update(1)
    else:
        print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] No entities found for {function} in {module_entity_api}!{PrintColors.RESET}")
    for error in error_list:
        print(error)
    return entity_list


def v4_get_subnets(client,module,entity_api,function,page,limit=50):
    '''v4_get_subnets function.
        Args:
            client: a v4 Python SDK client object.
            module: name of the v4 Python SDK module to use.
            entity_api: name of the entity API to use.
            function: name of the function to use.
            page: page number to fetch.
            limit: number of entities to fetch.
        Returns:
    '''
    entity_api_module = getattr(module, entity_api)
    entity_api = entity_api_module(api_client=client)
    list_function = getattr(entity_api, function)
    response = list_function(_page=page,_limit=limit)
    return response


def v4_get_all_subnets(client,limit):
    '''v4_get_all_subnets function.
        Args:
            client: a v4 Python SDK client object.
            limit: number of entities to fetch.
        Returns:
    '''

    entity_api = ntnx_networking_py_client.SubnetsApi(api_client=client)
    entity_list=[]
    error_list=[]
    response = entity_api.list_subnets(_page=0,_limit=1)
    total_available_results=response.metadata.total_available_results
    if total_available_results:
        page_count = math.ceil(total_available_results/limit)
        if page_count > 0:
            with tqdm.tqdm(total=page_count, desc=f"{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [DATA] Fetching pages list_subnets in SubnetsApi") as progress_bar:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(
                            v4_get_subnets,
                            module=ntnx_networking_py_client,
                            entity_api='SubnetsApi',
                            client=client,
                            function='list_subnets',
                            page=page_number,
                            limit=limit
                        ) for page_number in range(0, page_count, 1)]
                    for future in as_completed(futures):
                        try:
                            entities = future.result()
                            if hasattr(entities, 'data'):
                                if isinstance(entities.data, Iterable):
                                    entity_list.extend(entities.data)
                                else:
                                    entity_list.append(entities.data)
                        except ntnx_monitoring_py_client.rest.ApiException as e:
                            error_data = json.loads(e.body)
                            for error in error_data['data']['error']:
                                #print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}")
                                error_message = f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] {type(e)} '{error['$objectType']}' {error['code']}: {error['message']} {PrintColors.RESET}"
                                error_list.append(error_message)
                        except Exception as e:
                            print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] Task failed: {e}{PrintColors.RESET}")
                        finally:
                            progress_bar.update(1)
    else:
        print(f"{PrintColors.WARNING}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [WARNING] No entities found for list_subnets in SubnetsApi!{PrintColors.RESET}")
    for error in error_list:
        print(error)
    return entity_list


def v4_get_entity_stats(client,module,entity_api,function,entity,metric_key_prefix,sampling_interval,stat_type):
    '''v4_get_entity_stats function.
       Fetches metrics for a specified entity.
        Args:
            client: a v4 Python SDK client object.
            entity: an entity uuid/ext_id
            minutes_ago: integer indicating the number of minutes to get metrics for (exp: 60 would mean get the metrics for the last hour).
            sampling_interval: integer used to specify in seconds the sampling interval.
            stat_type: The operator to use while performing down-sampling on stats data. Allowed values are SUM, MIN, MAX, AVG, COUNT and LAST.
        Returns:
    '''

    #* fetch metrics for entity
    if metric_key_prefix.startswith('nutanix_files_'):
        sampling_interval = 300
    entity_api_module = getattr(module, entity_api)
    entity_api = entity_api_module(api_client=client)
    get_stats_function = getattr(entity_api, function)

    start_time = (datetime.now(timezone.utc) - timedelta(seconds=150)).isoformat()
    end_time = (datetime.now(timezone.utc)).isoformat()
    if 'entity_parent_uuid' in entity:
        response = get_stats_function(entity['entity_parent_uuid'],extId=entity['entity_uuid'], _startTime=start_time, _endTime=end_time, _samplingInterval=sampling_interval, _statType=stat_type, _select='*')
    else:
        response = get_stats_function(extId=entity['entity_uuid'], _startTime=start_time, _endTime=end_time, _samplingInterval=sampling_interval, _statType=stat_type, _select='*')
    #print(type(response.data))
    #print(response.data)
    if metric_key_prefix == 'nutanix_vmm_ahv_stats_vm_':
        metrics = response.data.stats
    else:
        metrics = response.data.to_dict()

    #print(metrics)
    exclude_list = ['timestamp','_reserved','_object_type','_unknown_fields','ext_id','links', 'container_ext_id', 'tenant_id', 'stat_type', 'cluster', 'hypervisor_type', 'volume_group_ext_id', 'volume_disk_ext_id']
    lb_stats = ['listener_stats','target_stats']
    metrics_list = []
    #print(metrics)
    if metric_key_prefix == 'nutanix_vmm_ahv_stats_vm_':
        for metric_tuple in metrics:
            metric_list = metric_tuple.to_dict()
            for metric in metric_list:
                if metric is not None:
                    if metric not in exclude_list:
                        metric_data = metric_list.get(metric)
                        if metric_data is not None:
                            key_string = f"{metric_key_prefix}{metric}"
                            key_string = key_string.replace(".","_")
                            key_string = key_string.replace("-","_")
                            metric_to_return = f"{key_string}:{entity['entity_name']}:{metric_data}"
                            metrics_list.append(metric_to_return)
    else:
        for metric in metrics:
            #print(metric)
            if metric is not None:
                if metric not in exclude_list:
                    if metric in lb_stats:
                        #todo: add correct processing for load balancer stats here
                        pass
                    else:
                        metric_data = metrics.get(metric)
                        if metric_data is not None:
                            key_string = f"{metric_key_prefix}{metric}"
                            key_string = key_string.replace(".","_")
                            key_string = key_string.replace("-","_")
                            if metric_key_prefix == 'nutanix_networking_vpc_ns_stats_':
                                metric_to_return = f"{key_string}:{entity['entity_name']}:{metric_data[0]}"
                            else:
                                metric_to_return = f"{key_string}:{entity['entity_name']}:{metric_data[0]['value']}"
                            metrics_list.append(metric_to_return)
                            #print(f"{entity['entity_name']}:{key_string}:{metric_data[0]['value']}")
                            #self.__dict__[key_string].labels(host=entity['entity_name']).set(metric_data[0]['value'])
    #print(metrics_list)
    return metrics_list


def v4_get_files_analytics_stats(client,module,entity_api,function,entity,metric_key_prefix):
    '''v4_get_files_analytics_stats function.
       Fetches metrics for a specified entity.
        Args:
            client: a v4 Python SDK client object.
            entity: an entity uuid/ext_id
            minutes_ago: integer indicating the number of minutes to get metrics for (exp: 60 would mean get the metrics for the last hour).
        Returns:
    '''

    #* fetch metrics for entity
    sampling_interval = 300
    entity_api_module = getattr(module, entity_api)
    entity_api = entity_api_module(api_client=client)
    get_stats_function = getattr(entity_api, function)

    start_time = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
    end_time = (datetime.now(timezone.utc)).isoformat()
    if 'entity_parent_uuid' in entity:
        response = get_stats_function(entity['entity_parent_uuid'],extId=entity['entity_uuid'], _startTime=start_time, _endTime=end_time, _samplingInterval=sampling_interval, _select='*')
    else:
        response = get_stats_function(extId=entity['entity_uuid'], _startTime=start_time, _endTime=end_time, _samplingInterval=sampling_interval, _select='*')
    #print(type(response.data))
    #print(response.data)
    metrics = response.data.to_dict()

    #print(metrics)
    exclude_list = ['timestamp','_reserved','_object_type','_unknown_fields','ext_id','links', 'container_ext_id', 'tenant_id', 'stat_type', 'cluster', 'hypervisor_type']
    metrics_list = []
    #print(metrics)
    for metric in metrics:
        #print(metric)
        if metric is not None:
            if metric not in exclude_list:
                metric_data = metrics.get(metric)
                if metric_data is not None:
                    key_string = f"{metric_key_prefix}{metric}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    metric_to_return = f"{key_string}:{entity['entity_name']}:{metric_data[0]['value']}"
                    metrics_list.append(metric_to_return)
                    #print(f"{entity['entity_name']}:{key_string}:{metric_data[0]['value']}")
                    #self.__dict__[key_string].labels(host=entity['entity_name']).set(metric_data[0]['value'])
    return metrics_list


def v4_get_objectstore_stats(client,module,entity_api,function,entity,metric_key_prefix,sampling_interval,stat_type):
    '''v4_get_objectstore_stats function.
       Fetches metrics for a specified entity.
        Args:
            client: a v4 Python SDK client object.
            entity: an entity uuid/ext_id
            minutes_ago: integer indicating the number of minutes to get metrics for (exp: 60 would mean get the metrics for the last hour).
            sampling_interval: integer used to specify in seconds the sampling interval.
            stat_type: The operator to use while performing down-sampling on stats data. Allowed values are SUM, MIN, MAX, AVG, COUNT and LAST.
        Returns:
    '''

    #* fetch metrics for entity
    entity_api_module = getattr(module, entity_api)
    entity_api = entity_api_module(api_client=client)
    get_stats_function = getattr(entity_api, function)

    start_time = (datetime.now(timezone.utc) - timedelta(seconds=150)).isoformat()
    end_time = (datetime.now(timezone.utc)).isoformat()
    if 'entity_parent_uuid' in entity:
        response = get_stats_function(entity['entity_parent_uuid'],extId=entity['entity_uuid'], _startTime=start_time, _endTime=end_time, _samplingInterval=sampling_interval, _statType=stat_type)
    else:
        response = get_stats_function(extId=entity['entity_uuid'], _startTime=start_time, _endTime=end_time, _samplingInterval=sampling_interval, _statType=stat_type)
    metrics = response.data.to_dict()

    exclude_list = ['timestamp','_reserved','_object_type','_unknown_fields','ext_id','links', 'container_ext_id', 'tenant_id', 'stat_type', 'cluster', 'hypervisor_type']
    metrics_list = []
    for metric in metrics:
        if metric is not None:
            if metric not in exclude_list:
                metric_data = metrics.get(metric)
                if metric_data is not None:
                    key_string = f"{metric_key_prefix}{metric}"
                    key_string = key_string.replace(".","_")
                    key_string = key_string.replace("-","_")
                    metric_to_return = f"{key_string}:{entity['entity_name']}:{metric_data[0]['value']}"
                    metrics_list.append(metric_to_return)
    return metrics_list


def v4_get_all_vm_stats(client,start_time,end_time,sampling_interval,stat_type,page,limit='50'):
    '''v4_get_all_vm_stats function.
       Fetches metrics for all vms.
        Args:
            client: a v4 Python SDK client object.
            entity: an entity uuid/ext_id
            minutes_ago: integer indicating the number of minutes to get metrics for (exp: 60 would mean get the metrics for the last hour).
            sampling_interval: integer used to specify in seconds the sampling interval.
            stat_type: The operator to use while performing down-sampling on stats data. Allowed values are SUM, MIN, MAX, AVG, COUNT and LAST.
        Returns:
    '''

    #* fetch metrics for all vms
    entity_api = ntnx_vmm_py_client.StatsApi(api_client=client)
    response = entity_api.list_vm_stats(_page=page, _limit=limit, _startTime=start_time, _endTime=end_time, _samplingInterval=sampling_interval, _statType=stat_type, _select='*')
    metrics = response.data
    return metrics


def v4_init_api_client(module, prism, user, pwd, prism_secure=False):
    """Initialize the API client for Prism Central v4"""

    try:
        # Dynamically import the module
        module = importlib.import_module(module)
    except ModuleNotFoundError:
        print(f"Error: Could not import module '{module}'. Make sure it is installed.")
        return None

    api_client_configuration = module.Configuration()
    api_client_configuration.host = prism
    api_client_configuration.username = user
    api_client_configuration.password = pwd

    if prism_secure is False:
        #! suppress warnings about insecure connections
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        #! suppress ssl certs verification
        api_client_configuration.verify_ssl = False

    client = module.ApiClient(configuration=api_client_configuration)
    return client


def main():
    """Main entry point"""

    print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Getting environment variables...{PrintColors.RESET}")
    polling_interval_seconds = int(os.getenv("POLLING_INTERVAL_SECONDS", "30"))
    api_requests_timeout_seconds = int(os.getenv("API_REQUESTS_TIMEOUT_SECONDS", "30"))
    api_requests_retries = int(os.getenv("API_REQUESTS_RETRIES", "5"))
    api_sleep_seconds_between_retries = int(os.getenv("API_SLEEP_SECONDS_BETWEEN_RETRIES", "15"))
    app_port = int(os.getenv("APP_PORT", "9440"))
    exporter_port = int(os.getenv("EXPORTER_PORT", "8000"))

    cluster_metrics_env = os.getenv('CLUSTER_METRICS',default='True')
    if cluster_metrics_env is not None:
        cluster_metrics = cluster_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        cluster_metrics = False

    storage_containers_metrics_env = os.getenv('STORAGE_CONTAINERS_METRICS',default='True')
    if storage_containers_metrics_env is not None:
        storage_containers_metrics = storage_containers_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        storage_containers_metrics = False

    disks_metrics_env = os.getenv('DISKS_METRICS',default='False')
    if disks_metrics_env is not None:
        disks_metrics = disks_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        disks_metrics = False

    ipmi_metrics_env = os.getenv('IPMI_METRICS',default='True')
    if ipmi_metrics_env is not None:
        ipmi_metrics = ipmi_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        ipmi_metrics = False

    prism_central_metrics_env = os.getenv('PRISM_CENTRAL_METRICS',default='False')
    if prism_central_metrics_env is not None:
        prism_central_metrics = prism_central_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        prism_central_metrics = False

    networking_metrics_env = os.getenv('NETWORKING_METRICS',default='False')
    if networking_metrics_env is not None:
        networking_metrics = networking_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        networking_metrics = False
    
    microseg_metrics_env = os.getenv('MICROSEG_METRICS',default='False')
    if microseg_metrics_env is not None:
        microseg_metrics = microseg_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        microseg_metrics = False

    files_metrics_env = os.getenv('FILES_METRICS',default='False')
    if files_metrics_env is not None:
        files_metrics = files_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        files_metrics = False

    object_metrics_env = os.getenv('OBJECT_METRICS',default='False')
    if object_metrics_env is not None:
        object_metrics = object_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        object_metrics = False

    volumes_metrics_env = os.getenv('VOLUMES_METRICS',default='False')
    if volumes_metrics_env is not None:
        volumes_metrics = volumes_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        volumes_metrics = False

    hosts_metrics_env = os.getenv('HOSTS_METRICS',default='False')
    if hosts_metrics_env is not None:
        hosts_metrics = hosts_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        hosts_metrics = False

    ncm_ssp_metrics_env = os.getenv('NCM_SSP_METRICS',default='False')
    if ncm_ssp_metrics_env is not None:
        ncm_ssp_metrics = ncm_ssp_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        ncm_ssp_metrics = False

    show_stats_only_env = os.getenv('SHOW_STATS_ONLY',default='False')
    if show_stats_only_env is not None:
        show_stats_only = show_stats_only_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        show_stats_only = False

    prism_secure_env = os.getenv('PRISM_SECURE',default='False')
    if prism_secure_env is not None:
        prism_secure = prism_secure_env.lower() in ("true", "1", "t", "y", "yes")
        if prism_secure is False:
            #! suppress warnings about insecure connections
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    else:
        prism_secure = False
        #! suppress warnings about insecure connections
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    ipmi_secure_env = os.getenv('IPMI_SECURE',default='False')
    if ipmi_secure_env is not None:
        ipmi_secure = ipmi_secure_env.lower() in ("true", "1", "t", "y", "yes")
        if ipmi_secure is False:
            #! suppress warnings about insecure connections
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    else:
        ipmi_secure = False
        #! suppress warnings about insecure connections
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    ipmi_additional_metrics_env = os.getenv('IPMI_ADDITIONAL_METRICS', default='False')
    if ipmi_additional_metrics_env is not None:
        ipmi_additional_metrics = ipmi_additional_metrics_env.lower() in ("true", "1", "t", "y", "yes")
    else:
        ipmi_additional_metrics = False

    ipmi_config = json.loads(os.getenv('IPMI_CONFIG', '[]'))

    operations_mode_env = os.getenv('OPERATIONS_MODE',default='v4')

    if operations_mode_env == 'legacy':
        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Initializing metrics class...{PrintColors.RESET}")
        nutanix_metrics = NutanixMetricsLegacy(
            app_port=app_port,
            polling_interval_seconds=polling_interval_seconds,
            api_requests_timeout_seconds=api_requests_timeout_seconds,
            api_requests_retries=api_requests_retries,
            api_sleep_seconds_between_retries=api_sleep_seconds_between_retries,
            prism=os.getenv('PRISM'),
            user = os.getenv('PRISM_USERNAME'),
            pwd = os.getenv('PRISM_SECRET'),
            prism_secure=prism_secure,
            ipmi_username = os.getenv('IPMI_USERNAME', default='ADMIN'),
            ipmi_secret = os.getenv('IPMI_SECRET', default=None),
            vm_list=os.getenv('VM_LIST'),
            cluster_metrics=cluster_metrics,
            storage_containers_metrics=storage_containers_metrics,
            ipmi_metrics=ipmi_metrics,
            prism_central_metrics=prism_central_metrics,
            ncm_ssp_metrics=ncm_ssp_metrics
        )
        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Starting http server on port {exporter_port}{PrintColors.RESET}")
        start_http_server(exporter_port)
        nutanix_metrics.run_metrics_loop()
    elif operations_mode_env == 'v4':
        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Initializing metrics class...{PrintColors.RESET}")
        nutanix_metrics = NutanixMetrics(
            app_port=app_port,
            polling_interval_seconds=polling_interval_seconds,
            api_requests_timeout_seconds=api_requests_timeout_seconds,
            api_requests_retries=api_requests_retries,
            api_sleep_seconds_between_retries=api_sleep_seconds_between_retries,
            prism=os.getenv('PRISM'),
            user = os.getenv('PRISM_USERNAME'),
            pwd = os.getenv('PRISM_SECRET'),
            prism_secure=prism_secure,
            cluster_metrics=cluster_metrics, hosts_metrics=hosts_metrics, storage_containers_metrics=storage_containers_metrics, disks_metrics=disks_metrics, networking_metrics=networking_metrics, 
            files_metrics=files_metrics, object_metrics=object_metrics, volumes_metrics=volumes_metrics, ncm_ssp_metrics=ncm_ssp_metrics, prism_central_metrics=prism_central_metrics, microseg_metrics=microseg_metrics,
            vm_list=os.getenv('VM_LIST'),
            show_stats_only=show_stats_only
        )
        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Starting http server on port {exporter_port}{PrintColors.RESET}")
        start_http_server(exporter_port)
        nutanix_metrics.run_metrics_loop()
    elif operations_mode_env == 'redfish':
        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Initializing metrics class...{PrintColors.RESET}")
        nutanix_metrics = NutanixMetricsRedfish(
            polling_interval_seconds=polling_interval_seconds,
            api_requests_timeout_seconds=api_requests_timeout_seconds,
            api_requests_retries=api_requests_retries,
            api_sleep_seconds_between_retries=api_sleep_seconds_between_retries,
            ipmi_secure=ipmi_secure,
            ipmi_config=ipmi_config,
            ipmi_additional_metrics=ipmi_additional_metrics,
        )
        print(f"{PrintColors.OK}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [INFO] Starting http server on port {exporter_port}{PrintColors.RESET}")
        start_http_server(exporter_port)
        nutanix_metrics.run_metrics_loop()
    else:
        print(f"{PrintColors.FAIL}{(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Invalid operations mode (v4, legacy, redfish): {operations_mode_env}{PrintColors.RESET}")
#endregion #*FUNCTIONS


if __name__ == "__main__":
    main()
