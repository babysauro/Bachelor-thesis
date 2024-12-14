# SPDX-License-Identifier: MIT

import json
import logging
import os
import subprocess
import sys
import time
import re
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
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

# Dizionario per mappare i codici di failure alle descrizioni
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
        experiment_map[os.path.basename(path)] = fault_mapping.get(fault_code)

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
                # experiment_name = os.path.join(
                #     os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(root)))),  # Livello superiore (es. 999_99_apiserver_etcd_subset)
                #     os.path.basename(os.path.dirname(os.path.dirname(root)))) # Nome dell'esperimento (es. 100_deploy)
                if experiment_name not in experiment_map:
                    continue  # Salta gli esperimenti non mappati
                with open(os.path.join(root, file)) as f:
                    for line in f:
                        lines.extend([(line.strip(), experiment_name) for line in f])


start_time = time.time()
batch_start_time = start_time
batch_size = 100000

# Filtraggio nell'array
# lines = [
#     x
#     for xs in lines
#     for x in xs
# ]


# Struttura per raccogliere i dati delle tabelle
table_data = {}


for line, experiment_name in lines:
    line = line.rstrip()
    match = user_agent_regex.match(line)
    user_agent_value = match.group(1) if match else None
    if match:
        line = match.group(1)
    
    # Estrai il valore di 'verb' e 'userAgent'
    verb_value = None
    verb_match = re.search(r'verb="([^"]+)"', line)
    if verb_match:
        verb_value = verb_match.group(1)

    user_agent_value = None
    user_agent_match = re.search(r'userAgent="([^"]+)"', line)
    if user_agent_match:
        user_agent_value = user_agent_match.group(1)

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
        fault_code = experiment_map.get(experiment_name)
        
        # Inizializza il cluster se non esiste
        if cluster_id not in table_data:
            table_data[cluster_id] = {
                'experiments': {},
                'fault_codes': set(),
                'total_count': 0,
                'verb': verb_value,
                'userAgent': user_agent_value
            }


        # Aggiungi o aggiorna l'esperimento per questo cluster
        if experiment_name not in table_data[cluster_id]['experiments']:
            table_data[cluster_id]['experiments'][experiment_name] = 0
        
        table_data[cluster_id]['experiments'][experiment_name] += 1
        table_data[cluster_id]['fault_codes'].add(fault_code)
        table_data[cluster_id]['total_count'] += 1

# Salva i dettagli di verb e userAgent per ogni cluster
        if cluster_id not in table_data:
            table_data[cluster_id] = {'verb': verb_value, 'userAgent': user_agent_value}      


time_took = time.time() - start_time
rate = line_count / time_took
logger.info(f"--- Done processing file in {time_took:.2f} sec. Total of {line_count} lines, rate {rate:.1f} lines/sec, "
            f"{len(template_miner.drain.clusters)} clusters")

# Funzioni per dedurre workload e componente iniettato -> grafico
def infer_workload(experiment_name):
    if "deploy" in experiment_name:
        return "Deployment"
    elif "scale" in experiment_name:
        return "Scaling"
    return "Available"

# def infer_injected_component(experiment_name):
#     if "etcd" in experiment_name:
#         return "etcd"
#     elif "apiserver" in experiment_name:
#         return "apiserver"
#     return "Unknown"

# GRAFICI
# Preparazione i dati per il grafico
plot_data = []

for cluster_id, cluster_data in table_data.items():
    for experiment, count in cluster_data['experiments'].items():
        fault_code = experiment_map.get(experiment)
        plot_data.append({
            'cluster_id': cluster_id,
            'experiment': experiment,
            'fault_code': fault_code,
            'count': count,
            'workload': infer_workload(experiment),
            'verb': table_data.get(cluster_id, {}).get('verb'),
            'userAgent': table_data.get(cluster_id, {}).get('userAgent')
            #'injected_component': infer_injected_component(experiment)
        })
        # Estrai i valori di verb e userAgent
        verb = table_data.get(cluster_id, {}).get('verb')
        userAgent = table_data.get(cluster_id, {}).get('userAgent')

        # Stampa di verb e userAgent
        #print(f"Cluster ID: {cluster_id} - Verb: {verb} - UserAgent: {userAgent}")
        

# Conversione in DataFrame per analisi e grafico
df = pd.DataFrame(plot_data)

# GRAFICO 1: Distribuzione per tipo di fault e workload -> boxplot 1
plt.figure(figsize=(12, 8))
sns.boxplot(x='fault_code', y='count', hue='workload', data=df, palette="Set3")
plt.title('Distribuzione di Log per Tipo di Fault e Workload')
plt.xlabel('Tipo di Fault')
plt.ylabel('Numero di Log')
plt.xticks(rotation=45)
plt.legend(title='Workload')
plt.tight_layout()
plt.savefig("cluster_failure_workload_analysis.png")
plt.show()


# # # Creazione della matrice di occorrenze (cluster_id vs fault_code)
# # cluster_fault_matrix = df.pivot_table(index='cluster_id', columns='fault_code', values='count', aggfunc='sum', fill_value=0)
# # # GRAFICO 2: heatmap
# # plt.figure(figsize=(13, 8))
# # sns.heatmap(cluster_fault_matrix, cmap="Blues", annot=False, cbar=True)
# # plt.title('Distribuzione dei Cluster nei Vari Failure')
# # plt.xlabel('Tipo di Failure')
# # plt.ylabel('Cluster ID')
# # plt.tight_layout()
# # plt.savefig("heatmap_clusters_vs_failure.png")
# # plt.show()

