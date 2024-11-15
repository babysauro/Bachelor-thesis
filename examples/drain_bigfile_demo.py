# SPDX-License-Identifier: MIT

import json
import logging
import os
import subprocess
import sys
import time
from os.path import dirname

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

#Path verso la cartella contenente tutti i log
in_log_file = "/Users/serenasavarese/Desktop/Tesi/Mutiny_dataset_filtered/999_99_apiserver_etcd_subset"


config = TemplateMinerConfig()
config.load(f"{dirname(__file__)}/drain3.ini")
config.profiling_enabled = True
template_miner = TemplateMiner(config=config)

line_count = 0
txt_file_count = 0 

lines=[]

#Si esplorano le cartelle e sotto-cartelle fino a trovare file .txt, dopodiché avviene la lettura del file
for root, dirs, files in os.walk(in_log_file):
    #print(root, files)
    if "deploy" in root:
        #print(f"Found 'deploy' in path: {root}")
        for file in files:
            #Filtraggio dei file .txt il cui nome contiene "filtered"
            if file.endswith(".txt") and "filtered" in file:
             with open(os.path.join(root, file)) as f:
                lines.append(f.readlines())
                txt_file_count += 1



start_time = time.time()
batch_start_time = start_time
batch_size = 100000

#Filtraggio nell'array
lines = [
    x
    for xs in lines
    for x in xs
]

#Dizionario per raccogliere i templates
#templates = {}
#template_count = {}

for line in lines:
    line = line.rstrip()
    #line = line.partition(": ")[2]
    result = template_miner.add_log_message(line)
    line_count += 1

    #Controllo se il risultato contiene un template
    #if result["change_type"] != "none":
        #template_message = result["template_mined"]
        #cluster_id = f"cluster_{len(templates) + 1}"
    
    #Se il template non è presente in templates
    #if cluster_id not in templates:
        #templates[cluster_id] = []
        #template_count[cluster_id] = 0

    #Aggiunta template al cluster
    #templates[cluster_id].append(template_message)
    #Incremento del contatore per questo cluster
    #template_count[cluster_id] +=1

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

#Stampa il numero di template
#print("Numero di template per cluster:")
#for cluster_id, count in template_count.items():
    #print(f"{cluster_id}: {count} template")

time_took = time.time() - start_time
rate = line_count / time_took
logger.info(f"--- Done processing file in {time_took:.2f} sec. Total of {line_count} lines, rate {rate:.1f} lines/sec, "
            f"{len(template_miner.drain.clusters)} clusters")

sorted_clusters = sorted(template_miner.drain.clusters, key=lambda it: it.size, reverse=True)
for cluster in sorted_clusters:
    logger.info(cluster)

print("Prefix Tree:")
template_miner.drain.print_tree()

template_miner.profiler.report(0)

#Stampa numero di file txt
print(f"Found {txt_file_count} .txt files")

#Scrittura dei template nel file templates.txt
#with open('templates.txt', 'w') as txt_file:
    #for cluster, template_list in templates.items():
        #txt_file.write(f"{cluster}:\n")
        #for template in template_list:
            #txt_file.write(f"  - {template}\n")
        #txt_file.write("\n")

#print("File txt creato con successo")


