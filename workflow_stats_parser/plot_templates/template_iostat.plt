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

clear
reset

print "cpu time spent waiting on read and write"
set terminal pngcairo transparent enhanced font "arial,25" fontscale 1.0 size 1920, 1080
set key outside bottom center box title "Workflow phase(s)" enhanced
set key maxrows 4
set key font ",25" spacing 1 samplen 2.9 width 2 height 1
set xlabel "Time (hours)" font ",25"
set ylabel "milliseconds" font ",25"

set output "/post_processed_stats/output_io_waittime_per_phase_plot.png"
set title "IO Wait per Phase (ms)\n{/*0.5 <subtitle>}" font ",35"
set datafile separator ","
set timefmt "%Y-%m-%d %H:%M:%S"
set ytics font ",25"

set style line 1 lt 1 lc rgb "red" lw 4
set style line 2 lt 1 lc rgb "orange" lw 4
set style line 3 lt 1 lc rgb "brown" lw 4
set style line 4 lt 1 lc rgb "green" lw 4
set style line 5 lt 1 lc rgb "cyan" lw 4
set style line 6 lt 1 lc rgb "blue" lw 4
set style line 7 lt 1 lc rgb "violet" lw 4
set style line 8 lt 1 lc rgb "brown" lw 4
set style line 9 lt 1 lc rgb "green" lw 4
set style line 10 lt 1 lc rgb "cyan" lw 4
set style line 11 lt 1 lc rgb "red" lw 4
set style line 12 lt 1 lc rgb "violet" lw 4
show style line
starting_time = 37794

offset = 0
t0(x)=(offset=($0==0) ? x : offset, x - offset)

plot "/post_processed_stats/2014-03-03_13.29.19_iostat.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 1 t "bwa aln 1" with lines, \
  '' using ((timecolumn(3)-offset)/3600):4 every ::3 ls 2 t "bwa aln 2" with lines, \
  '' using ((timecolumn(5)-offset)/3600):6 every ::3 ls 3 t "sampe" with lines
