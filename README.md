# Drain3 - Log Prasing and Clustering Tool
Drain3 is a tool designed to parse and cluster logs, specifically targeting Kubernetes API-server logs in the context of fault injection experiments. This tool helps in de-parametrizing logs and extracting templates from log data. It focuses on filtering out variable fields and identifying message patterns to better understand system behavior under various failure conditions.

## Table of Contents 📋

- [Features](#features)
- [Usage](#usage) 
- [Output](#output)
- [Modification](#modification)
__________________________________________________________________________________________________________________________
## Features
<ul>
    <li><b>Log Parsing</b> - Tokenizes log fields, including dynamic components, to extract consistent templates for analysis.</li>
    <li><b>Clustering</b> - Uses unsupervised clustering techniques to group similar log entries based on message patterns and fault types.</li>
    <li><b>Fault Injection Analysis</b> - Helps analyze the impact of various fault types on the Kubernetes orchestrator, with a focus on the API server and etcd interactions.</li>
    <li><b>Customizable Configuration</b> - Allows adjustments of parameters like similarity threshold and maximum number of clusters for more refined clustering results.</li>
    <li><b>Fault Classification</b> - Classifies logs according to injected fault types, including network issues, resource constraints, and system outages.</li>
</ul>

## Usage
Modify the configuration file (config.ini) to adjust parameters for log parsing and clustering. Key parameters include:
<ul>
    <li><b>similarity_threshold</b> - Defines the similarity threshold for clustering.</li>
    <li><b>max_clusters</b> - Sets the maximum number of clusters to generate.</li>
    <li><b>failure_type_mapping</b> - Maps fault types to log entries.</li>
</ul>

## Output
The output will include:
<ul>
    <li><b>Clustered Templates</b> - Identified message patterns across the logs.</li>
    <li><b>Cluster Metadata</b> - Information about the clusters, such as the number of occurrences of each template.</li>
    <li><b>FaILURE Type Associations</b> - Mapping of log entries to their respective fAILURE types.</li>
</ul>


## Modifications
<ul>
    <li>Improved tokenization of log fields for better handling of dynamic components.</li>
    <li>Updated clustering algorithm to handle a higher number of samples and more varied fault types.</li>
    <li>Enhanced log filtering to remove irrelevant fields and focus on critical components.</li>
</ul>






