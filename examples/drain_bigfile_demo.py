# SPDX-License-Identifier: MIT

import json
import logging
import os
import subprocess
import sys
import time
import re
from os.path import dirname

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

# Path verso la cartella contenente tutti i log
in_log_file = "/Users/serenasavarese/Desktop/Tesi/Mutiny_dataset_filtered"

# Path verso il file delle classificazioni
classif_file = "/Users/serenasavarese/Desktop/Tesi/Mutiny_dataset_filtered/classif_new_updated.txt"

config = TemplateMinerConfig()
config.load(f"{dirname(__file__)}/drain3.ini")
config.profiling_enabled = True
template_miner = TemplateMiner(config=config)

line_count = 0 
lines = []

# Regex per catturare fino a userAgent
user_agent_regex = re.compile(r'^(.*?userAgent="[^"]*")')

# Dizionario per mappare i codici di fault alle descrizioni
fault_mapping = {
    "A": "no_failure",
    "B": "timing",
    "C": "more_resources",
    "D": "less_resources",
    "E": "network",
    "F": "stallo",
    "G": "outage_totale"
}

# Creazione di un dizionario per mappare il nome dell'esperimento al faultCode
experiment_map = {}
with open(classif_file, "r") as f:
    for line in f:
        path, fault_code = line.strip().split()
        # Associa il nome del file all'errore
        experiment_map[os.path.basename(path)] = fault_mapping.get(fault_code, "Unknown")

# Leggi le cartelle da esplorare dal file di classificazione
folders_to_explore = set(experiment_map.keys())

# Si esplorano le cartelle e sotto-cartelle fino a trovare file .txt, dopodiché avviene la lettura del file
for root, dirs, files in os.walk(in_log_file):
    # Controlla se il percorso corrente contiene una delle cartelle da esplorare
    if any(folder in root for folder in folders_to_explore):
        for file in files:
            # Filtraggio dei file .txt il cui nome contiene "filtered"
            if file.endswith(".txt") and "filtered" in file:
                experiment_name = os.path.basename(os.path.dirname(os.path.dirname(root)))
                with open(os.path.join(root, file)) as f:
                    for line in f:
                        lines.extend([(line.strip(), experiment_name) for line in f])
                        #logger.info(f"Esperimento trovato: {experiment_name}, Path: {root}")

start_time = time.time()
batch_start_time = start_time
batch_size = 100000

# Filtraggio nell'array
# lines = [
#     x
#     for xs in lines
#     for x in xs
# ]


# Struttura per raccogliere i dati della tabella
table_data = {}


for line, experiment_name in lines:
    line = line.rstrip()
    match = user_agent_regex.match(line)
    if match:
        line = match.group(1)
    

    # Aggiungi il log al miner per il template
    result = template_miner.add_log_message(line)
    line_count += 1

    # Controllo batch per la velocità di elaborazione
    if line_count % batch_size == 0:
        time_took = time.time() - batch_start_time
        rate = batch_size / time_took
        logger.info(f"Processing line: {line_count}, rate {rate:.1f} lines/sec, "
                    f"{len(template_miner.drain.clusters)} clusters so far.")
        batch_start_time = time.time()

    if result["change_type"] != "none":
        result_json = json.dumps(result)
        logger.info(f"Input ({line_count}): {line}")
        logger.info(f"Result: {result_json}")

    # Raccogli i dati per la tabella
    for cluster in template_miner.drain.clusters:
        cluster_id = cluster.cluster_id
        fault_code = experiment_map.get(experiment_name, "Unknown")

        # Inizializza il cluster se non esiste
        if cluster_id not in table_data:
            table_data[cluster_id] = {
                'experiments': {},
                'fault_codes': set(),
                'total_count': 0
            }

        # Aggiungi o aggiorna l'esperimento per questo cluster
        if experiment_name not in table_data[cluster_id]['experiments']:
            table_data[cluster_id]['experiments'][experiment_name] = 0
        
        table_data[cluster_id]['experiments'][experiment_name] += 1
        table_data[cluster_id]['fault_codes'].add(fault_code)
        table_data[cluster_id]['total_count'] += 1

time_took = time.time() - start_time
rate = line_count / time_took
logger.info(f"--- Done processing file in {time_took:.2f} sec. Total of {line_count} lines, rate {rate:.1f} lines/sec, "
            f"{len(template_miner.drain.clusters)} clusters")

# Stampa dei clusters creati
sorted_clusters = sorted(template_miner.drain.clusters, key=lambda it: it.size, reverse=True)
for cluster in sorted_clusters:
    logger.info(cluster)

print("Prefix Tree:")
template_miner.drain.print_tree()

template_miner.profiler.report(0)

# Stampa tabella nel file cluster_analysis_report
script_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(script_dir, 'cluster_analysis_report.txt')

with open(output_file, 'w') as f:
    f.write("Cluster Analysis Report\n")
    f.write("-------------------\n")

    # Ottieni la lista dei cluster ID
    cluster_ids = set()
    for experiment in table_data.values():
        cluster_ids.update(experiment.keys())
    cluster_ids = sorted(list(cluster_ids))

    # Scrivi la tabella
    f.write("  |")
    for cluster_id in cluster_ids:
        f.write(f"{cluster_id}\t")
    f.write("Fault Code\n")
    f.write("-" * (len(cluster_ids) * 10 + 20) + "\n")

    for experiment, clusters in table_data.items():
        fault_code = experiment_map.get(experiment, "Unknown")
        f.write(f"{experiment}\t")
        for cluster_id in cluster_ids:
            if cluster_id in clusters:
                f.write(f"{clusters[cluster_id]}\t")
            else:
                f.write("0\t")
        f.write(f"{fault_code}\n")

logger.info(f"Cluster analysis report saved to {output_file}")
