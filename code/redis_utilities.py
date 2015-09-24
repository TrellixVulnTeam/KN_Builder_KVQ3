"""Utiliites for interacting with the KnowEnG Redis db through python.

Classes:


Functions:


Variables:
"""

import config_utilities as cf
import redis
import json
import os

def import_ensembl(alias):
    """Imports the ensembl data for the provided alias into the Redis database.

    This stores the foreign key to ensembl stable ids in the Redis database.
    It uses the all mappings dictionary created by mysql.query_all_mappings
    for alias. This then iterates through each foreign_key. If the foreign_key
    has not been seen before, it sets unique:foreign_key as the stable id. If
    the key has been seen before and maps to a different ensembl stable id, it
    sets the value for unique:foreign_key as unmapped:many. In each case, it
    sets the value of taxid:hint:foreign_key as the stable_id, and appends
    taxid:hint to the set with foreign_key as the key.

    Args:
        alias (str): An alias defined in ensembl.aliases.

    Returns:
    """
    rdb = redis.StrictRedis(host=cf.DEFAULT_REDIS_URL,
        port=cf.DEFAULT_REDIS_PORT, db=0)
    map_dir = os.sep + cf.DEFAULT_MAP_PATH
    if os.path.isdir(cf.DEFAULT_LOCAL_BASE):
        map_dir = cf.DEFAULT_LOCAL_BASE + map_dir
    with open(os.path.join(map_dir, alias + '_all.json')) as infile:
        map_dict = json.load(infile)
    for key in map_dict:
        (taxid, hint, foreign_key) = key.split('::')
        hint = hint.upper()
        ens_id = map_dict[key].encode()
        rkey = rdb.getset('unique::' + foreign_key, ens_id)
        if rkey is not None and rkey != ens_id:
            rdb.set('unique::' + foreign_key, 'unmapped-many')
        rdb.sadd(foreign_key, '::'.join([taxid, hint]))
        rdb.set('::'.join([taxid, hint, foreign_key]), ens_id)

def conv_gene(rdb, foreign_key, hint, taxid):
    """Uses the redis database to convert a gene to enesmbl stable id

    This checks first if there is a unique name for the provided foreign key.
    If not it uses the hint and taxid to try and filter the foreign key
    possiblities to find a matching stable id.

    Args:
        rdb (redis object): redis connection to the mapping db
        foreign_key (str): the foreign gene identifer to be translated
        hint (str): a hint for conversion
        taxid (str): the species taxid
    """
    hint = hint.upper()
    unique = rdb.get('unique::' + foreign_key)
    if unique is None:
        return 'unmapped-none'
    if unique != 'unmapped-many'.encode():
        return unique.decode()
    mappings = rdb.smembers(foreign_key)
    taxid_match = list()
    hint_match = list()
    both_match = list()
    for taxid_hint in mappings:
        taxid_hint = taxid_hint.decode()
        taxid_hint_key = '::'.join([taxid_hint, foreign_key])
        taxid_hint = taxid_hint.split('::')
        if taxid == taxid_hint[0] and hint in taxid_hint[1]:
            both_match.append(taxid_hint_key)
        if taxid == taxid_hint[0]:
            taxid_match.append(taxid_hint_key)
        if hint in taxid_hint[1]:
            hint_match.append(taxid_hint_key)
    if both_match:
        both_ens_ids = list(set(rdb.mget(both_match)))
        if len(both_ens_ids) == 1:
            return both_ens_ids[0].decode()
    if taxid_match:
        taxid_ens_ids = list(set(rdb.mget(taxid_match)))
        if len(taxid_ens_ids) == 1:
            return both_ens_ids[0].decode()
    if hint_match:
        hint_ens_ids = list(set(rdb.mget(hint_match)))
        if len(taxid_ens_ids) == 1:
            return both_ens_ids[0].decode()
    return 'unmapped-many'