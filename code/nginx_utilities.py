#!/usr/bin/env python3

"""Utiliites for interacting with the KnowEnG Nginx db through python.

Contains module functions::

    get_database(args=None)
    import_ensembl(alias, args=None)
    conv_gene(rdb, foreign_key, hint, taxid)
    import_mapping(map_dict, args=None)

"""

import config_utilities as cf
import json
import os
from argparse import ArgumentParser
import subprocess

def deploy_container(args=None):
    """Deplays a container with marathon running nginx using the specified
    args.
    
    This replaces the placeholder args in the json describing how to deploy a 
    container running Nginx with those supplied in the users arguements.
    
    Args:
        args (Namespace): args as populated namespace or 'None' for defaults
    """
    if args is None:
        args=cf.config_args()
    deploy_dir = os.path.join(args.local_dir, 'marathon_jobs')
    if not os.path.exists(deploy_dir):
        os.makedirs(deploy_dir)
    template_job = os.path.join(args.local_dir, args.code_path, 
                                'dockerfiles', 'marathon', 'nginx.json')
    with open(template_job, 'r') as infile:
        deploy_dict = json.load(infile)
    deploy_dict["id"] = "p1nginx-" + args.nginx_port
    deploy_dict["container"]["volumes"][0]["hostPath"] = args.nginx_dir
    conf_path = os.path.join(args.cloud_dir, args.code_path, 'nginx', args.nginx_conf)
    deploy_dict["container"]["volumes"][1]["hostPath"] = conf_path
    deploy_dict["container"]["docker"]["portMappings"][0]["hostPort"] = int(args.nginx_port)
    out_path = os.path.join(deploy_dir, "p1nginx-" + args.nginx_port +'.json')
    with open(out_path, 'w') as outfile:
        outfile.write(json.dumps(deploy_dict))
    job= 'curl -X POST -H "Content-type: application/json" ' + args.marathon + " -d '"
    job += json.dumps(deploy_dict) + "'"
    if not args.test_mode:
        try:
            subprocess.check_output(job, shell=True)
        except subprocess.CalledProcessError as ex1:
            print(ex1.output)
    else:
        print(job)

def main():
    """Deploy a Nginx container using marathon with the provided command line
    arguements. 
    
    This uses the provided command line arguments and the defaults found in 
    config_utilities to launch a Nginx docker container using marathon.
    """
    parser = ArgumentParser()
    parser = cf.add_config_args(parser)
    args = parser.parse_args()
    deploy_container(args)
    
if __name__ == "__main__":
    main()