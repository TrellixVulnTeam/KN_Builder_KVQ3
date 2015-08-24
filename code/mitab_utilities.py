"""Utiliites for cleaning files of in the mitab format.

Classes:

Functions:
    2table(rawline, version_dict) -> str: takes as input a fetched file in
        MITAB format and a dictionary object version_dict describing the file.
        Produces the 2table edge file, edge_meta file and node_meta files.

Variables:
"""

import json
import os
import csv
import re

def table(rawline, version_dict):
    """Uses the provided rawline file to produce a 2table_edge file, an
    edge_meta file, and a node_meta file (only for property nodes).

    This returns noting but produces the 2table formatted files from the
    provided rawline file:
        rawline table (file, line num, line_chksum, rawline)
        2tbl_edge table (line_cksum, n1name, n1hint, n1type, n1spec, 
                        n2name, n2hint, n2type, n2spec, et_hint, score)
        edge_meta (line_cksum, info_type, info_desc)
        node_meta (line_cksum, node_num (1 or 2), 
                   info_type (evidence, relationship, experiment, or link),
                   info_desc (text))
    
    Args:
        rawline(str): The path to the rawline file
        version_dict (dict): A dictionary describing the attributes of the
            alias for a source.

    Returns:
    """

    #outfiles
    table_file = '.'.join(rawline.split('.')[:-2]) + '.edge.txt'
    e_meta_file = '.'.join(rawline.split('.')[:-2]) + '.edge_meta.txt'
    #n_meta_file = '.'.join(rawline.split('.')[:-2]) + '.node_meta.txt'

    #static column values
    n1type = 'gene'
    n2type = 'gene'
    score = 1
    info_type = 'reference'

    #mapping files
    ppi = os.path.join('..', '..', 'ppi', 'obo_map', 'ppi.obo_map.json')
    with open(ppi) as infile:
        term_map = json.load(infile)
    #species = (os.path.join('..', '..', 'species', 'species_map')
    #            'species.species_map.json')
    #with open(species) as infile:
    #   species_map = json.load(species)

    with open(rawline, encoding='utf-8') as infile, \
        open(table_file, 'w') as edges,\
        open(e_meta_file, 'w') as e_meta:
        reader = csv.reader(infile, delimiter='\t')
        next(reader)
        edge_writer = csv.writer(edges, delimiter='\t')
        e_meta_writer = csv.writer(e_meta, delimiter='\t')
        for line in reader:
            chksm = line[2]
            raw = line[3:]
            n1list = raw[0].split('|') + raw[2].split('|')
            n2list = raw[1].split('|') + raw[3].split('|')
            if len(n1list) == 0 or len(n2list) == 0:
                continue
            match = re.search('taxid:(\d+)', raw[9])
            if match is not None:
                n1spec = match.group(1)
            else:
                continue
            match = re.search('taxid:(\d+)', raw[10])
            if match is not None:
                n2spec = match.group(1)
            else:
                continue
            n2spec = raw[10].split('|')[0][6:].split('(')[0]
            if len(raw) > 35 and raw[35].upper() == 'TRUE':
                et_hint = 'PPI_negative'
            else:
                match = re.search('(MI:\d+)', raw[11])
                if match is not None:
                    et_hint = term_map[match.group(1)]
                else:
                    continue
            for n1tuple in n1list:
                if n1tuple.count(':') != 1:
                    continue
                n1hint, n1 = n1tuple.split(':')
                for n2tuple in n2list:
                    if n2tuple.count(':') != 1:
                        continue
                    n2hint, n2 = n2tuple.split(':')
                    edge_writer.writerow([chksm, n1, n1hint, n1type, n1spec, \
                        n2, n2hint, n2type, n2spec, et_hint, score])
            publist = raw[8]
            e_meta_writer.writerow([chksm, info_type, publist])