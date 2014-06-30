Workflow Profiler         
=====================

Released under The MIT License (refer to LICENSE file)

Software Requirements:
----------------------

Software          | Version   | Test Version  | Purpose 
------------------| ----------| --------------|-------------------------------
Python            |   2.7     |     2.7       | profiler and post-processing
gnuplot           | >= 4.6    |    4.6.3      | plots for post-processing
Perl              |  5.10.1   |    5.10.1     | generating workflow script
collect_stats.ksh |   0.1     |     0.1       | data collection
kill_scripts/     |   0.1     |     0.1       | halting data collection
systat            |  9.0.4**  |    9.0.4      | Sar and Iostat tool

** We have tested with systat 9.0.4, and have built-in support for older 
versions by using --legacy option in sar. However, behavior with older versions 
is not guaranteed. 


Summary: 
--------

User-defined workflows or pipelines can be defined as an ordered sequence of one or more processing stages. Workflow Profiler provides users with a fast and an automated means to profile and understand coarse-grain resource utilization for user-defined workflows by using freely available Linux profiling tools. It allows for easy definition of workflows, and maintains explicit partition of the individual stages to provide the user with a clear view of the system utilization across the various stages while still offering a unified view of the overall workflow. It is a complete package that automates the execution of the workflow, stats collection, and post-processes the profiled data to generate CSVs and plots illustrating the resource utilization. 

The overall workflow profiling can be broken down into two main stages:

1. Workflow execution and data collection: 
   - Workflows are generally scripted by the end user to automate execution of 
     the different stages comprising a workflow. 
   - We instrument a typical workflow script to enable data collection. 
     data_collection_workflow_template.pl is provided as an example, with 
     profiling enabled via collect_stats.ksh, both of which are described later.

2. Post-processing: 
   - Post-process raw data collected using linux profiling tools such as 'sar', 
     and generate charts which illustrate resource utilization for a given 
     workflow. 
   - workflow_stats_parser.py in workflow_stats_parser folder provides an 
     automated way of parsing and plotting raw data collected for a given 
     workflow (consisting of a single stage or multiple stages). Refer to
     section on Workflow Stats Parser for details.


Steps to execute and profile a new workflow:
--------------------------------------------
1. Create a workflow based on data_collection_workflow_template.pl, where each 
   stage of the workflow is preceeded by a call to start profiling, and 
   followed by a call to stop profiling. For each stage, specify a stage tag 
   to identify the stage. If profiling option is turned ON, system-level data 
   will be gathered via linux profiling tools such as 'sar' and 'iostat'. 
   collect_stats.ksh script is used to automate data collection for various 
   profiling tools.
   OR
   Modify your existing workflow script by adding calls to start and stop 
   profiling for each stage in the workflow via collect_stats.ksh, using the 
   template as an example. 

2. Add a dictionary to the workflow_stats_parser/workflow_dictionaries.py 
   that specifies the order of the various stages in your workflow (corresponding the stage tag 
   used in 1))

3. For sar data files, the character count for the full path name is restricted 
   to 254. Inorder to not exceed it, please keep the profiler's output directory
   path relatively short and specify the above dictionary with relevant but 
   small stage names.
   

Additional features:
--------------------
1. Archiving: Output directories are timestamped, hence user can run the 
   profiler multiple times and achieve automatic archiving of resulting data.

2. The workflow profiler script can be used in two ways:
   - Without profiling (If the user is interested in just the application data) 
      - Output directory will only have bam/sam/metrics files. No run.* dirs will be created. 
   - With profiling (If the user is interested in profiling data)
      - Output directory will have both bam/sam/metrics files and run.* dirs.

3. Post-processing only mode:  
   - If the profiled data is readily available, the post-processing script can 
     be run as a stand-alone script to generate CSVs and plots.
   - For details, refer to Workflow Stats Parser section.


Usage:
------

workflow_profiler.py : collects data for the workflow and post-processes the profiled data to 
generate csv's and plots.

Usage: workflow_profiler.py workflow_script workflow_name sample_name 
                            no_of_threads input_directory output_directory [flags]

positional arguments [Need to be provided in the following order]:
-  workflow_script        location of your workflow script. 
                        Example: /foo/data_collection_workflow.pl
