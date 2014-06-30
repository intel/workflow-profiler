#!/usr/bin/env python
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

"""
    FILE:    workflow_stats_parser.py 

    VERSION: 0.1 

    PURPOSE:  parses single or multi-stage workflow profile files and outputs 
              per-stage csv files and optional graph plots of the profile data.
              See README file for more details

    USAGE:
    workflow_stats_parser.py root [-N workflow_name] \
                            [-S substring] [-h] [-o pathToOuputFolder] \
                            [-i | -s | -A] [-w size] [-t tag] [-p] [-l level] 
     
    root                  The path to the workflow output directory

    -h                    Prints out usage information
   
    -N, --workflow_name workflow_name
                          Enter a known workflow name.
                          The default is 'sample'.

    -S, --single_step s   A substring for use when post-processing a single
                           step of a workflow. The substring must be present in 
                           the directory name containing the stage output. 

    -o, --output          Path to output folder for post-processed data files.
                          Creates folder if does not exist.  Default directory
                          is 'post_processed_stats' in the run directory. 

    -i, --iostat          Parse iostat metrics 
    -s, --sar             Parse sar metrics 
    -A, --all             Parse all metrics

    -w, --window n        n is the size of the window, in seconds, to use for 
                            smoothing graphs, default=100

    -t  --tag tag         A name that is added to the plots which identifes the
                          data set.
    
    -p, --plot            Plot the data using gnuplot

    -l, --level           Enter log level.
                          Default is info.
  

    REQUIREMENTS: 
    1. GNU plot for graphing 4.6.x.  We have run our tests on version 4.6.3 and 4.6.4 

    2. Python, version 2.6.x - 2.7.x. We have tested with 2.6.6 

    INPUT: one directory ('root') which contains sub-directories for each
           workflow stage to post-process

    OUTPUT: a set of csv files and corresponding gnuplot plots (if -p option)

    REFERENCE:
        POSSIBLE_METRICS:
            iostat
            sar
            sar_reads
            sar_writes
"""

from __future__ import division
from glob import glob
from datetime import datetime
from sys import platform as _platform
from datetime import timedelta
from subprocess import call
from shutil import rmtree
from tempfile import mkdtemp, mkstemp
from itertools import izip_longest
from itertools import izip
from pprint import pprint
from contextlib import contextmanager
import multiprocessing
import traceback
import sys
import csv
import re
import errno
import os
import logging
import time
import json
import inspect  #  - introspection for debugging only! 
import argparse 
import numpy
from collections import OrderedDict

# This will import all the workflow dictionaries
from workflow_dictionaries import *

# Possible values:
# warning - Important messages that aren't an error
# error - For routine event that might be of interest
# debug - For messages useful to debugging. Dumping variables and so on 
# none - Don't log anything
LOG_TO_SCREEN = False

# Maps the command line option to the logging level
LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO
}


##START DO NOT MODIFY LIST - these are globals, not intended to be modified
MULTITHREAD_PARSER_OUTPUT_DIR = "multithreading_stats"  # rlk -only needed fo mpstat support
OUTPUT_DEFAULT_DIR = "./post_processed_stats"  # the default output directory path
OUTPUT_DIR_NAME = ''
#MEASURE_INTERVAL = 30
PL = ''  # to store the workflow name
ARGS_NS = None

# Folder that contains the .plt templates
TEMPLATE_DIR = "plot_templates"

## For single step support - not used currently
single_step_dict = OrderedDict([])

##END DO NOT MODIFY LIST 


def main(argv=None):
    """
    PURPOSE: The entry point for the program. First receives, parses, and 
             validates arguments; and then calls the work method.
        
    INPUTS:
       argv - a list holding the command line user arguments
        
    OUTPUTS: Nothing on success. If non-recoverable error, exits program. 
    
    ALGORITHM (the steps):
        1. Capture arguments
        2. Parse arguments
        3. Validate arguments
        4. Post-process 
        
    CALLEES: 
    """

    ## 1. get arguments from sys.argv
    if argv is None:
        argv = sys.argv[1:]  # strip out the program name

    # create object for handling user input
    input = UserInput() 

    ## 2. parse arguments
    args = input.parse_args(argv)  # parse arguments

    # The logger is created in input.parse_args(). We grab it for use in main()
    logger = input.logger
    logger.info("=== Starting parser at {0}".format(time.strftime("%Y-%m-%d %H:%M:%S")))
    logger.info("Logging level set to {0}".format(args.log))

    ## 3. validate arguments 
    check_list = input.check_args(args)
    if check_list[1] is None:
        logger.error("MAIN::Error found when checking user specified arguments")
        logger.error("      Exiting now.")
        sys.exit(1)
    
    print ("main::Arguments are valid")
    
    args = check_list[1]  # update main's args namespace 

    ## 4. do work
    try:
        post_process_rc = input.post_process(args)
    # Catch all exceptions that aren't handled elsewhere
    except Exception, e:
        traceback.print_exc()
        print ("MAIN::Error while post processing.")
        #print("MAIN::Error found while post processing. Cleaning up.")
        #cleanup(args)
        sys.exit(1)

    print ("main::All done! Exiting now")
##end main


def cleanup(args):
    """
    PURPOSE: Cleans up the output dir if there has been an error 
    
    INPUTS: args: The arguments namespace
    
    OUTPUTS: None
    
    CALLEES: main()
    """
    # Remove output dir
    print("Removing the the output directory: %s" % args.output)
    rmtree(args.output)


def who_called():
    """"
    PURPOSE: This is a debugging helper function to retrieve the
             the calling function's name.  It uses the inspect
             module for introspection of the call stack

    INPUTS:  none

    OUTPUTS: caller name as a string

    CALLEES: only for debugging, do not fill this in now
    """
    
    cf = inspect.currentframe()
    caller = inspect.getouterframes(cf)
    #for item in caller:
    #    print item
    #caller = inspect.getouterframes(cf,2)[1][4]
    caller = inspect.getouterframes(cf, 2)
    print('caller name: ', caller[1][5])
    #print ("who_called:: caller \'%s\'" % (caller))
   
    #return caller


def setup_logger(output_folder, log_level):
    # create logger
    logger = logging.getLogger(__file__)
    logger.setLevel(log_level)

    log_format = logging.Formatter('%(funcName)s:%(lineno)d - %(levelname)s - %(message)s')

    if LOG_TO_SCREEN:
        # A StreamHandler without arguments defaults to stderr
        stderr_handler = logging.StreamHandler()
        stderr_handler.setLevel(log_level)
        stderr_handler.setFormatter(log_format)

        logger.addHandler(stderr_handler)

    # Make sure the output folder exists
    parser_log_filename = 'parser.log'
    if output_folder:
        try:
            os.mkdir(output_folder)
        except: pass
        parser_log_filename = os.path.join(output_folder, parser_log_filename)

    file_handler = logging.FileHandler(parser_log_filename)
    file_handler.setLevel(log_level)
    # create a formatter and set the formatter for the handler.
    file_handler.setFormatter(log_format)
    # add the Handler to the logger
    logger.addHandler(file_handler)

    return logger


