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
print "average utilization across many cores"
set terminal pngcairo transparent enhanced font "arial,25" fontscale 1.0 size 1920, 1080
set key outside bottom center box title "Workflow Phase(s)" enhanced
set key maxrows 4
set key font ",25" spacing 1 samplen 2.9 width 2 height 1
set xlabel "Time (hours)" font ",25"
set ylabel "Utilization (%)" font ",25"

set output "/post_processed_stats/output_many_cores_utilization_plot.png"
set title "Average CPU Utilization (%) Across All Cores per Phase\n{/*0.5 <subtitle>}" font ",35"
set datafile separator ","
#set xdata time
set timefmt "%Y-%m-%d %H:%M:%S"
#set xtics format "%d:%H:%M" font ",25"
set ytics font ",25"

set style line 1 lt 1 lc rgb "red" lw 4
set style line 2 lt 1 lc rgb "orange" lw 4
set style line 3 lt 1 lc rgb "brown" lw 4
set style line 4 lt 1 lc rgb "green" lw 4
set style line 5 lt 1 lc rgb "cyan" lw 4
set style line 6 lt 1 lc rgb "blue" lw 4
set style line 7 lt 1 lc rgb "violet" lw 4
set style line 8 lt 1 lc rgb "yellow" lw 4
set style line 9 lt 1 lc rgb "green" lw 4
set style line 10 lt 1 lc rgb "cyan" lw 4
set style line 11 lt 1 lc rgb "red" lw 4
set style line 12 lt 1 lc rgb "violet" lw 4

show style line

offset = 0
starting_time = 56309
t0(x)=(offset=($0==0) ? x : offset, x - offset)

plot "/tmp/tmpAe1agT/0TkGIar.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 1 t "core 0" with lines,\
 "/tmp/tmpAe1agT/1v8mw8f.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 2 t "core 1" with lines,\
 "/tmp/tmpAe1agT/2Swc4Sc.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 3 t "core 2" with lines,\
 "/tmp/tmpAe1agT/3qR_gQy.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 4 t "core 3" with lines,\
 "/tmp/tmpAe1agT/40rZ_Ic.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 5 t "core 4" with lines,\
 "/tmp/tmpAe1agT/5FTDVgU.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 6 t "core 5" with lines,\
 "/tmp/tmpAe1agT/6F6F_zO.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 7 t "core 6" with lines,\
 "/tmp/tmpAe1agT/7asjTV4.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 8 t "core 7" with lines,\
 "/tmp/tmpAe1agT/8855lJ8.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 9 t "core 8" with lines,\
 "/tmp/tmpAe1agT/9fqP1w1.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 10 t "core 9" with lines,\
 "/tmp/tmpAe1agT/1090Xii2.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 11 t "core 10" with lines,\
 "/tmp/tmpAe1agT/11PFh16_.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 12 t "core 11" with lines,\
 "/tmp/tmpAe1agT/126wQeVe.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 13 t "core 12" with lines,\
 "/tmp/tmpAe1agT/13fqpjE9.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 14 t "core 13" with lines,\
 "/tmp/tmpAe1agT/14KGGIBO.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 15 t "core 14" with lines,\
 "/tmp/tmpAe1agT/15Sx9Drj.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 16 t "core 15" with lines,\
 "/tmp/tmpAe1agT/164oMqDB.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 17 t "core 16" with lines,\
 "/tmp/tmpAe1agT/17BIAj2P.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 18 t "core 17" with lines,\
 "/tmp/tmpAe1agT/18TsOhwO.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 19 t "core 18" with lines,\
 "/tmp/tmpAe1agT/19WZ68jG.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 20 t "core 19" with lines,\
 "/tmp/tmpAe1agT/206mkNTa.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 21 t "core 20" with lines,\
 "/tmp/tmpAe1agT/21b7fxzo.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 22 t "core 21" with lines,\
 "/tmp/tmpAe1agT/229mBLIJ.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 23 t "core 22" with lines,\
 "/tmp/tmpAe1agT/23iWPP89.csv" using (t0(timecolumn(1))/3600):2 every ::3 ls 24 t "core 23" with line
