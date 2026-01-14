FROM python:slim-bookworm

WORKDIR /~

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "-u", "./nutanix_prometheus_exporter.py" ]

#to make sure stdout shows up in the logs
ENV PYTHONUNBUFFERED=1
#used to specify Prism Element IP address or FQDN (assuming FQDN can be resolved inside the container)
ENV PRISM='127.0.0.1'
#used to specify the username to access Prism (viewer is the least privilege required) 
ENV PRISM_USERNAME='admin'
#used to specify the password for username
ENV PRISM_SECRET='secret'
#used to specify the OOBM module (IPMI) username.  Will default to ADMIN if nothing is specified.
#ENV IPMI_USERNAME='ADMIN'
#used to specify the password for the IPMI user. Will default to using the node serial number if this is left blank.
#ENV IPMI_SECRET='secret'
#leave this value to null if you don't want to verify SSL certificates. Set it to anything but null to check SSL certificates.
#ENV PRISM_SECURE=''
#used to specify the port used by Prism API
ENV APP_PORT='9440'

#defines the time to wait between each poll
ENV POLLING_INTERVAL_SECONDS='30'
#used to specify the container port where the node exporter will publish metrics
ENV EXPORTER_PORT='8000'

#used to determine operations mode (v4,legacy,redfish).
ENV OPERATIONS_MODE='v4'

#*used when operations mode is legacy (some apply to v4 as well where indicated in the description)
#scope: legacy, v4
#use a comma separated string with virtual machine names for which you want to collect metrics. If this is null, then no VM metrics will be collected.
#it is strongly recommended not to get crazy with vm list as this would considerably lengthen the metric collection time when using legacy operations mode.
#with v4 operations mode, you can set this to 'all' if you want to collect all metrics for all VM entities.
ENV VM_LIST='all'
#scope: legacy
#used to control timeout setting when making API calls in legacy mode
ENV API_REQUESTS_TIMEOUT_SECONDS=30
#scope: legacy
#used to control retry setting when making API calls in legacy mode
ENV API_REQUESTS_RETRIES=5
#scope: legacy
#used to control retry sleep setting when making API calls in legacy mode
ENV API_SLEEP_SECONDS_BETWEEN_RETRIES=15
#scope: legacy, v4
#used to determine if clusters metrics will be generated; set it to False value if you don't want to collect cluster metrics.
ENV CLUSTER_METRICS='True'
#scope: legacy, v4
#used to determine if storage containers metrics will be generated; set it to False value if you don't want to collect storage containers metrics.
ENV STORAGE_CONTAINERS_METRICS='True'
#scope: legacy, v4
#used to determine if IPMI metrics will be generated; set it to False value if you don't want to collect IPMI metrics. This is only valid for legacy operations mode
#When using v4, you will need to create a separate instance to collect metrics from the IPMIs that will work in the redfish operations mode.
#scope: legacy
ENV IPMI_METRICS='False'
#used to determine if additional IPMI metrics will be generated (power_state, cpu_util, mem_util); set it to False value if you don't want to collect IPMI metrics. This is only valid for legacy operations mode
#When using v4, you will need to create a separate instance to collect metrics from the IPMIs that will work in the redfish operations mode.
#scope: legacy
ENV IPMI_ADDITIONAL_METRICS='False'
#used to determine if Prism Central metrics will be generated; set it to False value if you don't want to collect Prism Central metrics.
#with v4 operations mode, this determines if most count metrics are collected or not.
#scope: legacy, v4
ENV PRISM_CENTRAL_METRICS='True'
#used to determine if NCM SSP metrics will be generated; set it to False value if you don't want to collect NCM SSP metrics.
#since there is no v4 NCM SSP API yet, this only works in legacy operations mode.
#scope: legacy
ENV NCM_SSP_METRICS='False'

#*used when operations mode is redfish
#leave this value to null if you don't want to verify SSL certificates when using redfish operations mode. Set it to anything but null to check SSL certificates.
#ENV IPMI_SECURE=''
#When using redfish operations mode, configure list of ipmi entities as follows.
#ENV IPMI_CONFIG='[
#    {"ip":"1.1.1.1","name":"myhost1","username":"ADMIN","password":"my_pwd"},
#    {"ip":"2.2.2.2","name":"myhost2","username":"ADMIN","password":"my_other_pwd"},
#]

#*used when operations mode is v4
#used to determine if Disks (hardware disks) specific metrics will be generated
#note that this can take quite a long time if you have lots of nodes and disks in your clusters
ENV DISKS_METRICS='False'
#used to determine if Advanced Networking and Flow Virtual Networking metrics will be generated
#(applies to all networking module entities except subnets which are always inlcuded with Prism Central and Cluster metrics)
ENV NETWORKING_METRICS='True'
#used to determine if Flow Network Security metrics will be generated
ENV MICROSEG_METRICS='True'
#used to determine if Nutanix Files metrics will be generated
ENV FILES_METRICS='True'
#used to determine if Nutanix Object metrics will be generated
ENV OBJECT_METRICS='True'
#used to determine if Nutanix Volume metrics will be generated
ENV VOLUMES_METRICS='True'
#used to determine if Hosts/Nodes metrics will be generated
ENV HOSTS_METRICS='True'
#when set to true, only displays the complete list of available metrics (based on the true/false selection for each metric type) in a JSON format
ENV SHOW_STATS_ONLY='False'