#------------------------------
# Data storage
#------------------------------
class InputOutput ():
    """
    PURPOSE: Manages writing to files and getting file info.
    
    ATTRIBUTES: None
    
    ORIGINAL DATE, VERSION:
    
    CHANGE LOG:
    
    CURRENT VERSION:
        
    """

    def __init__(self, logger):
        self.logger = logger
    
    # Get the data from a file!
    def get_data_for_one_step (self, step_path='path/to/step', metric=''):
        """
        PURPOSE: Gets the text of the log file for one metric (iostat, sar, ...) 
            and step in a workflow
        
        INPUTS:
            root_name: path to the folder that holds the log files -- old name for step_path

            step_path: path to dir that holds the step's log files

            metric: the metric we need to retrieve from the log files

        OUTPUTS: Returns the log file text as a list of lines
        
        ALGORITHM: If it's sar data we must decode it first
        
        CALLEES: InputOutput.get_data_for_each_step()
            
        """
        sub_dirlist = os.listdir (step_path)

        # We want specific output files for active_mem/active_core
        if metric == 'active_mem' or "sar" in metric:
            search_term = 'sar'
        elif metric == 'mpstat_active_core' or metric == 'mpstat_total_core':
            search_term = 'mpstat'
        else:
            search_term = metric

        target_file = None
        data = None
        
        for filename in sub_dirlist:
            if search_term in filename and "decoded" not in filename:
                target_file = filename
        if not target_file:
            raise Exception("Can't find file for {0} in input data folder".format(search_term))

        target_file = os.path.join (step_path, target_file)

        # todo: implement reflection so I don't have to do all these checks
        if metric == 'sar' and "linux" in _platform:
            target_file = self.decode_data (target_file, step_path, "decoded_cpu_sr.txt")

        if "sar_" in metric and "linux" in _platform:
            target_file = self.decode_data (target_file, step_path, "decoded_io_sr.txt", '-b')

        if metric == 'active_mem' and "linux" in _platform:
            target_file = self.decode_data (target_file, step_path, "decoded_active_mem_sr.txt", "-r")

        elif metric == 'active_mem':
            return self.get_data_for_one_step (step_path, "active_mem")

        with open (target_file, 'r') as old_data:
            data = old_data.readlines ()
        if "decoded" in target_file:
            os.remove(target_file)
        return data

    # Get data for all steps
    def get_data_for_each_step (self, root_name='', metric=""):
        """
        PURPOSE: Wrapper function that calls get_data_for_one_step() for each step
        
        INPUTS:
            root_name: the input dir as specified by user
            metric: The metric to collect from each step
        
        OUTPUTS: Returns a list that contains the log data for each step
        
        CALLEES: SetOfColumns.make_columns_for_step()
            
        """
        # get list of dirs
        all_data = []
        dir_list = os.walk (os.path.join (root_name, '.')).next ()[1]
        dir_list = self.folder_workflow_sort (dir_list)

        # for each dir, get data
        for dirname in dir_list:
            dirname = os.path.join (root_name, dirname)
            step_data = self.get_data_for_one_step (dirname, metric)
            all_data.append (step_data)

        return all_data

    def decode_data (self, target_file, root_name, new_file_name, flag=""):
        """
        PURPOSE: decodes a sar file
        
        INPUTS:
            target_file: A sar filename in binary form which needs to be decoded
 
            root_name: the folder containing the binary sar file

            new_file_name: The output filename for the decoded file 

            flag: a string of flags to pass to the sar command
        
        OUTPUTS: Return the full path to the decoded sar file
        
        CALLEES: InputOutput.get_data_for_one_step()            
        """

        new_target_file = os.path.join (OUTPUT_DIR_NAME, new_file_name)
        sar_command = 'sar --legacy -f "{0}" {2} > "{1}"'.format (target_file, new_target_file, flag)
        self.logger.info("Running sar:\n{0}".format(sar_command))
        call ([sar_command], shell=True)
        return new_target_file

    def get_files_in_dir (self, dir_to_read):
        """
        PURPOSE: Get a list of files in the given directory
        
        INPUTS: dir_to_read: the dir to list
        
        OUTPUTS: Returns a list of file paths
        
        CALLEES: 
            CompleteDataFiles.fix_filename_in_plotfiles()
            CompleteDataFiles.fix_plotfile_for_multicore
        """
        return [os.path.join (dir_to_read, file) for file in os.listdir (dir_to_read) if os.path.isfile (os.path.join (dir_to_read, file))]

    def get_root_path (self):
        """
        PURPOSE: Gets the root folder of where this script was called from
        
        INPUTS: None
        
        OUTPUTS: Returns the root folder path
        
        ALGORITHM: Uses sys.argv[0] to determine the current folder
        
        CALLEES: 
            CompleteDataFiles.fix_filename_in_plotfiles()
            CompleteDataFiles.fix_plotfile_for_multicore
        """
        #  - fix this to work with
        return os.path.split (os.path.abspath (os.path.realpath (sys.argv[0])))[0]

    def check_root (self, root):
        """
        PURPOSE: Checks if root folder specified is an actual folder. 
        
        INPUTS: root: a root folder
        
        OUTPUTS: Returns root if root is a valid folder 
            otherwise returns the root folder of this script
        
        CALLEES: CompleteDataFiles.make_plots()
        """
        if not (os.path.isdir (root)):
            root = os.path.dirname (os.path.realpath (__file__))
        return root

    def make_output_dir (self, output_dir):
        """
        PURPOSE: Creates a directory in the path specified 
        
        INPUTS: output_dir - This is the path of the directory to create
        
        OUTPUTS: Returns the full path of the new folder as string
        
        CALLEES:
            InputOutput.store_data_into_csv()
            CpuSpecificsColumn.make_csv_from_data()
        """
        try:
            os.makedirs (output_dir)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        return output_dir

    #2. OUTPUT_DIR_NAME
    #def store_data_into_csv (self, data, output_file=0, output_dir=OUTPUT_DIR_NAME[0]):
    #def store_data_into_csv (self, data, output_file=0, output_dir=OUTPUT_DIR_NAME):
    def store_data_into_csv (self, data, output_file=0, output_dir=None): 
        """
        PURPOSE: Writes data into a csv file
        
        INPUTS:
            data: The data to be written
            output_file: The output filename
            output_dir: The folder the csv file will be created in
        
        OUTPUTS: Creates a file. Returns nothing
    
        CALLEES:
            ColumnOfStatistics.make_csv_from_data()
            CpuSpecificsColumn.make_csv_from_data()
        """
        #  - do not need to make the output dir - this was done as part of parsing arguments
        #if (output_dir == 0) or not (os.path.isdir (output_dir)):
        #    output_dir = self.make_output_dir (output_dir)
        if output_dir is None:
            output_dir = OUTPUT_DIR_NAME

        # make filename
        if (output_file == 0):
            output_file = time.strftime("%Y-%m-%d_%H.%M.%S") + "_io_stats.csv"

        output_file = os.path.join (output_dir, output_file)

        # write file
        with open(output_file, 'wb') as output:
            writer = csv.writer (output)
            for count in data:
                writer.writerow (count)

    # Calls all the plot files
    def make_plots (self, output_files=[]):
        """
        PURPOSE: Repeatedly calls gnuplot to create the output images
        
        INPUTS: output_files: The list of *.plt files
        
        OUTPUTS: Creates .png files if gpuplot runs successfully

        CLASS:  InputOutput   
        
        CALLEES: CompleteDataFiles.make_plots()
        """
        os.environ['GNUTERM'] = 'dumb'
        for filename in output_files:
            filename = filename.replace (' ', '\ ')
            print filename
            with open(os.devnull, "w") as fnull:
                call (["gnuplot", filename], stdout=fnull, stderr=fnull)
        return

    # The contextmanager decorators makes this function 
    # usable with a 'with' statement
    @contextmanager
    def make_temp_files (self, root, cores=0):
        """
        PURPOSE: A context manager for creating then removing temp files
            Usage example:
                with make_temp_files(root_folder, 4) as temp_files:
                    for file in temp_files: do_work(file)
                # Once out of the block, the temp files have been deleted
            Note: This is only used for multicore data runs for mpstat currently. 
        
        INPUTS:
            root: The folder to make the new temp files in.
            cores: # of cores. One temp file per core.
        
        OUTPUTS: Yields a list of temp files. 
        
        CALLEES: CompleteDataFiles.make_plots()
        """
        list_of_files = []
        temp_dir = mkdtemp ()

        for core in range (cores):
            list_of_files.append (mkstemp (prefix=str (core), suffix='.csv', dir=temp_dir))
        yield list_of_files

        for file in list_of_files:
            os.close (file[0])
            os.remove (file[1])
        rmtree (temp_dir)

    # Helpers -------
    # sort folder list (in workflow order)
    def folder_workflow_sort (self, folder_list):
        """
        PURPOSE: Orders folder_list to match ordering of workflow 
        
        INPUTS: folder_list: Folder names to sort
        
        OUTPUTS: Returns a sorted list
        
        CALLEES:
            SetOfColumns.get_number_of_cores()
            InputOutput.get_data_for_each_step()
        """
        new_folder_list = []
        not_found_folders = []

        pl_search_strings = (eval(PL)).values()
       
        #for folder_name in ORDERED_WORKFLOW_STAT_DIRS:
        for search_str in pl_search_strings:
            # Flag for if we've found a folder matching folder_name
            found = False
            for folder in folder_list:
                search_result = re.search (search_str, folder)
                if search_result:
                    # Found the matching folder
                    new_folder_list.append (folder)
                    found = True
                    break

            if not found:
                not_found_folders.append(search_str)

        if not new_folder_list:
            raise Exception("folder_workflow_sort(): Couldn't find any folders using the workflow search strings for '%s'." % (PL))

        if not_found_folders:
            raise Exception("Didn't find matches for all search strings in workflow '%s' for: \n%s" % (PL, '\n'.join(not_found_folders)))
        return new_folder_list

    def read_lines(self, filename):
        """
        PURPOSE: Reads in the text from a file as an array
        
        INPUTS: filename: The file to open
        
        OUTPUTS: Returns a list, each element is a line from the file

        CALLEES: CompleteDataFiles.fix_filename_in_plotfiles_old
        """
        with open(filename, 'r') as in_file:
            return in_file.readlines()

    def write_lines(self, filename, lines):
        """
        PURPOSE: Writes out lines from a list into a text file
            Note: Doesn't add a newline to the lines being written
        
        INPUTS: filename: The file to create
            lines: an array of lines to write
        
        OUTPUTS: None

        CALLEES: CompleteDataFiles.fix_filename_in_plotfiles_old
        """
        with open(filename, 'w') as out_file:
            return out_file.writelines(lines)

    def function():
            pass

