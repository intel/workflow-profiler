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
workflow_profiler.py

    A global script that handles the execution of a workflow passed and post
    -processes the profiling data to generate csv and graphs. The user is 
    required to pass in the location of the workflow they want to run and 
    provide some informational parameters. This script would provide them with 
    the post-processed data.

    Methodology/Structure:
        - Entry point
           - Main Function:main()
              - Parse input arguments : parse_args()
              - Validate arguments : validate_args()
                  -- If validation passes, proceed. Else exit with errors.
              - Run workflow script : profiler()
                  -- Creates a folder under the output directory for storing all
                     the data with format samplename_noofthreads_datetimestamp.
                  -- Generates the output files and a run.* directory for each 
                     stage of profiled data.
                  -- If workflow ran successfully, continue to run post-
                     processing script. Else exit with errors.
              - Run post-processing script : parser()
                  -- Creates a folder under samplename_datetimestamp called 
                     post_processed_stats.
                  -- Takes each run.* directory and generates the parsed csv data 
                     and relating png plots for the full workflow.
                  -- If post-processing script ran successfully, exit main 
                     successfully. Else exit with errors.
    Usage:
         workflow_profiler.py [-h] [-pr PROFILING] [-pp POST_PROCESSING]
                              [-int SAMPLING_INTERVAL] [-w SLIDING_WINDOW]
                              [-p] [-A] [-s] [-i]
                              workflow_script workflow_name sample_name
                              no_of_threads input_directory output_directory

    Examples:
    1. Run a workflow and capture both profiling and post-processing data with 
       default settings, all stats collected and plotting enabled
       $ workflow_profiler.py data_collection_dnaworkflow.pl workflow_name
         simulated 16 /data/simulated/ /foo/test/ -Ap
    2. Run a workflow and capture only profiling data with different sampling
       interval and only sar collected
       $ workflow_profiler.py data_collection_dnaworkflow.pl workflow_name
         simulated 16 /data/simulated/ /foo/test/ -pp 0 -int 100 -s
