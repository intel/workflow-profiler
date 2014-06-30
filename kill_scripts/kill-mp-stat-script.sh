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
unset mpstat

export me=`whoami`

#  Capture and record the PID of the correct emon 'counter' process:
ps -aef | grep ${me} | awk '{print $2,$8}' | grep 'mpstat' | grep -v 'grep' | grep -v 'kill' | awk '{printf "%8d", $1}' > ./dum_PID_mpstat
sort ./dum_PID_mpstat > ./dum_PID_mpstat.sorted
mpstat_PID_mpstat=`tail -1 ./dum_PID_mpstat.sorted | awk '{printf "%8d", $1}'`
echo "mpstat_PID_mpstat: "${mpstat_PID_mpstat}
# Now kill that process
while read line; do    
  #echo $line    
  kill -s SIGUSR1 ${line}
done < dum_PID_mpstat.sorted
#kill -s SIGUSR1 ${mpstat_PID_mpstat}
rm dum_PID_mpstat*
#    perl ./sar_parser.pl -f ${SARTSV} -o ${SAROUT}.csv &&

