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

from collections import OrderedDict

"""
The user needs to add their own dictionary here. 

The step names for the dictionary should match the stage names in the 
workflow script. 

For example: if there exists run..stage1.* , run..stage2.* and run..stage3.* 
folders, the dictionary would be constructed as in the example provided 
below for sample data. 
"""

# This dictionary is used to test the existing sample data
sample_dict = OrderedDict([('Stage1', 'stage1'), 
                           ('Stage2','stage2'), 
                           ('Stage3','stage3')])

"""
unordered dictionary for parsing workflow input parameter to one of the above 
workflow dictionaries

Format is:
   'workflowName': 'name_of_dictionary'

The workflowName will be what is entered on the command line with the -N 
option,the name_of_dictionary is the name of the OrderedDict you have defined 
above
"""

# If you add a new dictionary above, be sure to update this dictionary based on
# the example format provided. 
workflow_parse_dict = {
    'sample': 'sample_dict',
}