# #--------------------------------------------------------------------------------------------------------------#

# # # GRAFICO 3: boxplot di cluster per tipologia di failure (con divisione per workload)
# # # Calcolo dei primi 20 cluster globalmente in base alla dimensione
# # all_fault_data_sorted = sorted(template_miner.drain.clusters, key=lambda cluster: cluster.size, reverse=True)
# # top_n = 20
# # top_clusters = [cluster.cluster_id for cluster in all_fault_data_sorted[:top_n]]

# # # Lista di tipi di failure
# # failure_types = ['no_failure', 'timing', 'less_resources', 'more_resources', 'network', 'stallo', 'outage_totale']

# # # Ciclo su ciascun tipo di failure
# # for failure_type in failure_types:
# #     # Filtro dei dati per il tipo di failure
# #     fault_data = df[df['fault_code'] == failure_type]
    
# #     # Aggiunta della colonna 'workload' se non esiste già
# #     if 'workload' not in fault_data.columns:
# #         fault_data['workload'] = fault_data['experiment'].apply(infer_workload)  # Funzione per inferire il workload
    
# #     # Filtro dei dati per includere solo i top 20 cluster
# #     fault_data_top_clusters = fault_data[fault_data['cluster_id'].isin(top_clusters)]
    
# #     # Ordina i cluster per dimensione
# #     fault_data_top_clusters['cluster_id'] = pd.Categorical(
# #         fault_data_top_clusters['cluster_id'], categories=top_clusters, ordered=True
# #     )
    
# #     # Creazione del grafico
# #     plt.figure(figsize=(14, 8))
# #     sns.boxplot(x='cluster_id', y='count', hue='workload', data=fault_data_top_clusters, palette="Set3")
# #     plt.title(f'Distribuzione di Cluster per Tipo di Failure: {failure_type.capitalize()} con Workload')
# #     plt.xlabel('Cluster ID')
# #     plt.ylabel('Numero Eventi')
# #     plt.xticks(rotation=45)
# #     plt.legend(title='Workload', bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0, fontsize='small')
# #     plt.tight_layout()
# #     plt.savefig(f"{failure_type}_failure_cluster_workload_analysis.png")
# #     plt.show()

# #--------------------------------------------------------------------------------------------------------------#

# Filtro per verb = 'path' o 'post' e userAgent = 'kube-controller-manager'
filtered_df = df[
    (df['verb'].isin(['PATH', 'POST'])) & 
    (df['userAgent'].str.contains('kube-controller-manager'))
]
print(filtered_df)

# GRAFICO 3: boxplot di cluster per tipologia di failure con i nuovi filtri (verb='path' o 'post', userAgent='kube-controller-manager')
# Calcolo dei cluster unici dopo il filtro (senza limitare a 20)
unique_clusters = filtered_df['cluster_id'].unique()

# Lista di tipi di failure
failure_types = ['no_failure', 'timing', 'less_resources', 'more_resources', 'network', 'stallo', 'outage_totale']

# Ciclo su ciascun tipo di failure
for failure_type in failure_types:
    # Filtro dei dati per il tipo di failure
    fault_data = filtered_df[filtered_df['fault_code'] == failure_type]
    
    # Aggiunta della colonna 'workload' se non esiste già
    if 'workload' not in fault_data.columns:
        fault_data['workload'] = fault_data['experiment'].apply(infer_workload)  # Funzione per inferire il workload
    
    # Filtro dei dati per includere solo i cluster unici filtrati
    fault_data_unique_clusters = fault_data[fault_data['cluster_id'].isin(unique_clusters)]
    
    # Ordina i cluster per dimensione
    fault_data_unique_clusters['cluster_id'] = pd.Categorical(
        fault_data_unique_clusters['cluster_id'], categories=unique_clusters, ordered=True
    )
    
    # Creazione del grafico
    plt.figure(figsize=(14, 8))
    sns.boxplot(x='cluster_id', y='count', hue='workload', data=fault_data_unique_clusters, palette="Set3")
    plt.title(f'Distribuzione di Cluster per Tipo di Failure: {failure_type.capitalize()} con Workload (Verb e UserAgent Filtrati)')
    plt.xlabel('Cluster ID')
    plt.ylabel('Numero Eventi')
    plt.xticks(rotation=45)
    plt.legend(title='Workload', bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0, fontsize='small')
    plt.tight_layout()
    plt.savefig(f"{failure_type}_failure_cluster_workload_analysis_filtered.png")
    plt.show()
#--------------------------------------------------------------------------------------------------------------#


# Stampa dei clusters creati
sorted_clusters = sorted(template_miner.drain.clusters, key=lambda it: it.size, reverse=True)
for cluster in sorted_clusters:
    logger.info(cluster)

print("Prefix Tree:")
template_miner.drain.print_tree()

template_miner.profiler.report(0)

# Stampa tabella nel file cluster_analysis_report
script_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(script_dir, 'cluster_analysis_report.cvs')

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
    #f.write("Fault Code\n")
    f.write("-" * (len(cluster_ids) * 10 + 20) + "\n")

    for experiment, clusters in table_data.items():
        fault_code = experiment_map.get(experiment)
        f.write(f"{experiment}\t")
        for cluster_id in cluster_ids:
            if cluster_id in clusters:
                f.write(f"{clusters[cluster_id]}\t")
            else:
                f.write("0\t")
        #f.write(f"{fault_code}\n")


logger.info(f"Cluster analysis report saved to {output_file}")