#------------------------------
# User interaction
#------------------------------
class UserInput:
    """
    PURPOSE: Parses the command line input and runs the script
        UserInput.post_process() is the main entry point
    
    ATTRIBUTES: None
    
    ORIGINAL DATE, VERSION:
    
    CHANGE LOG:
    
    CURRENT VERSION:
    """

    def __init__(self):
        self.logger = None
        # List of steps that did not contain enough data to process
        self.skipped_steps = []
       
    def parse_args (self, argv):
        """
        PURPOSE: validates user arguments
            
        INPUTS: 
            args_ns: argument namespace as parsed by argparse.parse_args 
            
        OUTPUTS: 
            A list of two elements: [rc, args_ns] or [rc, None] 

            SUCCESS - [rc, args_ns] 
                rc:      integer return code which is 0 on success. 
                args_ns: This make it possible for other users of the arguments to 
                     access the options, and to change easily the value of an 
                     option if necessary and pass that back to the caller.

            FAILURE - [rc, None]
                rc:   integer > 0.  It is caller's responsibility to handle failure.
                None: return None instead of args_ns
        
        ALGORITHM:
            1. Validate 'root' input directory.
            2. Validate workflow and the workflow stage output dirs within 'root' 
            3. Statistics
            4. sliding window
            5. output directory
        CALLEES: main()
        """
        #instantiate parser
        #RawTextHelpFormatter is for preserving whitespace and indentation -- useful for usage and help messages
        parser = argparse.ArgumentParser (formatter_class=argparse.RawTextHelpFormatter,
                                          description="Generates readable CSVs and plots which describe resource utilization for a given workflow")
        
        ## Positional Parameters
        parser.add_argument ("root", help="Directory containing workflow's profile data")


        ## Optional Parameters
        # workflow
        pl_help = "Specify the workflow"

        pl_choices = workflow_parse_dict.keys()  # a list of acceptable workflow names

        parser.add_argument ("-N", "--workflow_name",
                             choices=pl_choices,
                             default='sample',
                             help=pl_help)
        # Single Stage workflow
        ss_help = "To process a single stage of a known workflow. \n" + \
                  "Specify a substring that is present in the stage \n" + \
                  "output directory name."
        """
        s is a substring for use when post-processing a single
        step of a workflow. The substring must be present in 
        the directory name containing the stage's output.
        """
        #parser.add_argument ("-S", "--single_step", help="Name of workflow step to process")
        parser.add_argument ("-S", "--single_step", help=ss_help)
        # Output directory
        parser.add_argument ("-o", "--output", 
                             default=OUTPUT_DEFAULT_DIR,
                             help="Specify path of the output folder. Default is ./post_processed_stats")

        # Plots
        parser.add_argument ("-p", "--plot", help="Plot the data using gnuplot", action='store_true')

        # Smoothing window size
        parser.add_argument ("-w", "--window", help="Window size for smoothing plots", default=100, type=int)

        parser.add_argument ("-t", "--tag", help="A tag name to uniquely identify the data set (Will be displayed in plots)")
        
        # Utilities -- REQUIRED to select at least one from this group
        # Required group to force user to pick at least one stats flag
        stats = parser.add_argument_group('metrics', 'metrics options')
        stats.add_argument ("-A", "--all", help="Parse all metrics", action='store_true')
        stats.add_argument ("-i", "--iostat", help="Parse iostat information", action='store_true')
        #stats.add_argument ("-m", "--mpstat", help="Parse mpstat info (cpu)", action='store_true')
        stats.add_argument ("-s", "--sar", help="Parse sar information", action='store_true')
        #stats.add_argument ("-f", "--free", help="Parse free information", action='store_true')

        # logger
        parser.add_argument ("-l", "--log", help="Specify the logging level", choices=LOG_LEVEL_MAP.keys(), default="info")


        args = parser.parse_args (args=argv)  # returns namespace object containin args

        
        # For outputting debug and error messages
        self.logger = setup_logger(args.output, LOG_LEVEL_MAP[args.log])

        ## Sampling Interval
        #global MEASURE_INTERVAL
        #if args.window != MEASURE_INTERVAL:
        #    MEASURE_INTERVAL = args.window
          
        return args

    def check_args (self, args_ns):
        global PL
        global ARGS_NS
        ## return codes
        success = 0
        root_err = 1                # input dir error
        stats_err = 2               # metrics error
        single_step_err = 3         # single step error
        out_err = 4                 # output dir error
        pl_err = 5                  # workflow error 
        rlist = [success, args_ns]  # return on success
        err_list = [-1, None]       # return on error    

        logger = self.logger       
        
        ##1.Check that 'root' is a valid directory
        logger.debug("check_args::Starting check of passed in \'root\' directory")
        #print ("check_args::Starting check of passed in \'root\' directory")
        root = args_ns.root
        if not os.path.isabs(root):
            root = os.path.abspath(root)
            args_ns.root = root  # change the namespace value
            rlist[1] = args_ns
 
        logger.debug("check_args::The root directory is \'%s\'" % (root))  # debug prnt
        #print ("check_args::The root directory is \'%s\'" % (root))
        if not os.path.isdir(root):
            #check the path before basename for validity

            logger.debug("check_args: Error: Root directory \'%s\' is not a valid directory" % (root))
            #rc = 1
            err_list[0] = root_err 
            #return rc, args_ns
            return err_list
         
        logger.debug("check_args::root directory \'%s\' passes validation!" % (root))
        #print ("check_args::root directory \'%s\' passes validation!" % (root))

 
        ##2. Check that 'workflow' choice is valid
        """
        IF valid: 
           check the root directory for the correct dirs
        """
        logger.debug("check_args::Validating workflow parameter")
        logger.debug("   passed in workflow arg is: \'%s\'" % (args_ns.workflow_name))

        if args_ns.workflow_name in workflow_parse_dict:
            PL = workflow_parse_dict[args_ns.workflow_name]  # sets PL to the dictionary
        logger.debug("check_args::The global var PL has been set to workflow \'%s\'" % (PL))
        logger.debug("   The workflow steps for \'%s\' are:" % (PL))
        pl = PL
        steps = (eval(pl)).keys()
        step_dict = (eval(pl))
        if args_ns.single_step:
            if not args_ns.single_step in step_dict.itervalues():
                raise Exception("single_step: "+args_ns.single_step+" not in step options for "+args_ns.workflow_name)
            for key, value in step_dict.iteritems():
                if value == args_ns.single_step:
                    step_dict.clear()
                    step_dict.update(OrderedDict ([(key, value)]))
                    steps = step_dict.keys()
                    break
        logger.debug(steps)
        logger.debug("   The workflow dir seach strings for \'%s\' are:" % (pl))
        search_dir_strs = (eval(pl).values())
        logger.debug(search_dir_strs)
        logger.debug("   The workflow dir search strings for \'%s\' are:" % (pl)) 
        logger.debug("     Step   Search Str")
        for s in steps:
            logger.debug("     %s  --> %s" % (s, (eval(pl)[s])))

        #Validate dir search strings to ensure that each pattern exists in a sub-dir of the root input dir 
        len_steps = len(steps)
        len_search_strs = len(search_dir_strs)
        validations = 0 
        sep = os.sep
        dir_entries = os.listdir(root)
        dir_entries_abs = []
        for e in dir_entries:
            dir_entries_abs.append(root + sep + e)

        not_found_strs = list(search_dir_strs)  # copy search strings to not found - remove as found 
        for str in search_dir_strs:
            for e in dir_entries_abs:
                if str in e:
                    #found an entry that contains a valid substr
                    #check if e is a dir
                    if os.path.isdir(e):
                        validations += 1
                        #remove found str from not_found list - for error case
                        not_found_strs.remove(str) 
                        break
        if validations != len_steps:
            if len(not_found_strs) > 0:
                err_list[0] = pl_err 

        ##3.Check for 'all' stats, and if not true check that at least one of the other stats are selected
        #stats_ok = True
        logger.debug("check_args::Starting check of metrics")

        all_args = args_ns.all
        iostat = args_ns.iostat
        #mpstat = args_ns.mpstat
        sar = args_ns.sar
        #free = args_ns.free

        stats_error_msg = "A|--all, -i|--iostat,  -s|--sar"

        #if not any([args.all, args.iostat, args.mpstat, args.sar, args.free]):
        if not any([all_args, iostat, sar]):
            #rc = 3 
            err_list[0] = stats_err
            logger.debug("ERROR:check_args: At least one metric argument is required: \'%s\'" % stats_error_msg)
            print ("ERROR:check_args: At least one metric argument is required: \'%s\'" % stats_error_msg)
            return err_list
        logger.debug("check_args::Metric choice is valid.")

        ##4. Check Output dir
        """
        Check that output is a valid directory. 
            IF exists AND default:                             #using default dir
                use this dir for output
            ELSE:                                              #not default dir 
                IF parent path is valid AND output does not exist: 
                    create directory        #works for default?
                ELIF output and parent exist:
                    create output 
                ELSE:
                    print error msg
                    return error code
        """
        logger.debug("check_args::Validating output dir.")
        output = args_ns.output.rstrip('/')
        abs_output = os.path.abspath(output)   #convert to absolute path

        ##set boolean to True when directory is created 
        #out_created = False  # used for cleanup later if error -- not using
        out_exist = os.path.isdir(abs_output)       # does path exists?
        parent = os.path.dirname(abs_output)        # parent path as str
        parent_exist = os.path.isdir(parent)    # does parent exist?

        if (out_exist and (abs_output == OUTPUT_DEFAULT_DIR)):
            try:
                os.mkdir(abs_output)
                
            except:
                pass #output dir already made

        else:
            if ((out_exist is False) and (parent_exist)):
                #create dir in path specified
                os.mkdir(abs_output)
            elif (out_exist) and (parent_exist):
                try:
                    os.mkdir(abs_output)
                except:
                    pass #exists
            else:
                logger.error("ERROR: check_args: Unable to create output directory: '%s'" % (abs_output))
                err_list[0] = out_err
                return err_list
        #out_created = True 
        #update args namespace with output in case it changed
        args_ns.output = abs_output
 
        rlist[1] = args_ns  # update the return list before returning
        ARGS_NS = args_ns   # update the global args namespace object
        return rlist

    def post_process (self, args):
        """
        PURPOSE: 
            does the work: 
               Parses the metrics and creates output files
        
        INPUTS: the argument namespace as updated by check_args 
        
        OUTPUTS:

        CALLEES: main()
        """
        global OUTPUT_DIR_NAME
        columns = SetOfColumns (self.logger)
        finished_data = CompleteDataFiles (self.logger)
        time_holder = ['go']
        average_time_holder = ['go']
        core_data = []
        iostat_columns = []
        sar_columns = [] 
        active_mem_columns = []
        mpstat_active_columns = []
        mpstat_total_columns = []
        list_of_plot_regexes = []
        list_of_file_regexes = []
        list_of_multicore_plot_regexes = [] #used by mpstat
        #window = args.window  ## change to use args.window instead
        rc = 0  # success return code
        ret_early = 1  # reurn early code

        if args.output:
            #3. OUTPUT_DIR_NAME
            #OUTPUT_DIR_NAME[:] = [args.output]
            OUTPUT_DIR_NAME = args.output

        """ #rlk - commenting this out for now
        if args.no_multistep:
            ORDERED_WORKFLOW_STEPS[:] = ['process']
            ORDERED_WORKFLOW_STAT_DIRS[:] = ['.*run\..*']
        """
        #workflow_steps = sample_dict.keys()
        workflow_steps = (eval(PL)).keys()

        if args.iostat or args.all:
            iostat_columns = columns.make_columns_for_step (args.root, 
                             'iostat', steps=workflow_steps, window=args.window)
            columns.make_csv_from_set (iostat_columns, 'iostat')
            list_of_plot_regexes.append (r'_iostat\.plt')
            list_of_file_regexes.append (r'_iostat\.csv')

        if args.sar or args.all:
            sar_columns = columns.make_columns_for_step (args.root, 'sar', 
                          steps=workflow_steps, time_holder=time_holder, 
                          window=args.window)
            columns.make_csv_from_set (sar_columns, 'sar')
            list_of_plot_regexes.append (r'_sar\.plt')
            list_of_file_regexes.append (r'_sar\.csv')

            sar_columns_reads = columns.make_columns_for_step (args.root, 
                                'sar_reads', steps=workflow_steps, 
                                time_holder=time_holder, window=args.window)
            columns.make_csv_from_set (sar_columns_reads, 'sar_reads')
            list_of_plot_regexes.append (r'_sar_reads\.plt')
            list_of_file_regexes.append (r'_sar_reads\.csv')

            sar_columns_writes = columns.make_columns_for_step (args.root, 
                                 'sar_writes', steps=workflow_steps, 
                                 time_holder=time_holder, window=args.window)
            columns.make_csv_from_set (sar_columns_writes, 'sar_writes')
            list_of_plot_regexes.append (r'_sar_writes\.plt')
            list_of_file_regexes.append (r'_sar_writes\.csv')

            active_mem_columns = columns.make_columns_for_step (args.root, 
                                 'active_mem', steps=workflow_steps, 
                                 window=args.window)
            columns.make_csv_from_set (active_mem_columns, 'active_mem')
            list_of_plot_regexes.append (r'committed_mem\.plt')
            list_of_file_regexes.append (r'active_mem\.csv')

        """
        #commenting this out - mpstat stuff
        if args.mpstat or args.all:
            # Active core data
            mpstat_active_columns = columns.make_columns_for_step (args.root, 
                                    'mpstat_active_core', steps=workflow_steps,
                                    window=args.window)
            columns.make_csv_from_set (mpstat_active_columns, 
                                       'mpstat_active_core')
            list_of_plot_regexes.append (r'active_core_mpstat\.plt')
            list_of_file_regexes.append (r'_mpstat_active_core\.csv')

            # Total core data
            mpstat_total_columns = columns.make_columns_for_step (args.root, 
                                   'mpstat_total_core', steps=workflow_steps, 
                                   window=args.window)
            columns.make_csv_from_set (mpstat_total_columns, 
                                       'mpstat_total_core')
            list_of_file_regexes.append (r'_mpstat_total_core\.csv')
            list_of_plot_regexes.append (r'_total_core_mpstat\.plt')

            # Multicore data
            core_data = columns.make_sets_for_cores (args.root, 'mpstat')
            columns.make_csv_from_set (core_data, 'mpstat')
            list_of_multicore_plot_regexes.append (r'many_cores\.plt')
        """
        if args.plot or args.all:
            if not args.tag:
                # set tag to the basename of the input dir
                tag = os.path.basename(os.path.normpath(args.root))

                """          
                # Split the basename of root dir by '_' chars
                root_bnSplit = os.path.basename(os.path.normpath(args.root)).split('_')
                if len(root_bnSplit) >= 3:
                    sname = root_bnSplit[0]
                    thread = root_bnSplit[1]
                    tag = sname + ', # Threads: ' + root_bnSplit[1]
                else:
                    tag = root_bnSplit[0] 
                """
            else:
                tag = args.tag

            #list_of_multicore_plot_regexes is only used with mpstat

            finished_data.make_plots (args.root, OUTPUT_DIR_NAME, tag, 0, 
              core_data, list_of_multicore_plot_regexes, list_of_file_regexes, 
              list_of_plot_regexes, columns.average_time[0])

        self._remove_logger_if_empty()
                
        return rc

    def _remove_logger_if_empty(self):
        empty = False
        parser_log_filename = 'parser.log'
        try:
            with open(parser_log_filename, 'r') as f:
                if not f.readlines():
                    empty = True
            if empty:
                os.remove(parser_log_filename)
        except:
            pass


