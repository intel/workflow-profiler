#!/bin/bash
#################################################################################
# The MIT License (MIT)                                                         #
#                                                                               #
# Copyright (c)  2014 Intel Corporation                                         #
#                                                                               #
# Permission is hereby granted, free of charge, to any person obtaining a copy  #
# of this software and associated documentation files (the "Software"), to deal #
# in the Software without restriction, including without limitation the rights  #
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell     #
# copies of the Software, and to permit persons to whom the Software is         #
# furnished to do so, subject to the following conditions:                      #
#                                                                               #
# The above copyright notice and this permission notice shall be included in    #
# all copies or substantial portions of the Software.                           #
#                                                                               #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR    #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,      #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE   #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER        #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, #
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN     #
# THE SOFTWARE.                                                                 #
#################################################################################

unset me
unset sar_PID

export me=`whoami`
#echo $SARDATA
#  Capture and record the PID of the correct sar 'counter' process:
#ps -aef | grep ${me} | grep 'sar ' | grep -v 'grep' | grep -v 'kill' | awk '{printf "%8d", $2}' > ./dum_PID_sar
ps -aef | grep ${me} | awk '{print $2,$8}' | grep 'sar' | grep -v 'grep' | grep -v 'kill' | awk '{printf "%8d", $1}' > ./dum_PID_sar

sort ./dum_PID_sar > ./dum_PID_sar.sorted
sar_PID=`tail -1 ./dum_PID_sar.sorted | awk '{printf "%8d", $1}'`
echo "sar_PID: "${sar_PID}
while read line; do    
  #echo $line
  kill -s SIGUSR1 ${line}
done < dum_PID_sar.sorted

# Now kill that process
#kill -s SIGUSR1 ${sar_PID}
rm dum_PID_sar*
#sadf -p ${SARDATA} -- -A > ${SARTSV}  
#perl /opt/sar_parser.pl -f ${SARTSV} -o ${SAROUT}.csv 
