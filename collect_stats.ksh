#################################################################################
# The MIT License (MIT)							        #
# 									        #
# Copyright (c)  2014 Intel Corporation					        #
# 									        #
# Permission is hereby granted, free of charge, to any person obtaining a copy  #
# of this software and associated documentation files (the "Software"), to deal #
# in the Software without restriction, including without limitation the rights  #
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell     #
# copies of the Software, and to permit persons to whom the Software is	        #
# furnished to do so, subject to the following conditions:		        #
# 									        #
# The above copyright notice and this permission notice shall be included in    #
# all copies or substantial portions of the Software.			        #
# 									        #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR    #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,      #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE   #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER        #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, #
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN     #
# THE SOFTWARE.								        #
#################################################################################

FILE_PREFIX=TEST
TAG=$(date +%Y%m%d).$(date +%H%M)
MY_TS=$(date +%Y%m%dD)$(date +%HH%MM%SS)
TARGET_DIRECTORY=~/runs
PROCESSOR=Xeon
SAR_INTERVAL=30
USEPACCT=0
if [ -z "${HOST}" ]
then
    echo "Reading profile..."
    ##source ~/.profile
fi
usage() {
	echo "Usage: collect_stats.ksh <--sar || --free || --iostat || --mpstat || --netstat || --pacct || --proc> <option list>"
	echo " Mandatory options:"
	echo "	-n <FILE_PREFIX>	Common prefix for all files (i.e. nmenoci for test, like QO), default ${FILE_PREFIX}"
	echo "	-l <SLEEP>		Time (in seconds) before steady state"
	echo " sar/iostat options:"
	echo "	-d <SAR_INTERVAL>		Delay for sar in seconds"
	echo " sar common options:"
	echo "	-u <USERS> 		Number of users" 
	echo " proc/sar/iostat/pacct options:"
	echo "	-s <STEADY_STATE>	Length of steady state in minutes"
	echo " output directoy options:"
	echo "	-tag <TAG>	a tag to be added to files and output dir  to make, if not provided script generates one"
	echo "	-td <TARGET_DIRECTORY>	absolute directory where to place the files (i.e. ~/runs/run${TAG}), defaults to current dir"
	exit 3
}
isdigit() {
	[ $# -ge 1 ] || return 3
	
	until [ -z ${1} ]
	do
		case ${1} in
			*[!0-9]*|"") return -1;;
			*) ;; # Do nothing if valid
		esac
		shift
	done
}
name_check() {
	if [ -z ${FILE_PREFIX} ] 
	then
		echo
		echo "FILE_PREFIX is not defined"
		echo
		usage
	fi
}
sleep_check() {
	if [ -z ${SLEEP} ] 
	then
		echo
		echo "SLEEP is not defined"
		echo
		usage
	fi
	if ! isdigit ${SLEEP} 
	then
		echo
		echo "SLEEP is not an integer"
		echo
		usage
	fi
}
sar_delay_check() {
	if [ -z ${SAR_INTERVAL} ] 
	then
		echo
		echo "SAR_INTERVAL is not defined"
		echo
		usage
	fi
	if ! isdigit ${SAR_INTERVAL} 
	then
		echo
		echo "SAR_INTERVAL is not an integer"
		echo
		usage
	fi
}
steady_state_check() {
	if [ -z ${STEADY_STATE} ] 
	then
		echo
		echo "STEADY_STATE is not defined"
		echo
		usage
	fi
	if ! isdigit ${STEADY_STATE} 
	then
		echo
		echo "STEADY_STATE is not an integer"
		echo
		usage
	fi
}
processor_check() {
	if [ -z ${PROCESSOR} ] 
	then
		echo
		echo "PROCESSOR is not defined"
		echo
		usage
	fi
}