#------------------------------
# Parsing
#------------------------------
class ColumnOfStatistics ():
    """
        PURPOSE: Base class for other column classes. This represents one column
        of data in the format: "time, data". Pass in the raw log data text for
        one column and let it parse it.

        ATTRIBUTES:
            io: an InputOutput object
            column_type: Doesn't appear to be used


        ORIGINAL DATE, VERSION: 2013, v. 0.0 

        CHANGE LOG: date, initials, description
            2-5-2014, added documentation block
 
        CURRENT VERSION: 0.1 
    """

    def __init__ (self, logger):
        self.logger = logger
        self.io = InputOutput(logger)
        self.column_type = None
        self.max_sampling_interval = 3600 # 1 hour

        
    def get_useful_metrics (self, log_data, core=0, times=[], date_holder=['skip']):
        """
        PURPOSE: Extracts metrics and timestamps that we care about from a 
                 log file

        INPUTS:
            log_data: The raw log text for this metric
            core: core # for multithreading stats (default: 0)
            times: a list used for multicore support, not used currently 
            date_holder: list used for multicore support, not used currently 


        OUTPUTS:
            Returns a list of [timestamp, metric_value] pairs for this metric

        EXCEPTIONS: none

        CALLEE(S): 
            ColumnOfStatistics.make_column_from_metrics()
        """
        if date_holder[0] is not 'skip':
            if date_holder[0] == 'go':
                date_holder.pop ()
            time_list = self.get_datetime_from_log (log_data, core)
            date_holder.append (time_list)
        else:
            time_list = self.get_datetime_from_log (log_data, core, times)
        data_list = self.get_data_from_log (log_data, core)

        return [list (pair) for pair in izip (time_list, data_list)]

    # Makes one data column from log data (one step in workflow)
    def make_column_from_metrics (self, log_data, core=0, date_data=[], date_holder=[], window=None, average_time_holder=None):
        """
            PURPOSE: Whereas get_useful_metrics gets the [time, data] info,
                this further cleans up the data, performing a sliding average
                and inserting title information for the metric. 
            INPUT:
                log_data: Its the text of the raw file like: [line 1 of sar output, line 2, ...]
                core:
                date_data:
                date_holder:
                window: sliding average window as specified with --window
                average_time_holder
            OUTPUT:
                A list of lists in format (value, timestamp) containing 
                cleaned data suitable for saving in csv and for use in 
                generating plots.  For example:
                [['value in x interval', 'time in x interval'], 
                    ['432432', '1-2-12 3:40 pm'],
                    ['432432', '1-2-12 3:50 pm']]
            CALLEES:
        """ 
        window = ARGS_NS.window 
        #-- check for special case
        if not log_data or len (log_data) is 0:
            # print "error, no data in 'make_column_from_metrics'"
            # return ['0']
            raise Exception("No data in 'make_column_from_metrics'")

        if date_holder:
            clean_data = self.get_useful_metrics (log_data, core, date_data, date_holder)
        else:
            clean_data = self.get_useful_metrics (log_data, core, date_data)
        average_time = self.get_time_averages (clean_data, window)
        if average_time > 0 and not average_time_holder[0]:
            average_time_holder[:] = [average_time] #we need to store this for the plot files
        clean_data = self.make_sliding_average (clean_data, window)
        clean_data = self.insert_headers (window, clean_data, average_time, core)
        return clean_data

    # Helpers -------
    def get_data_from_log (self, data, core=0):
        """
            PURPOSE: This takes a raw data file text list, like that extracted
                from iostats output file, and gets all the data
                from it and stores it in a list.  For iostat we grab
                the io time used for instance. 
            INPUT:
                data = raw text data extracted from file
            OUTPUT:
                ['112321', '432432', '54345', ...]
            CALLEES:
        """
        return data

    def get_datetime_from_log (self, data, core=0, date_data=[]):
        """
            PURPOSE: To get the timestamps from the raw data
                text list of a metric file. 
            INPUT:
                data = raw text data extracted from file
            OUTPUT:
                eg: ['1-2-2013 3:30pm', '1-2-2013 3:40pm', ...]
            CALLEES:
        """
        return data

    # For the header function
    def workflow_step_name ():
        """
            PURPOSE: 
              To return the type of step that we're working with. 

              TODO:
              THIS IS NOT USED OR NEEDED... remove?
            INPUT:
            OUTPUT:
              eg: 'bwa2'
            CALLEES:
        """
        return ''

    def remove_bad_first_elem(self, time_list):
        try:
            del time_list[0]
        except:
            pass

    def get_time_averages (self, data=[], window=30):
        """
            PURPOSE: 
              This will get the average time delta for a lot of data points. 
              For instance, you could parse the iostat file, pass it into 
              this, and it will tell you whatever time spacing you used
              for recording the data. 

              Additionally, it accounts for bad data where a collector may
              have missed a collection point.  
    
            INPUT:
              data:  list of data 
                e.g., [['4324', '1-12-2013 3:30pm'], ...]

              window: integer, specifying the collection interval in seconds. 
                      default is 30 seconds
            OUTPUT:
               average time delta as a float 
            CALLEES:
              make_sliding_average 
        """
        average_time_deltas = []
        average_time_delta = 0
        time_end = prev_end = datetime (1, 1, 1, 1, 1, 1)
        if not data:
            print("warning, data is empty while finding time averages")
            return 0
            
        miss_counter = 0  # for catching bad windows

        for line, i in izip (data, range(200)):
            time_end = datetime(*line[0])
            diff_since_last = time_end - prev_end
            if diff_since_last.seconds < window and diff_since_last.seconds > 0:
                average_time_deltas.append (diff_since_last.seconds)
            else:
                miss_counter += 1
                if miss_counter == 10:
                    window = self.max_sampling_interval
            prev_end = time_end

        if len(average_time_deltas) > 0:
            prev_end = time_end

        if len(average_time_deltas) > 0:
            average_time_delta = sum (average_time_deltas) / float (len (average_time_deltas))
        return average_time_delta

    # For make_sliding_average's error handling
    def repair_time_datapoint (self, data, line_number, average_time_delta):
        """
            PURPOSE: 
                This inserts a datapoint in the position you would expect, 
                when a very wrong datapoint is detected. 

                TODO: I think we should change this to 
                simply remove the datapoint
                and the associated timestamp.
            INPUT:
                data = eg: [['4324', '1-12-2013 3:30pm'], ...]
                line_number = 5 #where error is
                average_time_delta = 30 #average timestamp difference
            OUTPUT:
            CALLEES:
        """
        corrected_datapoint = 0
        if line_number == 0:
            if (datetime (*data[2][0]) - datetime (*data[1][0])).seconds > 3 * average_time_delta:
                raise Exception("Vital datapoint error, cannot continue repair. Please search datafile for: %s" % data[line_number][0])
            corrected_datapoint = datetime (*data[1][0]) - timedelta (seconds=average_time_delta)
        else:
            corrected_datapoint = datetime (*data[line_number - 1][0]) + timedelta (seconds=average_time_delta)
        return corrected_datapoint

    def make_sliding_average (self, data=[], window=60):
        """
            PURPOSE: 
                This will take data in the form of [[data, time], ...] 
                and perform a sliding average on it. This is so that
                our graphed data is prettier. 
            INPUT:
                data = eg: [['4324', '1-12-2013 3:30pm'], ...]
            OUTPUT:
                # with the sliding average performed
                data = eg: [['4324', '1-12-2013 3:30pm'], ...]
            CALLEES:
               

        """
        if self._find_sliding_avg_error(data, window):
            return self._convert_time_to_str(data)

        average_time_delta = self.get_time_averages (data, window)
        double_error = False
        averaged_data = []
        running_sum = 0
        time_end = prev_end = 0.0
        remainder_sum = 0.0
        # First time_start should be one interval behind due to data being cumulative
        prev_end = time_start = (datetime (*data[1][0]) - timedelta (seconds=average_time_delta)) - timedelta (seconds=average_time_delta)

        for line_number, line in enumerate(data):
            time_end = datetime (*line[0])
            diff_since_last = time_end - prev_end

            if diff_since_last < timedelta (seconds=0):
                diff_since_last = (time_end + timedelta (hours=23)) - prev_end

            if diff_since_last > timedelta (average_time_delta * 10) or diff_since_last < timedelta (seconds=0):
                if (double_error):
                    print time_end
                    raise Exception("Fatal error")
                print "Error bad time datapoint. Will attempt to repair based on average time"
                print time_end
                time_end = self.repair_time_datapoint (data, line_number, average_time_delta)
                diff_since_last = time_end - prev_end
                double_error = True
            else:
                double_error = False
            diff = time_end - time_start
            new_weighted_val = line[1] * (float (diff_since_last.seconds) / window)
            running_sum += new_weighted_val
            prev_end = time_end

            if diff.seconds >= (window + 1):
                diff_from_window = diff - timedelta (seconds=window)
                remainder_sum = new_weighted_val * (float (diff_from_window.seconds) / (diff_since_last.seconds))
                running_sum = running_sum - remainder_sum
                time_end -= diff_from_window
                time_end = time_end - (timedelta (microseconds=time_end.microsecond))

                averaged_data.append ([str (time_end), round (running_sum, 1)])
                # Set up for next iteration
                running_sum = remainder_sum
                time_start = time_end

        return averaged_data

    def _find_sliding_avg_error(self, data, window):
        def error_msg():
            print "Warning, not enough data to do make_sliding_average()"
            return True

        if not data:
            return error_msg()

        min_data_points = 3
        time_start = datetime (*data[0][0])
        time_end = datetime (*data[-1][0])
        min_frame_size = time_end - time_start
        
        if len (data) < min_data_points or min_frame_size.seconds < window:
            return error_msg()
        return True

    def _convert_time_to_str(self, data):
        cleaned_time = []
        for line in data:
            cleaned_time.append([str(datetime(*line[0])), line[1]])
        return cleaned_time

    # Returns the type of data which we're looking at
    def data_type (self, core=0):
        """
            PURPOSE: 
                This will return the type of stat. We use this to identify
                the class, and to insert the header name. 
            INPUT:
            OUTPUT:
                eg: 'iostat'
            CALLEES:
        """
        return ''

    def insert_headers (self, time_header=100, data=[], avg_interval='', core=0):
        """
            PURPOSE: 
                This will insert the header information for each (of 2)
                columns in this data. 
            INPUT:
                time_header = the starting time interval, pre-sliding average
                data = [['data', 'time'], ...]
                avg_interval = average time interval between data points
            OUTPUT:
                data, but with the headers inserted
            CALLEES:
        """
        if data is not None:
            time_column = 'time in interval: ' + str (time_header) + 's'
            data_column = 'average ' + self.data_type (core) + ' per ' + str (avg_interval) + 's'
            data.insert (0, [time_column, data_column])
        return data

    def make_csv_from_data (self, data, type_of_metric):
        """
        PURPOSE: Wrapper around InputOutput.store_data_into_csv()
            Writes the input data to a CSV file
        
        INPUTS:
            data: the log data
            type_of_metric: eg: "iostat", see top of file REFERENCE: POSSIBLE_METRICS

        There are two functions with same name in different classes
        CLASS: ColumnOfStatistics 
 
        OUTPUTS: Creates a csv file
        
        CALLEES: SetOfColumns.make_csv_from_set()
        """
        output_file = time.strftime("%Y-%m-%d_%H.%M.%S") + '_' + type_of_metric + '.csv'
        self.io.store_data_into_csv (data, output_file)
        return

    def get_datetime_given_regex (self, regex, current_date, data):
        """
            PURPOSE: 
                This will walk through the raw data, performing the 
                regex, and storing any timestamps it finds with it. 
                It also "stradles midnight", aka does the right thing
                about PM - AM transitions.
            INPUT:
                regex: the compiled regex used for finding timestamps
                current_date: the first timestamp in the file? 
                    TODO: why do we need this?
                data: the raw file data for the metric
            OUTPUT:
                ['timestamp1', 'timestamp2', ...]
            CALLEES:
        """
        date_data = []
        previous_AM_PM = ''

        for line in data:
            parsed_time = (re.search (regex, str (line)))
            if parsed_time is not None:
                am_pm = str (parsed_time.group (4))
                # Increase day if past midnight
                if (am_pm == 'AM') and (previous_AM_PM == 'PM'):
                    current_date = datetime.strptime ('-'.join (current_date), "%Y-%m-%d")
                    current_date += timedelta (days=1)
                    current_date = [date for date in current_date.strftime ("%Y %m %d").split (" ")]

                standard_time = [int (num) for num in list (current_date) + list (parsed_time.group (1, 2, 3))]
                if (am_pm == 'PM') and (standard_time[3] is not 12):
                    standard_time[3] += 12
                if (am_pm == 'AM') and (standard_time[3] is 12):
                    standard_time[3] = 0

                date_data.append (standard_time)
                previous_AM_PM = am_pm

        return date_data


