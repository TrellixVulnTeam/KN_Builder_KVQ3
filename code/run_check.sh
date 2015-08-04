#!/bin/bash

LOCAL_BASE="/mnt/users/blatti/apps/P1_source_check/"   # toplevel local directory inside runner of this script
#LOCAL_BASE="/shared/"   # when called by container like check_master
CLOUD_BASE="/mnt/storage/blatti/apps/P1_source_check/"   # toplevel directory on cloud

CMD1="sh -c 'cd TMPBASEcode/; /usr/bin/time -v python3 TMPSRC.py;'" # command for current step of pipeline
CMD2="sh -c 'cd TMPBASEcode/; /usr/bin/time -v python3 TMPSRC.py; run_fetch.sh TMPSRC'" # command for current and next step of pipeline

RUN_TYPE="CLOUD" # LOCAL, CONTAIN, CLOUD
CMD_TYPE="STEP"  # STEP or PIPELINE

IMG="cblatti3/python3:0.1" 
ctr=1
CURL="curl -i -L -H 'Content-Type: application/json' -X POST -d@$LOCAL_BASE/jobs/check_TMPNUM_TMPSRC.json mmaster02.cse.illinois.edu:4400/scheduler/iso8601"

CMD=$CMD1
if [ "$CMD_TYPE" == "PIPELINE" ]; then
	CMD=$CMD2;
fi

echo "$RUN_TYPE $CMD_TYPE $LOCAL_BASE"
mkdir -p $LOCAL_BASE/raw_downloads/

## loop through all sources
for i in `ls $LOCAL_BASE/code/*.py | sed -e 's/.py//g' | sed "s#$LOCAL_BASE/code/##g" | sort`; do  
	echo "$i"
	
	# skip non-source specific files
	if [ "$i" == "utilities" ]; then
		continue;
	fi

	if [ "$RUN_TYPE" == "LOCAL" ]; then
		LOCAL_CMD=$(echo $CMD | sed "s#TMPBASE#$LOCAL_BASE#g" | sed -e "s/TMPSRC/$i/g")
		echo $LOCAL_CMD
		#eval $LOCAL_CMD
	fi

	if [ "$RUN_TYPE" == "CONTAIN" ]; then
		CONTAIN_CMD=$(echo "docker rm check_TMPNUM_TMPSRC; docker run --name check_TMPNUM_TMPSRC -d -v $LOCAL_BASE/code/:/code/ -v $LOCAL_BASE/raw_downloads/:/raw_downloads/ $IMG $CMD" | sed -e "s/TMPNUM/$ctr/g" | sed "s#TMPBASE#/#g" | sed -e "s/TMPSRC/$i/g")
		echo $CONTAIN_CMD
		#eval $CONTAIN_CMD
	fi

	if [ "$RUN_TYPE" == "CLOUD" ]; then
		mkdir -p $LOCAL_BASE/jobs/
		cat $LOCAL_BASE/check_template.json | sed "s#IMG#$IMG#g" | sed "s#TMPCMD#$CMD#g" | sed "s#TMPBASE#/#g" | sed "s#CLOUDBASE#$CLOUD_BASE#g" | sed -e "s/TMPSRC/$i/g" | sed -e "s/TMPNUM/$ctr/g" > $LOCAL_BASE/jobs/check\_$ctr\_$i.json;
		CLOUD_CMD=$(echo $CURL | sed -e "s/TMPNUM/$ctr/g" | sed -e "s/TMPSRC/$i/g")
		echo $CLOUD_CMD
		#eval $CLOUD_CMD
	fi

	ctr=$(($ctr + 1))

done;