"""

import os
import sys
import re
import argparse
import subprocess
import time
import datetime


################################
# Main Function
################################
def main(argv=None):
    """
    PURPOSE: The entry point for the program. First receives, parses, and
             validates arguments; and then calls the workflow and parser scripts.

    INPUTS:  argv - a list holding the command line user arguments

    OUTPUTS: "Completed Successfully" on success. If non-recoverable error, 
             exits program.

    ALGORITHM (the steps):
        1. Capture arguments
        2. Parse arguments
        3. Validate arguments  
        4. Run workflow and parser 
    """
    
    #global variables for workflow folder, return codes for workflow and post-processing scripts are declared within each function. 

    ## 1. Get arguments from sys.argv
    if argv is None:
        argv=sys.argv[1:]
    
    # Create object for handling the above input 
    input=UserInput()

    ## 2. Parse arguments
    args=input.parse_args(argv)
 
    ## 3. Validate arguments
    validate_list=input.validate_args(args)
    if validate_list[1] is None:
        print("MAIN:: Error found when checking user specified arguments.")
        print("       Exiting now.\n")
        sys.exit()
    
    args = validate_list[1] # Update main's args namespace


    # Create object for handling the workflow and parser 
    run=executeWorkflow()

    ## 4. Run the workflow and Post-processing script
    # if pr = 0 : run workflow but don't run parser (even if pp = 1). 
    # if pr = 1 : run workflow and if retcode_workflow == 0 and if pp = 1, run parser
    if int(args.profiling) == 0:
        print("MAIN:: Profiling is switched off.")
        print("       This script will only run the workflow. There will be no data to post-process.\n")
        run.profiler(args)
        if retcode_workflow == 0:
            print("MAIN:: workflow without profiling ran successfully.")
            print("       Data is present in \'%s\'" %(args.output_directory))
            print("       Exiting now.\n")
            sys.exit()
        else:
            print("MAIN:: workflow without profiling returned errors. Verify the output.log for more information.")
            print("       Exiting now.\n")
            sys.exit()
    else:
        run.profiler(args)
        if retcode_workflow == 0:
            if int(args.post_processing) == 1:
                run.parser(args)
                if retcode_parser == 0:
                    print("MAIN:: Workflow Profiler completed successfully.")
                    print("       Data is present in \'%s\'" %(args.output_directory))
                    print("       Exiting now.\n")
                    sys.exit()
                else:
                    print("MAIN:: Post-processing returned errors. Need to verify the script.")
                    print("       Exiting now.\n")
                    sys.exit()
            else:
                print("MAIN:: Post-processing (creating csv's and plots) was not requested by the user.")
                print("       Data is present in \'%s\'" %(args.output_directory))
                print("       Exiting now.\n")
                sys.exit()       
        else:
            print("MAIN:: workflow returned errors. Verify the output.log for more information.")
            print("       Execution of parser script is called off due to the above errors.")
            print("       Exiting now.\n")
            sys.exit()

#-------------------------------
# User Interaction
#-------------------------------
class UserInput:
    """
    PURPOSE: Parses and validates the command line inputs.
    """

    def parse_args(self, argv):
        """
        PURPOSE: Parses the command line arguments

        INPUTS:  argument vector

        OUTPUTS: Returns a namespace object of the parsed args as parsed by
                 argparse.parse_args().

        CALLEES: main()
        """
	parser = argparse.ArgumentParser(description = '''
                workflow_profiler collects data and post-processes the data.
        ''')
        
        # positional parameters 
        parser.add_argument("workflow_script", help="Enter the location of your workflow script. Example: /foo/data_collection_workflow.pl")
        parser.add_argument("workflow_name", help="Enter the name of your workflow")
	parser.add_argument("sample_name", help="Enter the name of the sample")
	parser.add_argument("no_of_threads", help="Enter the number of threads you want to run on")
	parser.add_argument("input_directory", help="Enter the directory where the input files are located")
	parser.add_argument("output_directory", help="Enter the directory where the output data will be stored")
         
        # optional parameters 
        parser.add_argument("-pr", "--profiling", help="Do you want to profile the workflow? ON by default", default='1')
        parser.add_argument("-pp", "--post-processing", help="Do you want to run the parser to generate CSVs and plots? ON by default", default='1')
        parser.add_argument("-int", "--sampling_interval", help="Sampling interval for profiling in seconds. Default=30", default='30')
        parser.add_argument("-w", "--sliding_window", help="Sliding window (average) for plots in seconds. Default=100", default='100')
        parser.add_argument("-p", "--plot", help="Plot all data", action='store_true')

        # Required group to force user to pick at least one stats flag
        stats = parser.add_argument_group('statistics', 'statistics options')
        stats.add_argument("-A", "--all", help="Parse all statistics", action='store_true')
        stats.add_argument("-s", "--sar", help="Parse sar information", action='store_true')
        stats.add_argument("-i", "--iostat", help="Parse iostat information", action='store_true')
        #stats.add_argument("-m", "--mpstat", help="Parse mpstat info (cpu)", action='store_true')
        #stats.add_argument("-f", "--free", help="Parse free information", action='store_true')
 
        args = parser.parse_args(args=argv) ## returns namespace object containing args
	return args
    
    def validate_args (self, args_ns):
        """ 
        PURPOSE: Validates user arguments
        
        INPUTS: args_ns: argument namespace as parsed by argparse.parse_args 
        
        OUTPUTS: A list of two elements: [rc, args_ns] or [rc, None] 

        SUCCESS - [rc, args_ns] 
            rc: integer return code which is 0 on success. 
            args_ns: This make if possible for other users of the arguments to 
                 access the options, and to change easily the value of an 
                 option if necessary and pass that back to the caller.

        FAILURE - [rc, None]
            rc:   integer > 0.  It is caller's responsibility to handle failure.
            None: return None instead of args_ns
        
        CALLEES: main()
        """
        ### Validating the workflow script, workflow name, input directory and output directory for now.
        ## return codes
        success = 0
        ps_err = 1                #workflow script error
        id_err = 2                #input directory error
        od_err = 3                #output directory error
        od_len_err = 4            #output directory length error
        stats_err = 5             # stats argument error
        rlist = [success,args_ns] #return on success
        err_list = [-1, None]     #return on error           

        ## 1.Check that workflow_script is a valid file
        ps = args_ns.workflow_script
        if (os.path.isabs(ps) == False):
            ps = os.path.abspath(ps)
            args_ns.workflow_script = ps # change the namespace value
            rlist[1] = args_ns
        if (os.path.isfile(ps) == False):
            #check that the file exists
            print("validate_args:: Error: workflow Script \'%s\' doesnt exist." %(ps))
            err_list[0] = ps_err
            return err_list
        #print("validate_args:: workflow script \'%s\' passes validation!" % (ps))     
        
        ## 2.Check that 'id' is a valid directory
        id = args_ns.input_directory
        if os.path.isabs(id) == False:
            id = os.path.abspath(id)
            args_ns.input_directory = id #change the namespace value
            rlist[1] = args_ns
        if (os.path.isdir(id) == False):
            #check the path before basename for validity
            print("validate_args:: Error: Input directory \'%s\' is not a valid directory" % (id))
            err_list[0] = id_err
            return err_list
        #print("validate_args:: Input directory \'%s\' passes validation!" % (id))
 
        ## 3.Check that 'od' is a valid directory and create a directory within it for storing the output
        od = args_ns.output_directory
        if os.path.isabs(od) == False:
             od = os.path.abspath(od)
	if (os.path.isdir(od) == False):
             #check the path before basename for validity
             print("validate_args:: Error: Output directory \'%s\' is not a valid directory" % (od))
             err_list[0] = od_err
             return err_list
        #print("validate_args:: Output directory \'%s\' passes validation!" % (od))
        
        # Check for the length of the output directory and error if it is more than 100 characters.
        if len(od) > 100:
            print("validate_args:: Error: The output directory's character count is more than 100 characters.")
            print("                       We are restricting to 100 characters to accomodate the sar data that will be generated.")
            err_list[0] = od_len_err
            return err_list
	
        #Creating folder for storing the output.
        if not od.endswith("/"): od = od + "/"
        dt = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        od = od + args_ns.sample_name + "_" + args_ns.workflow_name + "_" + args_ns.no_of_threads + "t_" + str(args_ns.sampling_interval) + "s_" + dt + "/"
        if not os.path.exists(od): os.makedirs(od)
	args_ns.output_directory = od #change the namespace value
        rlist[1] = args_ns

        ## 4.Check for sampling_interval and sliding window for profiling
        interval = int(args_ns.sampling_interval)
        window = int(args_ns.sliding_window)
        if not 5 <= interval <= 120: 
	    print("validate_args:: Warning: Preferable to have sampling interval %ds within the bounds of 5s and 120s" % interval)
        #else:
	    #print("validate_args:: Sampling interval passes validation")
        if not window > 2*interval:
	    print("validate_args:: Warning: Preferable to have sliding window %ds more than twice that of sampling interval %ds" % (window,interval))
                   
 
        ## 5.Check for 'all' stats, and if not true check that at least one of the other stats are selected
        ## Check for stats only if profiling and post-processing are requested. 
        if int(args_ns.profiling) or int(args_ns.post_processing) == 1:
            all = args_ns.all
            sar = args_ns.sar
            iostat = args_ns.iostat
            #mpstat = args_ns.mpstat
            #free = args_ns.free

            stats_error_msg = "A|--all, -s|--sar, -i|--iostat" # -m|--mpstat, -f|--free

            #if not any([all, sar, iostat, mpstat, free]):
            if not any([all, sar, iostat]):
                print("validate_args:: Profiling and/or post-procssing are enabled by default.")
                print("validate_args:: Error: Choose at least one statistic to parse:")
                print("                " + stats_error_msg)
                print("                Also enable -p if you want post-processing script to generate plots.")
                err_list[0] = stats_err
                return err_list
            #print("validate_args:: Statistics check passes validation!")

        rlist[1] = args_ns  ## update the return list before returning
        return rlist

#-----------------------------
# Run workflow and Parser
#-----------------------------
class executeWorkflow():
    """
    PURPOSE: Run the pipeine and the parser for generating workflow output and csv and plots
    """
    
    def profiler(self, args):
        """
        PURPOSE: Run the workflow script with the provided command line arguments

        INPUTS:  args

        OUTPUTS: Returns a code to the main function to indicate success/failure. 
                 A folder with output files and run.* directories for profiled  data.

        CALLEES: main()
        """
        
        #return code for workflow script to be checked in the main function for errors.
        global retcode_workflow
        
        # location of collect_stats.ksh script to be passed in to the pipeline script
        collect_stats_path = os.getcwd() + '/collect_stats.ksh'

        #Args for running the workflow
        collect_stats = []
        if args.all: collect_stats.append("--sar --iostat")
        if args.sar: collect_stats.append("--sar")
        if args.iostat: collect_stats.append("--iostat")
        #if args.mpstat: collect_stats.append("--mpstat")
        #if args.free: collect_stats.append("--free")
        collect_stats = [' '.join(collect_stats)]
        
        # Only the valid arguments are passed based on whether profiling is enabled or not
        if int(args.profiling) == 1: workflow_args = [args.workflow_script, args.sample_name, args.no_of_threads, args.input_directory, args.output_directory, args.profiling, collect_stats_path, args.sampling_interval] + collect_stats
	else: workflow_args = [args.workflow_script, args.sample_name, args.no_of_threads, args.input_directory, args.output_directory, args.profiling]
        
        print("Running the workflow script... \n")

        retcode_workflow = subprocess.check_call(workflow_args)
        return(retcode_workflow)

    def parser(self, args):
        """
        PURPOSE: Run the post-processing script with the provided command line arguments

        INPUTS:  args

        OUTPUTS: Returns a code to the main function to indicate success/failure. 
                 A post_processed_stats folder with csv's and plots.

        CALLEES: main()
        """
         
        #return code for parser script to be checked in the main function for errors.
        global retcode_parser
        
        #Creating folder for storing the post processed stats
        parser_path= os.getcwd() + "/workflow_stats_parser/workflow_stats_parser.py"
        profiling_folder = args.output_directory + 'post_processed_stats'
        if not os.path.exists(profiling_folder): os.makedirs(profiling_folder)
        
        # Support for a single stage is not provided here. To do so, run the stand-alone parser script
        #Args for running the parser
        parser_args = [parser_path, args.output_directory, "-o", profiling_folder, "-w", args.sliding_window, "-N", args.workflow_name.lower(), "-l", "debug"]
        #Doing this crude method because subprocess doesn't like the TRUE/FALSE boolean args that is provided for the statistics arguments. 
        if args.plot: parser_args.append("-p")
        if args.all: parser_args.append("-A")
        if args.sar: parser_args.append("-s")
        if args.iostat: parser_args.append("-i")
        #if args.mpstat: parser_args.append("-m")
        #if args.free: parser_args.append("-f")
        
        print("\nRunning the post-processing script... \n")

        retcode_parser=subprocess.check_call(parser_args)
        return(retcode_parser)
  
################################
# Entry Point for Profiler
################################
if __name__ == "__main__":
    #os.system('clear')
    print("Running the Intel Workflow Profiler package...\n") 
    sys.exit(main())