class SetOfColumns ():
    """
        These functions get the various stats for the whole workflow given
        the workflow's root dir.

        For instance, this class makes all the columns for 1 step. 
    """
    def __init__ (self, logger):
        self.logger = logger
        self.io = InputOutput(logger)
        self.column_type = None
        self.average_time = [0]

    def compute_stats (self, data, metric="", step=''):
        """
            PURPOSE: 
                Computes mean, median, etc for each metric and stores them in global for now
            INPUT:
            OUTPUT:
            CALLEES:
        """
        values = []
        for x in data[1:]:
            values.append(float(x[1]))
        if not values:
            return 
        meanval = numpy.mean(values)
        medianval = numpy.median(values)
        maxval = max(values)
        stdev = numpy.std(values)
        self.logger.info("Metric\t %s \tStep\t %s \tMean\t %f \tMedian\t %f \tStdev\t %f \tMax\t %f" % (metric, step, round(meanval,2), round(medianval,2), round(stdev, 2), round(maxval,2)))


    #def make_columns_for_step (self, root_dir='dir-to-data', type_of_metric="iostat", core=0, steps=ORDERED_WORKFLOW_STEPS, time_data=[], time_holder=[], window=100):
    ## Pass in the PL dict name
    def make_columns_for_step (self, root_dir='dir-to-data', type_of_metric="iostat", core=0, steps=[], time_data=[], time_holder=[], window=100):
        """
        PURPOSE: 
            For 1 root dir, this will parse the data for 1 metric, for
            all steps in the workflow.
        
        INPUTS:
            #root_dir: Root folder of log data for this step
            root_dir: this is the input dir as given by user
            type_of_metric: Metric name
                eg: "iostat", see top of file REFERENCE: POSSIBLE_METRICS
            core: The core number used for multithreading stats
            steps: List of workflow steps (e.g., ['bwa aln 1', 'bwa aln 2', 'sampe']), default is ??
            
            time_data: ?? 
            time_holder: a list of lists containing start times for each interval
                         format is [[YYYY,DD,M,hh,m,s],...]
            window: sampling interval as given by user with default interval or --interval option
        
        OUTPUTS:
            Returns a list of datapoints ready to be written to a CSV file
            Format: [data, time, data, time, ...], ...] 
        CALLEES: 
            SetOfColumns.make_sets_for_cores()
            UserInput.post_process() via instance of SetOfColumns
        """
        data = [[]]
        self.column_type = self.get_class_type (type_of_metric)
        log_data = self.io.get_data_for_each_step (root_dir, type_of_metric)

        for raw, step, a_time in izip_longest (log_data, steps, time_data):
            temp_data = self.column_type.make_column_from_metrics (raw, core, a_time, time_holder, window, self.average_time)
            # Compute stats
            self.compute_stats (temp_data,type_of_metric,step)
            if temp_data is None:
                print "No data in " + step
                return data
            temp_data.insert (0, [step])
            data = self.append_column (data, temp_data)
        data.insert (0, [type_of_metric.upper () + ': ' + self.column_type.data_type (core)])
        return data

    def make_sets_for_cores (self, root_dir, type_of_metric, core=0):
        """
            PURPOSE: 
                This will make all the data for all cores 
                for 1 metric, across all the workflow steps. 
                it only does this for all workflow steps b/c it calls 
                  make_columns_for_step which runs over all the steps
            INPUT:
                root_dir: input directory
                type_of_metric: the metric being processed
                core:
            OUTPUT:
                The core data will be encapsulated into the data list.
                Each core data is all the columns for each step in the 
                workflow for 1 different core. 
            CALLEES:
                UserInput.post_process() via instance of SetOfColumns
        """
        data = []

        if type_of_metric == 'mpstat':
            core = self.get_number_of_cores (root_dir)

        for core_num in range (core):
            steps = (eval(PL)).keys() 
            data.append (self.make_columns_for_step (root_dir, type_of_metric, core_num, steps))
        return data

    def get_number_of_cores (self, root_dir, type_of_metric="mpstat"):
        """
        PURPOSE: This will get the number of cores that 
            were used during the workflow run.
            It's set up to use mpstat
        
        INPUTS: 
            root_dir: Root of step log data
            type_of_metric: Metric name
                eg: "iostat", see top of file REFERENCE: POSSIBLE_METRICS

        
        OUTPUTS: Returns the number of cores found
            e.g. 16
        
        CALLEES:
            CompleteDataFiles.make_plots()
            SetOfColumns.make_sets_for_cores()
        """
        dir_list = os.walk (root_dir).next ()[1]
        dir_list = self.io.folder_workflow_sort (dir_list)
        dir_list = [os.path.join (root_dir, dir) for dir in dir_list]

        log_data = self.io.get_data_for_one_step(dir_list[0], type_of_metric)
        in_core_data = False
        log_data = iter (log_data)
        found_core_len = False
        core_count = ''
        total_cores = 0

        # walk the lines of data,
        # regex for the starting core
        # count
        # regex for ending, end
        while found_core_len is False:
            # Using the date to signal the start of core data
            core_start = re.compile (r"^\d+:\d+:\d+\s\w\w\s\s\s")
            core_count = re.search (core_start, log_data.next ())

            if in_core_data is True and core_count is None:
                found_core_len = True
            if core_count is not None:
                in_core_data = True
                total_cores += 1

        return total_cores

    def make_csv_from_set (self, data, type_of_metric):
        """
            PURPOSE: 
                This will make the csv file for the data.

                NOTE: Why it needs to set up a class for this
                is because the class contains naming information. 
            INPUT:
            OUTPUT:
            CALLEES:
        """
        # Pass data to single data class, which will call io class
        column_type = self.get_class_type (type_of_metric)
        column_type.make_csv_from_data (data, type_of_metric)
        return

    # Helpers -------
    # Get class from classname (for workflow)
    def get_class_type (self, metric=''):
        """
            PURPOSE: 
                This will return a metric class based on
                the text name of it. 
            INPUT:
                metric name.
            OUTPUT:
                metric class.
            CALLEES:
        """
        #iostat
        if metric == 'iostat':
            return IostatColumn (self.logger)
        #sar
        elif metric == 'sar':
            return CpuTotalsColumn (self.logger)

        elif metric == 'sar_reads':
            return IoReadsFromSar (self.logger)

        elif metric == 'sar_writes':
            return IoWritesFromSar (self.logger)

        elif metric == 'active_mem':
            return ActiveMemoryColumn (self.logger)
        """
        #not used
        elif metric == 'mpstat':
            return CpuSpecificsColumn (self.logger)

        elif metric == 'mpstat_active_core':
            return ActiveCoreColumn (self.logger)

        elif metric == 'mpstat_total_core':
            return TotalCoreColumn (self.logger)

        elif metric == 'free':
            return MemoryColumn (self.logger)

        """
        return

    def append_column (self, data, new_column):
        """
            PURPOSE: 
                This will combine columns, and if one is longer it'll
                pad the other one with spaces. 

                TODO: I think the izip_longest function does this already.
            INPUT:
            OUTPUT:
            CALLEES:
        """
        longest = 0
        data_len = len (data)
        for line in data:
            if len (line) > longest:
                longest = len (line)
        for count in range (len (new_column)):
            # Adding blanks
            if count >= data_len:
                data.append ([])
            if len (data[count]) < longest:
                for x in range (longest - len (data[count])):
                    data[count] += ['']
            data[count] += new_column[count]
        # get rid of trailing []
        if not data[-1]:
            data.pop ()
        return data



