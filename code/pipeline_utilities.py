"""Utiliites for running single or multiple steps of the pipeline either locally or on the cloud.

Classes:

Functions:
    run_local_check(run_mode) -> : takes a run_mode string 'STEP' or 'PIPELINE'.  Runs all necessary checks.  If 'PIPELINE', calls next step
    run_local_fetch(run_mode) -> : takes a run_mode string 'STEP' or 'PIPELINE'.  Runs all necessary fetches.  If 'PIPELINE', calls next step
    run_local_table(run_mode) -> : takes a run_mode string 'STEP' or 'PIPELINE'.  Runs all necessary tables on chunks.  If 'PIPELINE', calls next step

Variables:
"""

from argparse import ArgumentParser
import config_utilities as cf
import json
import os
import re
import traceback

DEFAULT_START_STEP = 'CHECK'
DEFAULT_DEPLOY_LOC = 'LOCAL'
DEFAULT_RUN_MODE = 'STEP'
POSSIBLE_STEPS = ['CHECK', 'FETCH', 'TABLE']
CHECK_PY = "check_utilities"
FETCH_PY = "fetch_utilities"
TABLE_PY = "table_utilities"

def parse_args():
    """Processes command line arguments.

    Expects three positional arguments(start_step, deploy_loc, run_mode) and a number of optional arguments. If argument is missing, supplies default value.
    Returns: args as populated namespace
    """
    parser = ArgumentParser()
    parser.add_argument('start_step', help='select start step, must be CHECK, FETCH, or TABLE ', default=DEFAULT_START_STEP)
    parser.add_argument('deploy_loc', help='select deployment type, must be LOCAL or CLOUD ', default=DEFAULT_DEPLOY_LOC)
    parser.add_argument('run_mode', help='select run mode, must be STEP or PIPELINE', default=DEFAULT_RUN_MODE)
    parser.add_argument('-i', '--image', help='docker image name for pipeline', default=cf.DEFAULT_DOCKER_IMG)
    parser.add_argument('-c', '--chronos', help='url of chronos scheduler', default=cf.DEFAULT_CURL_URL)
    parser.add_argument('-ld', '--local_dir', help='name of toplevel directory on local machine', default=cf.DEFAULT_LOCAL_BASE)    
    parser.add_argument('-cd', '-cloud_dir-', help='name of toplevel directory on cloud storage', default=cf.DEFAULT_CLOUD_BASE)    
    parser.add_argument('-cp', '--code_path', help='relative path of code directory from toplevel ', default=cf.DEFAULT_CODE_PATH)    
    parser.add_argument('-dp', '--data_path', help='relative path  of data directory from toplevel', default=cf.DEFAULT_DATA_PATH)    
    args = parser.parse_args()
    return args

def run_local_check(args):
    
    local_code_dir = args.local_dir + os.sep + args.code_path
    os.chdir(local_code_dir)
    ctr = 0
    successful = 0 
    failed = 0
    for filename in sorted(os.listdir(local_code_dir)):
        if not filename.endswith(".py"): continue
        if 'utilities' in filename:
            continue;

        ctr += 1;
        module = os.path.splitext(filename)[0]
        print(str(ctr) + "\t" + module)
        
        try:
            checker = __import__(CHECK_PY)
            checker.check(module)
            successful += 1
        except Exception as e:
            print ("ERROR: " + module + " could not be run")
            print ("Message: " + str(e))
            print (traceback.format_exc())
            failed += 1
        
    print ("CHECK FINISHED. Successful: {0}, Failed: {1}".format(successful, failed))
    if(args.run_mode == "PIPELINE"):
        run_local_fetch(args)

def run_local_fetch(args):
    
    local_code_dir = os.path.join(args.local_dir, args.code_path)
    os.chdir(local_code_dir)
    fetcher = __import__(FETCH_PY)
    local_data_dir = os.path.join(args.local_dir, args.data_path)
    os.chdir(local_data_dir)
    ctr = 0
    successful = 0 
    failed = 0
    for src_name in sorted(os.listdir(local_data_dir)):
        print(src_name)
        for alias_name in sorted(os.listdir(os.path.join(local_data_dir, src_name))):
            print(str(ctr) + "\t" + alias_name)
            alias_dir = os.path.join(local_data_dir, src_name, alias_name)
            if not os.path.isfile(os.path.join(alias_dir, "file_metadata.json")):
                continue

            os.chdir(alias_dir)
            ctr += 1;
            fetcher.main("file_metadata.json")
            successful += 1

    print ("FETCH FINISHED. Successful: {0}, Failed: {1}".format(successful, failed))
    if(args.run_mode == "PIPELINE"):
        run_local_table(args)

def run_local_table(args):
    
    local_code_dir = os.path.join(args.local_dir, args.code_path)
    os.chdir(local_code_dir)
    tabler = __import__(TABLE_PY)
    local_data_dir = os.path.join(args.local_dir, args.data_path)
    os.chdir(local_data_dir)
    ctr = 0
    successful = 0 
    failed = 0
    for src_name in sorted(os.listdir(local_data_dir)):
        print(src_name)
        for alias_name in sorted(os.listdir(os.path.join(local_data_dir, src_name))):
            print("\t" + alias_name)
            alias_dir = os.path.join(local_data_dir, src_name, alias_name)
            if not os.path.isfile(os.path.join(alias_dir, "file_metadata.json")):
                continue
            os.chdir(alias_dir)
            for chunk_name in sorted(os.listdir(os.path.join(alias_dir, "chunks"))):
                if "rawline" not in chunk_name:
                    continue
                print(str(ctr) + "\t\t" + chunk_name)
                chunkfile = os.path.join("chunks", chunk_name)
                ctr += 1;
                tabler.main(chunkfile, "file_metadata.json")
                successful += 1

    print ("TABLE FINISHED. Successful: {0}, Failed: {1}".format(successful, failed))
    if(args.run_mode == "PIPELINE"):
        pass


def run_cloud_check(args):
    pass;

def run_cloud_fetch(args):
    pass;

def run_cloud_table(args):
    pass;


def main():
    """Runs the 'start_step' step of the pipeline on the 'deploy_loc' local or cloud location, and all subsequent steps if PIPELINE 'run_mode'

    Parses the arguments and runs the specified part of the pipeline using the specifice local or cloud resources.

    Args:

    Returns:
    """
    
    args = parse_args()
    if not args.run_mode == 'PIPELINE' and not args.run_mode == 'STEP':
        print(args.run_mode + ' is an unacceptable run_mode.  Must be STEP or PIPELINE')
        return

    if args.deploy_loc == 'LOCAL':
        if args.start_step == 'CHECK':
            run_local_check(args)       
        elif args.start_step == 'FETCH':
            run_local_fetch(args)       
        elif args.start_step == 'TABLE':
            run_local_table(args)       
        else:
            print(args.start_step + ' is an unacceptable start_step.  Must be ' + str(POSSIBLE_STEPS))
            return

    elif args.deploy_loc == 'CLOUD':
        if args.start_step == 'CHECK':
            run_cloud_check(args)       
        elif args.start_step == 'FETCH':
            run_cloud_fetch(args)       
        elif args.start_step == 'TABLE':
            run_cloud_table(args)       
        else:
            print(args.start_step + ' is an unacceptable start_step.  Must be ' + str(POSSIBLE_STEPS))
            return
    
    else:
        print(args.deploy_loc + ' is an unacceptable deploy_loc.  Must be LOCAL or CLOUD')
        return

    return


if __name__ == "__main__":
    main()