users_check() {
	if [ -z ${USERS} ] 
	then
		echo
		echo "USERS is not defined"
		echo
		usage
	fi
	if ! isdigit ${USERS} 
	then
		echo
		echo "USERS is not an integer"
		echo
		usage
	fi
}
param_check() {
	if [ -z ${USESAR} ] && [ -z ${USEPROC} ] && [ -z ${USEIOSTAT} ] && [ -z ${USEPACCT} ]
	then
		echo
		echo "No collections have been defined."
		echo
		usage
	fi
	
	name_check
	# sleep_check
	if [ -n "${USESAR}" ] 
	then
		if [ ${USESAR} != 0 ]
		then
			sar_param_check
		fi
	fi
	if [ -n "${USEPROC}" ] 
	then
		if [ ${USEPROC} != 0 ]
		then
			proc_param_check
		fi
	fi
	
	if [ -n "${USEPACCT}" ]
	then
		if [ ${USEPACCT} != 0 ]
		then
			pacct_param_check
		fi
	fi
	
	if [ -n "${USEMPSTAT}" ] #added
	then
		if [ ${USEMPSTAT} != 0 ]
		then
			mpstat_param_check
		fi
	fi
	if [ -n "${USEFREE}" ] #added
	then
		if [ ${USEFREE} != 0 ]
		then
			free_param_check
		fi
	fi
	if [ -n "${USENETSTAT}" ] #added 1/6
	then
		if [ ${USENETSTAT} != 0 ]
		then
			netstat_param_check
		fi
	fi
}
sar_param_check() {
	sar_delay_check
	steady_state_check
	users_check
}
proc_param_check() {
	steady_state_check
}
iostat_param_check() {
	sar_delay_check
	steady_state_check
	users_check
}
pacct_param_check() {
	steady_state_check
}
mpstat_param_check() { #added
	sar_delay_check
	steady_state_check
	users_check
}
free_param_check() { #added
	sar_delay_check
	steady_state_check
	users_check
}
netstat_param_check() { #added 1/6
	sar_delay_check
	steady_state_check
	users_check
}
read_cli_params() {
	until [ -z ${1} ] # Use all parameters on the command line
	do
		case ${1} in 
			-n) FILE_PREFIX=${2} ;;
			-u) USERS=${2} ;;
			-l) SLEEP=${2} ;;
			-p) PROCESSOR=${2} ;;
			-s) STEADY_STATE=${2} ;;
			-d) SAR_INTERVAL=${2} ;;
			-td) TARGET_DIRECTORY=${2} ;;
			-tag) TAG=${2} ;;
			--sar) USESAR=1
				shift 
				continue ;;
			--proc) USEPROC=1
				shift
				continue ;;
			--iostat) USEIOSTAT=1
				shift
				continue ;;
			--pacct) USEPACCT=1
				shift
				continue ;;
		    --mpstat) USEMPSTAT=1 
			shift
			continue ;;
		    --free) USEFREE=1
			shift
			continue ;;
		    --netstat) USENETSTAT=1 
			shift
			continue ;;
		    --kill-all) KILL_EVERYTHING=1 
			shift
			continue ;;
		    *) echo "bad argument: " $1
			usage ;;
		esac
    # shift moves the command line parameters.
    # Two parameters are used in one loop, so shift has to be called twice.
		shift
		shift
	done
}
create_derived_vars() {
    # this is used by all file names so it must be the first block in this section
        #test for zero length string
	if [ -z "{TAG}"  ] 
	then
	    TAG=$(date +%Y%m%d).$(date +%H%M)
	fi
	TARGET_DIRECTORY=${TARGET_DIRECTORY}/run.${FILE_PREFIX}.${HOST}.${TAG}.${USERS}u
	PATH_PREFIX=""
	if [ -n "{TARGET_DIRECTORY}"  ]
	then
	    mkdir -p ${TARGET_DIRECTORY}
	fi
	PATH_PREFIX=${TARGET_DIRECTORY}/${FILE_PREFIX}.${HOST}.${TAG}.${USERS}u
	#echo "The file prefix is: ${PATH_PREFIX}"
      
	if [ -n "${USESAR}" ]
	then
		if [ ${USESAR} != 0 ]
		then
			create_sar_vars
		fi
	fi
	if [ -n "${USEPROC}" ]
	then
		if [ ${USEPROC} != 0 ]
                then
			create_proc_vars
		fi
	fi
 	if [ -n "${USEIOSTAT}" ]
	then
		if [ $USEIOSTAT} != 0 ]
		then
			create_iostat_vars
		fi
	fi
	
	if [ -n "${USEPACCT}" ]
	then
		if [ ${USEPACCT} != 0 ]
		then
			create_pacct_vars
		fi
	fi
	if [ -z ${SLEEP} ]
	then
		SLEEP=0
	fi
 	if [ -n "${USEMPSTAT}" ] #added
	then
		if [ $USEMPSTAT} != 0 ]
		then
			create_mpstat_vars
		fi
	fi
 	if [ -n "${USEFREE}" ] #added
	then
		if [ $USEFREE} != 0 ]
		then
			create_free_vars
		fi
	fi
 	if [ -n "${USENETSTAT}" ] #added 1/6
	then
		if [ $USENETSTAT} != 0 ]
		then
			create_netstat_vars
		fi
	fi
}
create_sar_vars() {
	export SAROUT=${PATH_PREFIX}.${SAR_INTERVAL}s.sar
	export SARDATA=${SAROUT}.data
	export SARTSV=${SAROUT}.tsv
	SAR_ITERATIONS=$(((SLEEP+STEADY_STATE)*60/SAR_INTERVAL))
}