class CompleteDataFiles ():
    """
        Post processing for preparing data for gnuplot or others.
    """
    def __init__ (self, logger):
        self.logger = logger
        self.io = InputOutput (logger)
        self.column_type = None
        self.set_of_columns = SetOfColumns (logger)
        self.repair_process_needed = False
        self.gnuplot_formatted = ''
        self.max_number_of_cores = 5000 # max reasonable core amount

    #list_of_multicore_plot_regexes used only with mpstat
    def make_plots (self, root_dir, output_root, tag, cores=0, core_data='', 
                    list_of_multicore_plot_regexes='', 
                    list_of_file_regexes='', list_of_plot_regexes='', 
                    average_time=0):
        """
            PURPOSE: 
                This will makes the *.plt files for the parsed metrics.
                It also plots the graphs.
                We iterate through each plot file and add any new information,
                 and then call them at call the plot function on each one.
            INPUT:
                root_dir = string path to workflow output
                output_root = string path of output, where the plot files are
                cores = number of cores workflow ran with 
                core_data = the full dataset for multicore
                list_of_multicore_plot_regexes = the regexes to locate the 
                    multicore plot files
                list_of_file_regexes = the regeses to find the files (csvs) 
                    that hold the data
                list_of_plot_regexes = the regexes to find the plot files (.plt)
                average_time = sampling interval
            OUTPUT:
            CLASS: CompleteDataFiles -- two functions of same name defined in different classes
            CALLEES:
        """
        self._check_for_single_step(list_of_file_regexes)
    
        plotted_files = []

        #this next if statement is confusing. It uses the core count
        #  of the current machine if passed in cores is 0 or > max. We  
        #  call this statement everytime we run the parser AND we
        #  always pass in 0 as the value for cores 
        #  Only matters if mpstat, although cores is passed on to other 
        #  functions.
        if cores == 0 or cores > self.max_number_of_cores:
            cores = multiprocessing.cpu_count()

        with self.io.make_temp_files (root_dir, cores) as temp_files:
            # : can we check temp_files first for multi-core files? no need to do next step if not any
            self.make_temp_data_for_gnuplot (root_dir, temp_files, cores, core_data) 
            if (list_of_plot_regexes):  # make list of plot files from *.plt files
                plotted_files = self.fix_filename_in_plotfiles (output_root, tag, 
                                list_of_plot_regexes, list_of_file_regexes, 
                                root_dir, average_time)
            if (list_of_multicore_plot_regexes):# mpstat/mulitcore plot files
                #only for mpstat
                plotted_files += (self.fix_plotfile_for_multicore(
                                  list_of_multicore_plot_regexes, temp_files))
            self.io.make_plots (plotted_files)  # gnuplot images

        return

    def _check_for_single_step(self, list_of_file_regexes):
        if len(list_of_file_regexes) < 2:
            self.repair_process_needed = True 
        self.repair_process_needed = False

    #5. OUTPUT_DIR_NAME -- rk changed output dir list to output string
    def make_temp_data_for_gnuplot (self, root_dir, temp_files, cores=0, core_data='', output_dir=OUTPUT_DIR_NAME, multi_dir=MULTITHREAD_PARSER_OUTPUT_DIR):
        """
            PURPOSE: 
                Only used with mpstat; only applies to multicore plots.
                It makes temp files by concactinating all the multicore plot 
                files.  Otherwise gnuplot can't handle the data.
            INPUT:
                root_dir = string path to workflow output
                temp_files = list of string paths to temps files which hold the
                             multicore csv data
                cores = number of cores workflow ran with 
                core_data = the full dataset for multicore
                output_root = string path of output, where the plot files are
            OUTPUT:
                the temp files will now contain the multicore data
            CALLEES:
                self.make_plots
        """
        if not core_data:
            return

        for old_file in core_data:
            if not old_file:
                continue

            # transpose data
            just_data = old_file[3:]
            just_data = [list (data) for data in izip_longest (*just_data)]

            # append each column to start
            for column_count in range (int(len (old_file[3]) / 2)):
                column_pos = column_count * 2

                # get rid of trailing ''
                while just_data[0][-1] == '':
                    just_data[0].pop()
                    just_data[1].pop()

                just_data[0] += just_data[column_pos]
                just_data[1] += just_data[column_pos + 1]

            # untranspose and convert away unicode
            just_data = list (izip_longest (*just_data))
            old_file[3:] = [list (data) for data in just_data]
            for line in old_file:
                line[0] = str (line[0])

        # write to temp files
        for output_file, data in izip (temp_files, core_data):
            with open(output_file[1], 'wb') as output:
                writer = csv.writer (output)
                for count in data:
                    writer.writerow (count)
        return

    def get_process_name (self, dir):
        '''
            Given a dir to the files or whatever, get process

            input:
                dir = /path/stuff.stuff..bwa/

            output:
                bwa
        '''
        dir = os.path.basename (glob (dir + '/*')[0])
        process_name = re.search(r'''
            \/*  # start
            run\..+\.\.   # the start of the target folder name
            (.+)       # part that we want of the folder
            \.   # process stopping period
            ''', dir, re.X).group(1)
        return process_name

    def replace_named_line_in_file (self, raw_data_root, file_text):
        '''
            this will replace the 'process' name part of the plot file

            input:
                raw.. = /path/to/run.rjeklw.bwa/

            changes:
                file_text that's input to have correct process
        '''

        process_name_to_insert = self.get_process_name (raw_data_root)
        old_process = re.compile(r'''
                (plot\ ".*?".*?t\ ")  # everything up to the title
                .*
                (".*with\ lines.*)  # everything after the title
                ''', re.X)
        return [re.sub(old_process, r'\1' + process_name_to_insert + r'\2', line, re.M) for line in file_text]

    def fix_filename_in_plotfiles (self, output_dir, tag, plot_names, csv_names, raw_data_root, average_time):
        """
            PURPOSE: 
                Render the plot file template with the correct values inserted.
                Inserts the following:
                   The sampling interval of run
                   The tag of the run in the subtitle
                   The path for the .png file to be output
                   The path of the input .csv data file(s)
                It also handles removing a trailing comma if the script is set to parse a single stage

            INPUT:
               output_dir - The ouput dir as given by the user
               plot_names - The list of *.plt files*
               csv_names -  The list of *.csv files*
               raw_data_root - The root input directory as given by the user
            OUTPUT: a list
            CALLEES:
               CompleteDataFiles.make_plots
        """
        #steps = sample_dict.keys()
        steps = (eval(PL)).keys()

        # Escape underscores in subtitle
        #tag_app = tag + ", " + "Sampling Interval: " + str(int(average_time)) + " seconds"
        subtitle = re.sub("_", r"\\\\\\\\_", tag)
        #subtitle = re.sub("_", r"\\\\\\\\_", tag_app) 

        # this block gets the csvs in order
        parser_root = self.io.get_root_path ()
        files_in_output_root = self.io.get_files_in_dir (os.path.join (parser_root, output_dir))
        plot_template_files = self.io.get_files_in_dir (os.path.join(parser_root, TEMPLATE_DIR))
        list_of_csvs = self.order_files_by_regex (csv_names, files_in_output_root)  # Append relative path if needed
        # If WINDOWS, double backlashes
        list_of_csvs = [self.double_backslashes (a_csv) for a_csv in list_of_csvs]

        templates = self.order_files_by_regex (plot_names, plot_template_files)

        # The filepaths to the new .plt files
        output_plots = [self.get_output_plot_name(template_file, output_dir) for template_file in templates]
        
        # Open and fix plot data
        for output_plot, template, new_csv_path in izip (output_plots, templates, list_of_csvs):
            plot_text = self.io.read_lines(template)

            #repair process is True in the case of single stage workflow
            if self.repair_process_needed:
                plot_text = self.replace_named_line_in_file(raw_data_root, plot_text)
            else:
                #repair process_needed is False by default
                self.sub_data_for_each_match (plot_text, steps[0], r'(?<=1\ t\ \")[^\"]+', fix_time_flag=False)

            # Replace output dir the .png file
            output_root_dir = os.path.dirname(new_csv_path)

            # The regex (?<=set output \").+(?=\/[^\/]+\.png)
            # looks for 'set output "', and '/<some_filename>.png', and replaces everything in between

            self.sub_data_for_each_match(plot_text, output_root_dir, r"(?<=set output \").+(?=\/[^\/]+\.png)", fix_time_flag=False)


            ##  - make sure graphs have the correct sampling interval reported in the title - replace the interval with what it should be
            constructed_interval = "sampled at %d second intervals" % (average_time)
            self.sub_data_for_each_match(plot_text, constructed_interval, r"sampled at \d+ second intervals", False) 
            
            # Replace the subtitle with the correct text
            self.sub_data_for_each_match(plot_text, subtitle, r"<subtitle>", False) 
            
            self.sub_data_for_each_match (plot_text, new_csv_path, r"(?<=\").+\d+.+\w.+\.csv", fix_time_flag=True)

            new_p = self.put_extra_steps_in_text (steps[1:], plot_text) ##why start with index 1 here?
            plot_text[:] = [''.join(new_p)]

            # Output the new .plt file
            self.io.write_lines(output_plot, plot_text)
        return output_plots

    def get_output_plot_name(self, template_filepath, output_dir):
        """
        PURPOSE: Takes in a path to the .plt template and constructs a new filename
            e.g. ./plot_templates/template_iostat.plt -> outputdir/plot_iostat.plt
        
        INPUTS: 
            template_filepath: The path to a template .plt file
            output_dir: The output folder for the parser
        
        OUTPUTS: Returns a path to where the plt file should be written

        ALGORITHM:
        
        CALLEES: CompleteDataFiles.fix_filename_in_plotfiles
        """
        template_filename = os.path.basename(template_filepath)
        # template_iostat.plt -> plot_iostat.plt
        plot_filename = template_filename.replace("template", "plot", 1)

        return os.path.join(output_dir, plot_filename)

    def put_extra_steps_in_text (self, steps, text):
        """
            PURPOSE:
                If you open a plot file, you'll notice that each
                csv filename line after the first one is different
                formatted from the first. This puts in those.
            INPUT:
                steps = list of new csvs, 
                    TODO I think these are all
                    coppies of the same csv, unless it's dealing with
                    multiple cores...
                text = plotfile raw text
            OUTPUT:
                the plot text with the csv filename lines all added
            CALLEES:
                CompleteDataFiles.fix_filename_in_plotfiles
                CompleteDataFiles.build_gnuplot_lines_from
        """
        # I think this got duplicated in a merge
        # self.build_gnuplot_lines_from (steps)
        # text = self.trim_all_after_regex_in_text (r'^plot', text)
        # if len (ORDERED_WORKFLOW_STEPS) <= 1:
        #     text[-1] = re.search(r'.*with lines', text[-1]).group(0) + '\n'
        # elif text[-1][-2] != '\\':
        #     text[-1] = re.search(r'.*with lines', text[-1]).group(0) + ', \\\n'
        # return self.add_plot_lines_from_to (self.gnuplot_formatted, text)

        #"""
        self.build_gnuplot_lines_from (steps)
        text = self.trim_all_after_regex_in_text (r'^plot', text)
        if len (steps) <= 1:
            text[-1] = re.search(r'.*with lines', text[-1]).group(0) + '\n'
        elif text[-1][-2] != '\\':
            text[-1] = re.search(r'.*with lines', text[-1]).group(0) + ', \\\n'
        return self.add_plot_lines_from_to (self.gnuplot_formatted, text)

    def build_gnuplot_lines_from (self, csv_list):
        """
            PURPOSE: 
                This builds the the lines needed to add to the csv file, 
                except for the first one and last one which are 
                special cases.

                TODO: looking over this it looks like it omits the last line.
                Why is this? I think I put it in later..?
            INPUT:
                csv_list = the string list of csv files to take the plot
                    data from.
            OUTPUT:
            CALLEES:
                self.put_extra_steps_in_text
        """
        time = 3
        data = 4
        line = 2
        gnuplot_left_text = r"  '' using ((timecolumn(" + str(time) + r")-offset)/3600):" + str(data) + r" every ::3 ls " + str(line) + " t "
        gnuplot_middle_text = ''
        gnuplot_right_text = ' with lines, \\\n'
        self.gnuplot_formatted = []
        for count, csv in enumerate(csv_list):
            gnuplot_middle_text = '"' + csv + '"'
            if count == len(csv_list) - 1:
                gnuplot_right_text = gnuplot_right_text[0:-4]
            self.gnuplot_formatted.append (gnuplot_left_text + gnuplot_middle_text + gnuplot_right_text)
            time += 2
            data += 2
            line += 1
            gnuplot_left_text = r"  '' using ((timecolumn(" + str(time) + r")-offset)/3600):" + str(data) + r" every ::3 ls " + str(line) + " t "
        return

    def trim_all_after_regex_in_text (self, regex, text):
        # deletes everything after a regex match
        new_text = []
        for line in text:
            if re.search (regex, line) != None:
                new_text.append(line)
                break
            new_text.append(line)
        return new_text

    def add_plot_lines_from_to (self, format, text):
        return text + format

    def fix_plotfile_for_multicore (self, plot_name, temp_cores):
        """
            PURPOSE: 
                For multicore plot files, this will take 
                the csv names, and the 
                starting time, and update that info in the plot
                files.
                Only used with mpstat
            INPUT:
                plot_names = the regexes to find the plot files 
                temp_cores = the temporary core data files (csv)
            OUTPUT:
                the filename of the plotfile repaired
            CALLEES:
                self.make_plots
        """
        temp_cores = [self.double_backslashes (cores[1]) for cores in temp_cores]
        parser_root = self.io.get_root_path ()
        plot_template_files = self.io.get_files_in_dir (os.path.join(parser_root, TEMPLATE_DIR))

        templates = self.order_files_by_regex (plot_name, plot_template_files)
        starting_time = self.get_starting_time (temp_cores[0])

        output_root_dir = os.path.realpath(OUTPUT_DIR_NAME)

        # The filepaths to the new .plt files
        output_plots = [self.get_output_plot_name(template_file, output_root_dir) for template_file in templates]
        plot_text = self.io.read_lines(templates[0])

        new_plot_text = []

        # Fix first csv line and remove the rest
        for line in plot_text:
            if re.search (r'^plot\s\"', line):
                line = re.sub (r"(?<=\").+\w.+\.csv", temp_cores[0], line)
                new_plot_text.append (line)

                break

            line = re.sub (r"(?<=set output \").+(?=\/[^\/]+\.png)", output_root_dir, line)

            ##  - make sure graphs have the correct sampling interval reported in the title - replace the interval with what it should be
            #constructed_interval = "at %d second intervals" % (MEASURE_INTERVAL)  ##  not necessary b/c only for mpstat
            line = re.sub(r"at \d+ second intervals", constructed_interval, line)

            if re.search (r'starting_time\ \=', line):
                line = re.sub (r'(?<=starting_time\ \=\ )\S+', str (starting_time), line)

            new_plot_text.append (line)

        # Add each line with cores 1+
        new_line_text = re.search (r'(?<=plot).+$', new_plot_text [-1]).group (0)
        for index, core in enumerate (temp_cores[1:]):
            new_line_text = (re.sub (r'(?<=^\s\").+\w.+\.csv', core, new_line_text))
            new_line_text = (re.sub (r'(?<=::3\sls\s)\d+', str (index + 2), new_line_text))
            new_plot_text.append (re.sub (r'(?<=core\s)\d+', str (index + 1), new_line_text) + '\n')
        new_plot_text [-1] = new_plot_text [-1][:-4]

        plot_text[:] = new_plot_text

        self.io.write_lines(output_plots[0], plot_text)

        return output_plots

    def get_starting_time (self, file_name):
        """
            PURPOSE: 
                Gets the starting time's hours and seconds, 
                in seconds intervals
            INPUT:
                file_name = raw data file, has to be csv with data
            OUTPUT:
                the number of seconds expected as the starting time
            CALLEES:
                self.sub_data_for_each_match
                self.fix_plotfile_for_multicore
        """
        starting_time = 0
        with open (file_name) as file:
            all_lines = file.readlines()
            self.logger.debug("File: %s" % file_name)
            self.logger.debug(all_lines)
            start_time_line = all_lines[3]
            nums_from_time_line = [int (num) for num in re.findall (r'\d+', start_time_line)]
            hours, minutes, seconds = nums_from_time_line[3:6]
            starting_time = hours * 3600 + minutes * 60 + seconds

        return starting_time

    def double_backslashes (self, text):
        return re.sub(r'\\', r'\\\\\\\\', text)  # fixes backslashes for windows... wow

    def sub_data_for_each_match (self, text_to_edit, texts_to_insert, regexes, fix_time_flag):
        """
            PURPOSE: 
                For every regex match this finds, it will substitute
                that regex match for some text passed in.
                The text, and the regexes, are both in list form.
            INPUT:
                text_to_edit = raw string of text for file
                texts_to_insert = each string to insert into the 
                    raw data, when a match is found
                regexes = used to find the matches
                fix_time_flag = if true, repair the starting time 
            OUTPUT:
                the editted text string 
            CALLEES:
                self.fix_filename_in_plotfiles
        """

        for regex, text_to_insert in zip ([regexes], [texts_to_insert]):
            if fix_time_flag:
                starting_time = self.get_starting_time (text_to_insert)
            # then we fix time
            for count, line in enumerate(text_to_edit):
                if fix_time_flag:
                    text_to_edit[count] = re.sub (r'(?<=starting_time\ \=\ )\S+', str (starting_time), line, re.MULTILINE)
                text_to_edit[count] = re.sub (regex, text_to_insert, line, re.MULTILINE)
        return text_to_edit

    @contextmanager
    def open_edit_write (self, file):
        """
            PURPOSE: 
                Use this in lieu of "open" in "with open(x) as f:"
                And when you go out of the indentation, it will
                write the file and close it!
            INPUT:
                file = file to be opened 
            OUTPUT:
                an open file that will write when you close it
            CALLEES:
                self.fix_filename_in_plotfiles
                self.fix_plotfile_for_multicore
        """
        with open (file, 'r+b') as file_data:
            file_text = list (file_data.readlines ())
            yield file_text
            file_data.seek (0)
            file_data.truncate ()
            file_data.write (''.join (file_text))

    def order_files_by_regex (self, regex_list, file_names):
        """
            PURPOSE: 
                TODO: this could be replaced with the normal sort 
                function that's built in.
            INPUT:
                regex_list = list of regexes to be iterated over
                file_names = list of files to be compared to regexes
            OUTPUT:
                a list of the sorted files
            CALLEES:
                self.fix_filename_in_plotfiles
                self.fix_plotfile_for_multicore
        """
        sorted_files = []
        for keyword in regex_list:
            for file in file_names:
                if re.search (keyword, file):
                    sorted_files.append (file)
        return sorted_files