-  workflow_name          name of your workflow.
-  sample_name            name of the sample
-  no_of_threads          number of threads you want to run on
-  input_directory        directory where the input files are located
-  output_directory       directory where the output data will be stored

optional arguments:
- -h, --help            show this help message and exit
- -pr PROFILING, --profiling PROFILING
                        Do you want to profile the workflow? ON by default
- -pp POST_PROCESSING, --post-processing POST_PROCESSING
                        Do you want to run the parser to generate CSVs and
                        plots? ON by default
- -int SAMPLING_INTERVAL, --sampling_interval SAMPLING_INTERVAL
                        Sampling interval for profiling in seconds. Default=30
- -w SLIDING_WINDOW, --sliding_window SLIDING_WINDOW
                        Sliding window (average) for plots in seconds. 
                        Default=100
- -p, --plot            Plot all data

statistics: statistics options
- -A, --all             Parse all statistics
- -s, --sar             Parse sar information
- -i, --iostat          Parse iostat information

Examples:
-  Run a workflow and capture both profiling and post-processing data with 
   default settings (stats collected and plotting enabled)
   -   workflow_profiler.py data_collection_dnaworkflow.pl dnaworkflow simulated 16 /data/simulated/ /foo/test/ -Ap
-  Run a workflow and capture only sar profiling data with different sampling 
   interval (Post-processing is OFF)
   -   workflow_profiler.py data_collection_dnaworkflow.pl dnaworkflow simulated 16 /data/simulated/ /foo/test/ -pp 0 -int 100 -s 



Workflow Stats Parser
------------------------

The goal of the Workflow Stats Parser is to parse the raw data gathered using sar and iostat
and generate charts which illustrate resource utilization for workflows.
The parser supports post-processing both a single stage workflow as well as 
a multi-stage workflow.

This section describes the use of parser as a stand-alone tool. 

The parser package assumes data is collected using collect_stats.ksh, usage 
described below


1. Software Requirements

   Software  |  Version  | Test Version  | Purpose
   ----------|-----------|---------------|-----------------------------
   Python    |    2.7    |      2.7      | post-processing
   gnuplot   |  >= 4.6   |     4.6.3     | plots for post-processing 


2. HOW-TOs

   a. Usage and Argument/Options Description

      workflow_stats_parser.py root [arguments]
         arguments = [-N workflow_name] [-i | -s | -A] [-h] 
		     [-S substring] [-o output_folder] [-p] [-w size] [-t tag] 
                     [-l level] 

      a.1 Positional Arguments
          - root             path of directory containing workflow's profile data

      a.2 Required Arguments
         - -N, --workflow_name  workflow_name
              name of your workflow. Default is 'sample'.
         
         Statistics:
         - -i              parse iostat data
         - -s              parse sar data
         - -A              parse all data (iostat and sar)
         

      a.3 Optional Arguments
         - -h, --help                           
             show help message and exit

         - -S, --single_step stepSearchString
             To process a single stage of a known workflow.
             Specify a substring that is present in the stage output directory
               name. This will correspond to the 2nd item in the two-tuple in
               the ordered dictionary for the workflow.  See 'How to Add a New
               Workflow' section below.

         - -o, --output outputDir               
             Specify path to directory in which to save post-procesed data and 
               plots. The parser creates the directory if it does not exist.
             Default is post_processed_stats/ in current directory.

         - -p, --plot
             plot all data

         - -w, --sliding_window window          
             Window size in seconds to use for smoothing graphs. 
             Default is 100.
             We recommend starting with the default; if the graphs are not 
              smooth, then reprocess with a lower or higher window until the
              graphs look good.


         - -t, --tag
             Supply an optional identifier for the plot files
             Defaults to the name of the root directory for the profile data

         - -l, --log level                      
             Set the log level.
             Default level is 'info'.
             See 'Output Logger' section below for details.

   b. Usage Examples
      We show several examples of running the parser.  For sample output data 
        that is in the parser's directory, we have indicated this with an '*'.

      b.1 Full workflow using sample data
          - From sample_multistage_input:
             Run:
              ./workflow_stats_parser.py sample_multistage_input -N sample -o testing/multistage -isp

             *Output Sample Data: sample_multistage_output/

      b.2 Single stage using sample data
          - From sample_onestage_input:
             Run:
              ./workflow_stats_parser.py sample_onestage_input/ -N sample -S stage1 -o testing/stage1 -isp

             *Output Sample: sample_onestage_output/
          

          - One stage from sample_multistage_input:
             ./workflow_stats_parser.py sample_multistage_input -N sample -S stage2 -o testing/stage2 -isp 

   c. How to Add a New Workflow

      c.1 Python Ordered Dictionaries in the Parser
          For a new workflow edit the workflow_dictionaries.py 
          script by adding a new Ordered Dictionary that defines the order of the 
          workflow steps and search substrings that must exist in the directory 
          names of the workflow step's output. 

          We use ordered dictionaries to represent workflows because we need to 
          know the order of the pipline steps for summarizing profiled data in our 
          plots. We require a mapping of each step to the location of its 
          corresponding profiled data. 

     c.2 Structure of a Workflow Ordered Dictionary 
         The format for a two-tuple in a workflow ordered dictionary is:
  
           ('stepName', 'dirSearchSubstring')

          where:

           stepName           - the name of the workflow step (stage name)

           dirSearchSubstring - a unique substring from all other steps that 
                                 is present in the step's output directory
                                 name. 

           We use the user-supplied 'root' argument and the dirSearchSubtring
           to locate the correct data directory for each step. 
         
          
     c.3 Ordered Dictionary Examples
         
         The dictionary for the sample data set in this release is:

           sample_dict = OrderedDict([('Stage1','stage1'),
                                      ('Stage2','stage2'),
                                      ('Stage3','stage3')])
         
           The directory names for each step contains the substring specified
           for the step (second item in the two-tuple):

                 run.test..stage1.1u
                 run.test..stage2.1u
                 run.test..stage3.1u
     
         User can add their own dictionaries in workflow_dictionaries.py file. 

   d. Ouput Logger
      The logging level can be set to one of the levels listed below via the
      command line option.  Only messages as severe or more severe than the 
      level will be printed.

      Possible values (there are five Python-defined levels):
      info            - For routine event that might be of interest
      debug           - For messages useful to debugging, such as dumping variables

      Additional information about Python's logging module can be found at:
        https://docs.python.org/2.6/library/logging.html