create_proc_vars() {
	RUNTIME=$((SLEEP+STEADY_STATE))
	PROCOUT=${PATH_PREFIX}
}
create_pacct_vars() {
	RUNTIME=$((SLEEP+STEADY_STATE))
}
create_iostat_vars() {
	IOSTAT_OUT=${PATH_PREFIX}.${SAR_INTERVAL}s.iostat
	echo "iostat out: [${IOSTAT_OUT}]"
	IOSTAT_ITERATIONS=$(((SLEEP+STEADY_STATE)*60/SAR_INTERVAL))
}
create_mpstat_vars() { #added
	MPSTAT_OUT=${PATH_PREFIX}.${SAR_INTERVAL}s.mpstat
	echo "mpstat out: [${MPSTAT_OUT}]"
	MPSTAT_ITERATIONS=$(((SLEEP+STEADY_STATE)*60/SAR_INTERVAL))
}
create_free_vars() { #added
	FREE_OUT=${PATH_PREFIX}.${SAR_INTERVAL}s.free
	echo "free out: [${FREE_OUT}]"
}
create_netstat_vars() { #added 1/6
	NETSTAT_OUT=${PATH_PREFIX}.${SAR_INTERVAL}s.netstat
	echo "netstat out: [${NETSTAT_OUT}]"
}
start_collection() {
	if [ -n "${USESAR}" ]
	then
		if [ ${USESAR} != 0 ]
                then
			collect_sar
		fi
	fi

	if [ -n "${USEPROC}" ]
	then
		if [ ${USEPROC} != 0 ]
                then
			collect_proc
		fi
	fi
	
	if [ -n "${USEIOSTAT}" ]
	then
		if [ ${USEIOSTAT} != 0 ]
		then
			collect_iostat
		fi
	fi
	
	if [ -n "${USEPACCT}" ]
	then
		if [ ${USEPACCT} != 0 ]
		then
			collect_pacct
		fi
	fi
	if [ -n "${USEMPSTAT}" ] #added
	then
		if [ ${USEMPSTAT} != 0 ]
		then
			collect_mpstat
		fi
	fi
	if [ -n "${USEFREE}" ] #added
	then
		if [ ${USEFREE} != 0 ]
		then
			collect_free
		fi
	fi
  
	if [ -n "${USENETSTAT}" ] #added 1/6
	then
		if [ ${USENETSTAT} != 0 ]
		then
			collect_netstat
		fi
	fi

	if [ -n "${USENETSTAT}" ] #added 1/6
	then
		if [ ${USENETSTAT} != 0 ]
		then
			collect_netstat
		fi
	fi

	if [ -n "${KILL_EVERYTHING}" ] #added 1/6
	then
		if [ ${KILL_EVERYTHING} != 0 ]
		then
			kill_all
		fi
	fi
}
kill_all() {
  for file in kill_scripts/*.sh; do
    echo $file
    ./"$file"
  done
}
collect_sar() {
    updTS &&
    echo "Starting sar collection at ${MY_TS}..." &&
    sar -A -o ${SARDATA} ${SAR_INTERVAL} >/dev/null 2>&1 &&
    echo "sar collection complete at ${MY_TS}" &
}
updTS() {
    MY_TS=$(date +%Y%m%dD)$(date +%HH%MM%SS)
}
printTS() {
    updTS
    echo "Current time" $MY_TS
}
collect_proc() {
	echo "Starting proc collection..." &&
	cat /proc/cpuinfo > ${PROCOUT}.proc_before.txt &&
	cat /proc/meminfo >> ${PROCOUT}.proc_before.txt &&
	cat /proc/modules >> ${PROCOUT}.proc_before.txt &&
	cat /proc/partitions >> ${PROCOUT}.proc_before.txt &&
	cat /proc/mounts >> ${PROCOUT}.proc_before.txt &&
	cat /proc/swaps >> ${PROCOUT}.proc_before.txt &&
	cat /proc/interrupts >> ${PROCOUT}.proc_before.txt &&
	#
	numactl --hardware >> ${PROCOUT}.proc_before.txt &&
	numactl --show >> ${PROCOUT}.proc_before.txt &
	sleep ${RUNTIME}s &&
	cat /proc/cpuinfo > ${PROCOUT}.proc_after_${RUNTIME}.txt &&
	cat /proc/meminfo >> ${PROCOUT}.proc_after_${RUNTIME}.txt &&
	cat /proc/modules >> ${PROCOUT}.proc_after_${RUNTIME}.txt &&
	cat /proc/partitions >> ${PROCOUT}.proc_after_${RUNTIME}.txt &&
	cat /proc/mounts >> ${PROCOUT}.proc_after_${RUNTIME}.txt &&
	cat /proc/swaps >> ${PROCOUT}.proc_after_${RUNTIME}.txt &&
	cat /proc/interrupts >> ${PROCOUT}.proc_after_${RUNTIME}.txt &&
	numactl --hardware >> ${PROCOUT}.proc_after_${RUNTIME}.txt &&
	numactl --show >> ${PROCOUT}.proc_after_${RUNTIME}.txt &
	echo "PROC collection complete" &
}
collect_iostat() {
    updTS &&
    echo "Starting iostat collection...[${IOSTAT_OUT}] at ${MY_TS}" &&
    iostat -xt ${SAR_INTERVAL} > ${IOSTAT_OUT} &&
    echo "iostat collection complete at ${MY_TS}" &
}
collect_pacct() {
	echo "Start process accounting..." &&
	touch /var/log/pacct_${TAG} &&
	accton /var/log/pacct_${TAG} && 
	sleep ${RUNTIME}m &&
	accton &&
	lastcomm -f /var/log/pacct_${TAG} > pacct_${TAG}.txt &
}
collect_mpstat() { #added
    updTS &&
    echo "Starting mpstat collection...[${MPSTAT_OUT}] at ${MY_TS}" &&
    mpstat -P ALL ${SAR_INTERVAL} > ${MPSTAT_OUT} &&
    echo "mpstat collection complete at ${MY_TS}" &
}
collect_free() { #added 1/6
    echo "hi" ${FREE_OUT}
    updTS &&
    echo "Starting free collection...[${FREE_OUT}] at ${MY_TS}" &&
    free -ms ${SAR_INTERVAL} > ${FREE_OUT} &&
    echo "free collection complete at ${MY_TS}" &
}
collect_netstat() { #added 1/6
    updTS &&
    echo "Starting netstat collection...[${NETSTAT_OUT}] at ${MY_TS}" &&
    netstat -tuc ${SAR_INTERVAL} > ${NETSTAT_OUT} &&
    echo "netstat collection complete at ${MY_TS}" &
}
read_cli_params ${@}
param_check
create_derived_vars
start_collection