#------------------------------
# Specific parser classes
#------------------------------
class IostatColumn (ColumnOfStatistics):
    """
        Returns one column of data when given one unparsed iostat file.
        Iostat parses the reads and writes
    """
    # Get the dates for one of Iostat's logs
    def get_datetime_from_log (self, data, core=0, date_data=[]):
        date_data = []
        for line in data:
            parsed_time = (re.search(r"""
                (\d+).(\d+).(\d+)\s   # date
                (\d+):(\d+):(\d+)\s   # time
                (\w+).*$              # AM/PM
                """, str (line), re.VERBOSE))
            if parsed_time is not None:
                am_pm = parsed_time.group(7)
                standard_time = [int (time) for time in parsed_time.group(3, 1, 2, 4, 5, 6)]
                if (am_pm == 'PM') and (standard_time[3] is not 12):
                    standard_time[3] += 12
                if (am_pm == 'AM') and (standard_time[3] is 12):
                    standard_time[3] = 0
                date_data.append (standard_time)
        return date_data

    # Get the await data for one of Iostat's logs
    def get_data_from_log (self, log_data, core=0):
        await_data = []

        in_hdd_area = False  # For summing only the HDDs in one block
        prev_await = 0
        await_sum = 0

        # filter only sdb lines and filter only the number we want
        for line in log_data:
            # result = (re.search(r'^(sdb).+$', str(line), re.M))
            io_data = re.search (r'^\S+\s+(?:\d+\.\d+\s+){8}(\d+)', str (line), re.M)
            if io_data != None:
                in_hdd_area = True
                await_data_single = int (io_data.group (1))
                if await_data_single > 1000000000:
                    await_data_single = prev_await
                await_sum += await_data_single
                prev_await = await_data_single

            elif in_hdd_area:
                in_hdd_area = False
                await_data.append (await_sum)
                await_sum = 0

        return await_data

    # Returns the type of data which we're looking at
    def data_type (self, core=0):
        return 'time waiting on io'


class CpuTotalsColumn (ColumnOfStatistics):
    """
        Gives the total cpu% averaged for all cores given one unparsed
        sar file.
    """
    # Helpers -------
    # Get dates from sar logs
    def get_datetime_from_log (self, data, core=0, date_data=[]):
        date_list = []
        previous_AM_PM = ''
        current_date = re.search (r"(\d+)/(\d+)/(\d+)", str (data[0])).group (3, 1, 2)

        for line in data:
            parsed_time = (re.search (r"""
                ^(\d+):(\d+):(\d+)\s   # time
                (\w+).*                # AM/PM
                """, str (line), re.VERBOSE))
            if parsed_time is not None:
                am_pm = parsed_time.group(4)
                # Increase day if past midnight
                if (am_pm == 'AM') and (previous_AM_PM == 'PM'):
                    current_date = datetime.strptime ('-'.join (current_date), "%Y-%m-%d")
                    current_date += timedelta (days=1)
                    current_date = [date for date in current_date.strftime ("%Y %m %d").split(" ")]

                standard_time = [int (num) for num in list (current_date) + list (parsed_time.group (1, 2, 3))]
                if (am_pm == 'PM') and (standard_time[3] is not 12):
                    standard_time[3] += 12
                if (am_pm == 'AM') and (standard_time[3] is 12):
                    standard_time[3] = 0

                date_list.append (standard_time)
                previous_AM_PM = am_pm
        # to delete the header line from the date_list
        self.remove_bad_first_elem(date_list)
        return date_list

    # Get the cpu useage for averaged, or each core
    def get_data_from_log (self, log_data, core=0):
        cpu_usage = []
        for line in log_data:
            result = re.search (r'^\d+:\d+.+all\s+(\d+.\d+).*$', str (line))
            if result is not None:
                cpu_usage.append (float (result.group (1)))
        return cpu_usage

    # Returns the type of data which we're looking at
    def data_type (self, core=0):
        return 'cpu load (all cores)'


class IoReadsFromSar (ColumnOfStatistics):
    """
        Parses the IO read bandwidth given one unparsed
        sar file.
    """
    # Helpers -------

    # Get dates from sar logs
    def get_datetime_from_log (self, data, core=0, date_data=[]):
        date_list = []
        previous_AM_PM = ''
        current_date = re.search (r"(\d+)/(\d+)/(\d+)", str (data[0])).group (3, 1, 2)

        for line in data:
            parsed_time = (re.search (r"""
                ^(\d+):(\d+):(\d+)\s   #time
                (\w+).*                #AM/PM
                """, str (line), re.VERBOSE))
            if parsed_time is not None:
                am_pm = parsed_time.group(4)
                # Increase day if past midnight
                if (am_pm == 'AM') and (previous_AM_PM == 'PM'):
                    current_date = datetime.strptime ('-'.join (current_date), "%Y-%m-%d")
                    current_date += timedelta (days=1)
                    current_date = [date for date in current_date.strftime ("%Y %m %d").split(" ")]

                standard_time = [int (num) for num in list (current_date) + list (parsed_time.group (1, 2, 3))]
                if (am_pm == 'PM') and (standard_time[3] is not 12):
                    standard_time[3] += 12
                if (am_pm == 'AM') and (standard_time[3] is 12):
                    standard_time[3] = 0

                date_list.append (standard_time)
                previous_AM_PM = am_pm
        self.remove_bad_first_elem(date_list)
        return date_list

    # Get the cpu useage for averaged, or each core
    def get_data_from_log (self, dirty_data, core=0):
        MB_multiplier = 2048  # convert results to MB
        #1,048,576 bytes per megabyte, 512 bytes per data block
        #1,048,576 / 512 = 2,048
        #so divide each data block by 2048 to get size in MB
        io_reads = []

        for line in dirty_data:
            result = re.search (r'^\d+:\d+.+?\wM\s+(\S+\s+){3}(\d+.\d+)', str (line))
            if result is not None:
                io_reads.append (round((float (result.group (2)) / MB_multiplier),2))
        return io_reads

    # Returns the type of data which we're looking at
    def data_type (self, core=0):
        return 'io reads in mb/sec'