#######################################################################################
#######################################################################################
If you are interested in the usage model for the componenets themselves, please 
find them below: 

data_collection_workflow_template.pl: Template for a workflow script.
---------------------------------------------------------------------
Current template and support is for a perl script. 

Usage: data_collection_workflow_template.pl SampleName NumThreads InputDirectory 
                            OutputDirectory profiling [optional]: interval stats

Mandatory Options: 
-  SampleName            name of the sample
-  NumThreads            number of threads you want to use
-  InputDataDirectory    directory where the input files are located
-  OutputDirectory       directory where the output data will be stored  
-  profiling             to profile the workflow or not? [Default:ON]

Optional:
-  interval             Interval for collection statistics. Default: 30s
-  stats                Pass in the tools you want to collect profiling data for. 

Example: 
data_collection_workflow.pl simulated 16 /data/simulated/ /foo/test/ 1 30 
"--sar --iostat"


collect_stats.ksh
-----------------
Usage: collect_stats.ksh <--sar || --iostat || --kill-all> <option list>
  
Mandatory Options:
- -n <FILE_PREFIX>        Prefix appended to all profiling filenames.
                              Default is the value of $FILE_PREFIX in this 
                              script. e.g., To append the data collection 
                              machine, 'node1', '-n node1'.
- -l <SLEEP>              Time (in seconds) before steady state
  sar/iostat options:
- -s <STEADY_STATE>       Length of steady state in minutes
- -d <SAR_INTERVAL>       Interval for sar,iostat in seconds (Default: 30s)
  sar common options:
- -u <USERS>              Number of users
  output directoy options:
- -tag <TAG>              a tag to be added to files and output dir to make,
                              if not provided script generates one
- -td <TARGET_DIRECTORY>  absolute directory where to place the files 
                              (i.e. ~/runs/run${TAG}), defaults to current dir

Note: -l, -u, and -s options are not used when collecting SAR data although 
required.

Examples:
1) Start SAR data collection:
"./collect_stats.ksh  --sar -td /foo/stats -n test -tag stage -l 5 -u 1 -s 600"
2) Stop data collection (to stop sar and iostat):
"collect_stats.ksh --kill-all" - uses the scripts under kill_scripts