class IoWritesFromSar (ColumnOfStatistics):
    """
        Parses the IO write bandwidth given one unparsed
        sar file.
    """
    # Helpers -------
    # Get dates from sar logs
    def get_datetime_from_log (self, data, core=0, date_data=[]):
        date_list = []
        previous_AM_PM = ''
        current_date = re.search (r"(\d+)/(\d+)/(\d+)", str (data[0])).group (3, 1, 2)

        for line in data:
            parsed_time = (re.search (r"""
                ^(\d+):(\d+):(\d+)\s   #time
                (\w+).*                #AM/PM
                """, str (line), re.VERBOSE))
            if parsed_time is not None:
                am_pm = parsed_time.group(4)
                # Increase day if past midnight
                if (am_pm == 'AM') and (previous_AM_PM == 'PM'):
                    current_date = datetime.strptime ('-'.join (current_date), "%Y-%m-%d")
                    current_date += timedelta (days=1)
                    current_date = [date for date in current_date.strftime ("%Y %m %d").split(" ")]

                standard_time = [int (num) for num in list (current_date) + list (parsed_time.group (1, 2, 3))]
                if (am_pm == 'PM') and (standard_time[3] is not 12):
                    standard_time[3] += 12
                if (am_pm == 'AM') and (standard_time[3] is 12):
                    standard_time[3] = 0

                date_list.append (standard_time)
                previous_AM_PM = am_pm
        self.remove_bad_first_elem(date_list)
        return date_list

    # Get the cpu useage for averaged, or each core
    def get_data_from_log (self, dirty_data, core=0):
        MB_multiplier = 2048  # convert results to MB
        #1,048,576 bytes per megabyte, 512 bytes per data block
        #1,048,576 / 512 = 2,048
        #so divide each data block by 2048 to get size in MB
        io_writes = []

        for line in dirty_data:
            result = re.search (r'^\d+:\d+.+?\wM\s+(\S+\s+){4}(\d+.\d+)', str (line))
            if result is not None:
                io_writes.append (round((float (result.group (2)) / MB_multiplier),2))
        return io_writes

    # Returns the type of data which we're looking at
    def data_type (self, core=0):
        return 'io writes in mb/sec'


class CpuSpecificsColumn (ColumnOfStatistics):
    """
        Returns a column for each core given an mpstat file.
    """
    def __init__ (self, logger):
        self.logger = logger
        self.io = InputOutput (logger)

    # Helpers -------
    # Get dates from MPSTAT logs
    def get_datetime_from_log (self, data, core=0, date_data=[]):
        current_date = list (re.search (r"(\d+)/(\d+)/(\d+)", str (data[0])).group (3, 1, 2))
        parse_time = re.compile (r"""
            ^(\d+):(\d+):(\d+)\s   # time
            (\w+)                  # AM/PM
            \s\s\s\s0              # core 0 time (we only need one)
            """, re.X)
        date_data = self.get_datetime_given_regex (parse_time, current_date, data)
        return date_data

    # Get the cpu useage for averaged, or each core
    def get_data_from_log (self, log_data, core):
        cpu_usage = []
        num = 0
        for line in log_data:
            result = re.search (r'^\d+:\d+:\d+.\w+\s{3}(.\S+).+(...\.\d+)$', line)
            if result is not None:
                num = int (result.group (1))
                if num is core:
                    cpu_usage.append (round (100.0 - float (result.group (2)), 1))
        return cpu_usage

    # Returns the type of data which we're looking at
    #6. OUTPUT_DIR_NAME
    def make_csv_from_data (self, data, type_of_metric, output_root=None, multi_dir=MULTITHREAD_PARSER_OUTPUT_DIR):
        """
        PURPOSE: Wrapper around InputOutput.store_data_into_csv()
            Writes the input data to a CSV file
        
        INPUTS:
            data: the log data
            type_of_metric: eg: "iostat", see top of file REFERENCE: POSSIBLE_METRICS

        There are two functions with same name in different classes
        CLASS: ColumnOfStatistics 
 
        OUTPUTS: Creates a csv file
        
        CALLEES: SetOfColumns.make_csv_from_set()
        """
        if output_root is None:
            output_root = OUTPUT_DIR_NAME

        for data_set, count in izip (data, range (len (data))):
            output_file = time.strftime("%Y-%m-%d_%H.%M.%S") + '_' + type_of_metric + '_cpu_core_{num:02d}.csv'.format (num=count)

            output_dir = os.path.join (output_root, "multithreading_stats")
            output_dir = self.io.make_output_dir (output_dir) 
            
            self.io.store_data_into_csv (data_set, output_file, output_dir)
        return

    # Returns the type of data which we're looking at
    def data_type (self, core=0):
        return 'cpu load core {0}'.format (core)


class ActiveCoreColumn (ColumnOfStatistics):
    """
        This takes mpstat data, finds the biggest core, and gives that
        data.
    """
    def get_datetime_from_log (self, data, core=0, date_data=[]):
        current_date = list (re.search (r"(\d+)/(\d+)/(\d+)", str (data[0])).group (3, 1, 2))
        parse_time = re.compile (r"""
            ^(\d+):(\d+):(\d+)\s   # time
            (\w+)                  # AM/PM
            \s\s\s\s0              # core 0 time (we only need one)
            """, re.X)
        date_data = self.get_datetime_given_regex (parse_time, current_date, data)
        return date_data

    def get_data_from_log (self, log_data, core):
        # walk data
        active_core_usage = []
        biggest_usage = 0
        for line in log_data:
            result = re.search (r'^\d+:\d+:\d+\s.M\s+(\d+)\s+(\d+.\d+)', line)
            if result:
                usage = float (result.group (2))
                if usage > biggest_usage:
                    biggest_usage = usage
            elif biggest_usage > 0:
                active_core_usage.append (biggest_usage)
                biggest_usage = 0

        return active_core_usage

    # Returns the type of data which we're looking at
    def data_type (self, core=0):
        return 'cpu load on most active core (%)'


class TotalCoreColumn (ColumnOfStatistics):
    """
        This takes mpstat data, sums all the cores' usage, and gives that
        data.
    """
    def get_datetime_from_log (self, data, core=0, date_data=[]):
        current_date = list (re.search (r"(\d+)/(\d+)/(\d+)", str (data[0])).group (3, 1, 2))
        parse_time = re.compile (r"""
            ^(\d+):(\d+):(\d+)\s   # time
            (\w+)                  # AM/PM
            \s\s\s\s0              # core 0 time (we only need one)
            """, re.X)
        date_data = self.get_datetime_given_regex (parse_time, current_date, data)
        return date_data

    def get_data_from_log (self, log_data, core):
        # walk data
        total_core_usage = []
        total_usage = 0
        inside_data = False
        for line in log_data:
            result = re.search (r'^\d+:\d+:\d+\s.M\s+(\d+)\s+(\d+.\d+)', line)
            if result:
                inside_data = True
                usage = float (result.group (2))
                if usage > 0:
                    total_usage += usage
            elif inside_data:
                inside_data = False
                total_core_usage.append (total_usage)
                total_usage = 0

        return total_core_usage

    # Returns the type of data which we're looking at
    def data_type (self, core=0):
        return 'cpu load on all cores summed up'


#class SmartCpuMultithreading (ColumnOfStatistics):
#    """
#        This takes CpuSpecificsColumn output and gives the multithreading
#        efficiency by taking the difference from the active core and the
#        rest.
#    """
#    def placeholder ():
#        return
class MemoryColumn (ColumnOfStatistics):
    """
        Entire class is for free - not used currently
        Returns a column of total memory in use (MBs) given a .free file
    """
    def __init__ (self, logger):
        self.logger = logger
        self.total_memory = 0
        self.io = InputOutput (logger)
        self.column_type = None

    # Helpers -------
    # Gets dates from 'free' logs and from sar (for starting point)
    def get_datetime_from_log (self, data, core=0, date_data=[]):
        if not date_data:
            print "error, please make sure to parse iostat since free doesn't timestamp"
        return date_data

    # Gets the total memory usage at each point
    def get_data_from_log (self, log_data, core=0):
        memory_usage = []
        for line in log_data:
            result = re.search (r'Mem:\s+\d+\s+(\d+)', line)
            if result:
                memory_usage.append (int (result.group (1)))
        # get total memory size
        for line in log_data:
            result = re.search (r'Mem:\s+(\d+)', line)
            if result:
                self.total_memory = int (result.group (1))
                break
        return memory_usage

    # Returns the type of data which we're looking at
    def data_type (self, core=0):
        return 'total memory used out of {0}mb'.format (self.total_memory)


class ActiveMemoryColumn (ColumnOfStatistics):
    """
        Gives the total active 'committed' memory averaged for all drives given
        one unparsed sar file.
    """
    # Helpers -------
    # Get dates from sar logs
    def get_datetime_from_log (self, data, core=0, date_data=[]):
        date_list = []
        previous_AM_PM = ''
        current_date = re.search (r"(\d+)/(\d+)/(\d+)", str (data[0])).group (3, 1, 2)

        for line in data:
            parsed_time = (re.search (r"""
                ^(\d+):(\d+):(\d+)\s   # time
                (\w+).*                # AM/PM
                """, str (line), re.VERBOSE))
            if parsed_time is not None:
                am_pm = parsed_time.group(4)
                # Increase day if past midnight
                if (am_pm == 'AM') and (previous_AM_PM == 'PM'):
                    current_date = datetime.strptime ('-'.join (current_date), "%Y-%m-%d")
                    current_date += timedelta (days=1)
                    current_date = [date for date in current_date.strftime ("%Y %m %d").split(" ")]

                standard_time = [int (num) for num in list (current_date) + list (parsed_time.group (1, 2, 3))]
                if (am_pm == 'PM') and (standard_time[3] is not 12):
                    standard_time[3] += 12
                if (am_pm == 'AM') and (standard_time[3] is 12):
                    standard_time[3] = 0

                date_list.append (standard_time)
                previous_AM_PM = am_pm
        self.remove_bad_first_elem(date_list)
        return date_list

    # Get the cpu useage for averaged, or each core
    def get_data_from_log (self, log_data, core=0):
        cpu_usage = []
        for line in log_data:
            result = re.search (r'^\d+:\d+.+M\s+(?:\S+\s+){5}(\d+).*$', str (line))
            if result is not None:
                result = int (result.group (1)) / 1048576
                cpu_usage.append (round(result, 2))
        return cpu_usage

    # Returns the type of data which we're looking at
    def data_type (self, core=0):
        return 'committed memory (gb)'

#------------------------------
# Main
#------------------------------
if __name__ == "__main__":
    sys.exit(main())
