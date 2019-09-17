#!/usr/bin/env python3

"""
Script for auto initialization of EPICS Motion Controller IOCs.
It uses https://github.com/epicsNSLS2-deploy/motor-ioc-template as the IOC base.

Usage instructions can be found in the README.md file in this repo.

Author: Jakub Wlodek
"""

# imports
import os
import re
import subprocess
import datetime
from sys import platform


# version number
version = "v0.0.1"


# Bash shebang length limit is 127 characters, so we need to make sure we account for that
KERNEL_PATH_LIMIT = 127

supported_drivers = [
    'motorNewFocus'
]

class MotorIOCAction:


    def __init__(self, ioc_type, ioc_name, ioc_prefix, ioc_port, connection, ioc_num):
        """
        Constructor for the MotorIOCAction class
        Parameters
        ----------
        ioc_type : str
            name of EPICS motor module driver. ex. motorNewFocus
        ioc_name : str
            name of the IOC ex. pico97
        ioc_prefix : str
            Prefix used by the IOC
        ioc_port : str
            telnet port on which procserver will run the IOC
        connection : str
            Value used to connect to the device ex. IP, serial num. etc.
        ioc_num : int
            Counter that keeps track of which IOC it is
        """

        self.ioc_type   = ioc_type
        self.ioc_name   = ioc_name
        self.ioc_prefix = ioc_prefix
        self.ioc_port   = ioc_port
        self.connection = connection
        self.ioc_num    = ioc_num



    def convert_st_cmd(self, ioc_top, bin_loc, bin_flat, binary_path):
        """ Function responsible for convertion st.cmd file in IOC template based on configuration """

        initIOC_print("IOC template cloned, converting st.cmd")
        ioc_path = ioc_top +"/" + self.ioc_name

        startup_path = ioc_path+"/startupScripts"
        startup_type = self.ioc_type[5:].lower()

        for file in os.listdir(ioc_path +"/startupScripts"):
            if startup_type in file.lower():
                startup_path = startup_path + "/" + file
                break
        
        exe_written = False
        example_st = open(startup_path, "r+")

        if platform =='win32':
            st_exe = open(ioc_path+'/st.cmd', 'w+')
            st_exe.write(binary_path+' st_base.cmd\n')
            st_exe.close()
            st = open(ioc_path+"/st_base.cmd", "w+")
            exe_written = True

        elif len(binary_path) > KERNEL_PATH_LIMIT:     # The path length limit for shebangs (#!/) on linux is usually kernel based and set to 127
            initIOC_print('WARNING - Path to executable exceeds legal bash limit, generating st.cmd and st_base.cmd')
            st_exe = open(ioc_path + '/st.cmd', 'w+')
            st_exe.write(binary_path + ' st_base.cmd\n')
            st = open(ioc_path+"/st_base.cmd", "w+")
            st_exe.close()
            exe_written = True
        else:
            st = open(ioc_path+"/st.cmd", "w+")

        line = example_st.readline()
        while line:
            if "#!" in line:
                if not exe_written:
                    st.write("#!" + binary_path + "\n")
            elif "envPaths" in line:
                st.write("< envPaths\n")
            else:
                st.write(line)
            line = example_st.readline()

        example_st.close()
        st.close()


    def convert_as_and_dep(self, ioc_top, bin_loc, bin_flat):
        """ Function repsonsible for setting up autosave and dependency files """

        ioc_path = ioc_top +"/" + self.ioc_name
        autosave_path = ioc_path + "/autosaveFiles"
        autosave_type = self.ioc_type[5:].lower()
        if os.path.exists(autosave_path + "/" + autosave_type + "_auto_settings.req"):
            initIOC_print("Generating auto_settings.req file for IOC {}.".format(self.ioc_name))
            os.rename(autosave_path + "/" + autosave_type + "_auto_settings.req", ioc_path + "/auto_settings.req")
        else:
            initIOC_print("Could not find supported auto_settings.req file for IOC {}.".format(self.ioc_name))

        if os.path.exists(ioc_path + "/dependancyFiles"):
            for file in os.listdir(ioc_path + "/dependancyFiles"):
                if file.lower().startswith(autosave_type):
                    initIOC_print('Copying dependency file {} for {}'.format(file, self.ioc_type))
                    # Copy all required dependency files
                    os.rename(ioc_path + "/dependancyFiles/" + file, ioc_path + "/" + file.split('_', 1)[-1])
                    self.fix_macros(ioc_path + '/' + file.split('_', 1)[-1])


    def process(self, ioc_top, bin_loc, bin_flat):
        """
        Function that clones ioc-template, and pulls correct st.cmd from startupScripts folder
        The binary for the IOC is also identified and inserted into st.cmd
        Parameters
        ----------
        ioc_top : str
            Path to the top directory to contain generated IOCs
        bin_loc : str
            path to top level of binary distribution
        bin_flat : bool
            flag for deciding if binaries are flat or stacked
        Returns
        -------
        int
            0 if success, -1 if error
        """

        initIOC_print("-------------------------------------------")
        initIOC_print("Setup process for IOC " + self.ioc_name)
        initIOC_print("-------------------------------------------")
        # Checks to see if we should even try to clone + setup
        if os.path.exists(ioc_top + '/' + self.ioc_name):
            initIOC_print('ERROR - IOC with name {} already exists in {}.'.format(self.ioc_name, ioc_top))
            return -1
        binary_path =  self.getIOCBin(bin_loc, bin_flat) 
        if binary_path is None:
            initIOC_print('ERROR - Could not identify a compiled IOC binary for {}, skipping'.format(self.ioc_type))
            initIOC_print('Make sure that the binary exists and is compiled in the expected location.')
            return -1
        # Clone the template
        out = subprocess.call(["git", "clone", "--quiet", "https://github.com/epicsNSLS2-deploy/motor-ioc-template", ioc_top + "/" + self.ioc_name])
        if out != 0:
            initIOC_print("Error failed to clone IOC template for ioc {}".format(self.ioc_name))
            return -1
        else:
            # Convert all of the required files
            self.convert_st_cmd(ioc_top, bin_loc, bin_flat, binary_path)
            self.convert_as_and_dep(ioc_top, bin_loc, bin_flat)

            return 0



    def update_unique(self, ioc_top, bin_loc, bin_flat, prefix, engineer, hostname, ca_ip):
        """
        Function that updates the unique.cmd file with all of the required configurations
        Parameters
        ----------
        ioc_top : str
            Path to the top directory to contain generated IOCs
        bin_loc : str
            path to top level of binary distribution
        bin_flat : bool
            flag for deciding if binaries are flat or stacked
        prefix : str
            Prefix given to the IOC
        engineer : str
            Name of the engineer deploying the IOC
        hostname : str
            name of the host IOC server on which the IOC will run
        ca_ip : str
            Channel Access IP address
        """

        if os.path.exists(ioc_top + "/" + self.ioc_name +"/unique.cmd"):
            initIOC_print("Updating unique file based on configuration.")
            unique_path = ioc_top + "/" + self.ioc_name +"/unique.cmd"
            unique_old_path = ioc_top +"/" + self.ioc_name +"/unique_OLD.cmd"
            os.rename(unique_path, unique_old_path)

            uq_old = open(unique_old_path, "r")
            uq = open(unique_path, "w")
            line = uq_old.readline()
            while line:
                if not line.startswith('#'):
                    if "SUPPORT_DIR" in line:
                        if bin_flat:
                            uq.write('epicsEnvSet("SUPPORT_DIR", "{}")\n'.format(bin_loc))
                        else:
                            uq.write('epicsEnvSet("SUPPORT_DIR", "{}")\n'.format(bin_loc + "/support"))
                    elif "ENGINEER" in line:
                        uq.write('epicsEnvSet("ENGINEER", "{}")\n'.format(engineer))
                    elif "CAM-CONNECT" in line:
                        uq.write('epicsEnvSet("MC_CONNECT", "{}")\n'.format(self.connection))
                    elif "HOSTNAME" in line:
                        uq.write('epicsEnvSet("HOSTNAME", "{}")\n'.format(hostname))
                    elif '("MC"' in line:
                        uq.write('epicsEnvSet("MC", "MC:{}")\n'.format(self.ioc_num))
                    elif '("CT"' in line:
                        uq.write('epicsEnvSet("CT", "{}")\n'.format(prefix))
                    elif "PREFIX" in line and "MC_PREFIX" not in line:
                        uq.write('epicsEnvSet("PREFIX", "{}")\n'.format(prefix + "{{{}}}".format(self.ioc_type[5:] +"IOC:MC{}".format(self.ioc_num))))
                    elif "IOCNAME" in line:
                        uq.write('epicsEnvSet("IOCNAME", "{}")\n'.format(self.ioc_name))
                    elif "EPICS_CA_ADDR_LIST" in line:
                        uq.write('epicsEnvSet("EPICS_CA_ADDR_LIST", "{}")\n'.format(ca_ip))
                    elif "IOC" in line and "IOCNAME" not in line:
                        uq.write('epicsEnvSet("IOC", "{}")\n'.format("ioc"+self.ioc_type))
                    else:
                        uq.write(line)
                else:
                    uq.write(line)
                line = uq_old.readline()

            uq_old.close()
            uq.close()
        else:
            initIOC_print("No unique file found, proceeding to next step.")


    def update_config(self, ioc_top, hostname):
        """
        Function that updates the config file with the correct IOC name, port, and hostname
        Parameters
        ----------
        ioc_top : str
            Path to the top directory to contain generated IOCs
        hostname : str
            name of the host IOC server on which the IOC will run
        """

        conf_path = ioc_top + "/" + self.ioc_name + "/config"
        if os.path.exists(conf_path):
            initIOC_print("Updating config file for procServer connection.")
            conf_old_path = ioc_top + "/" + self.ioc_name + "/config_OLD"
            os.rename(conf_path, conf_old_path)
            cn_old = open(conf_old_path, "r")
            cn = open(conf_path, "w")
            line = cn_old.readline()
            while line:
                if "NAME" in line:
                    cn.write("NAME={}\n".format(self.ioc_name))
                elif "PORT" in line:
                    cn.write("PORT={}\n".format(self.ioc_port))
                elif "HOST" in line:
                    cn.write("HOST={}\n".format(hostname))
                else:
                    cn.write(line)
                line = cn_old.readline()
            cn_old.close()
            cn.close()
        else:
            initIOC_print("No config file found moving to next step.")


    def fix_env_paths(self, ioc_top, bin_flat):
        """
        Function that fixes the envPaths file if binaries are not flat
        Parameters
        ----------
        ioc_top : str
            Path to the top directory to contain generated IOCs
        bin_flat : bool
            flag for deciding if binaries are flat or stacked
        """

        env_path = ioc_top + "/" + self.ioc_name + "/envPaths"
        if os.path.exists(env_path):
            env_old_path = ioc_top + "/" + self.ioc_name + "/envPaths_OLD"
            os.rename(env_path, env_old_path)
            env_old = open(env_old_path, "r")
            env = open(env_path, "w")
            line = env_old.readline()
            while line:
                if line.startswith('epicsEnvSet("ARCH",'):
                    if platform == 'win32':
                        env.write('epicsEnvSet("ARCH",       "windows-x64-static")\n')
                    else:
                        env.write('epicsEnvSet("ARCH",       "linux-x86_64")\n')
                elif "EPICS_BASE" in line and not bin_flat:
                    initIOC_print("Detected non-flat binaries, fixing base location in envPaths.")
                    env.write('epicsEnvSet("EPICS_BASE", "$(SUPPORT)/../base")\n')
                else:
                    env.write(line)
                line = env_old.readline()
            env_old.close()
            env.close()


    def getIOCBin(self, bin_loc, bin_flat):
        """
        Function that identifies the IOC binary location based on its type and the binary structure
        Parameters
        ----------
        bin_loc : str
            path to top level of binary distribution
        bin_flat : bool
            flag for deciding if binaries are flat or stacked
        
        Return
        ------
        driver_path : str
            Path to the IOC executable located in driverName/iocs/IOC/bin/OS/driverApp or None if not found
        """

        try:
            if bin_flat:
                # if flat, there is no support directory
                driver_path = bin_loc + "/motor/modules/" + self.ioc_type
            else:
                driver_path = bin_loc + "/support/motor/modules/" + self.ioc_type
            # identify the IOCs folder
            for name in os.listdir(driver_path):
                if "ioc" == name or "iocs" == name:
                    driver_path = driver_path + "/" + name
                    break
            # identify the IOC 
            for name in os.listdir(driver_path):
                # Add check to see if NOIOC in name - occasional problems generating ADSimDetector
                if ("IOC" in name or "ioc" in name) and "NOIOC" not in name.upper():
                    driver_path = driver_path + "/" + name
                    break 
            # Find the bin folder
            driver_path = driver_path + "/bin"
            # There should only be one architecture
            for name in os.listdir(driver_path):
                driver_path = driver_path + "/" + name
                break
            # We look for the executable that ends with App
            for name in os.listdir(driver_path):
                driver_path = driver_path + "/" + name
                break

            return driver_path
        except FileNotFoundError:
            return None


    def fix_macros(self, file_path):
        """
        Function that replaces certain macros in given filepath (used primarily for substitution files)
        Parameters
        ----------
        file_path : str
            path to the target file
        """

        os.rename(file_path, file_path + '_OLD')
        old = open(file_path+'_OLD', 'r')
        contents = old.read()
        contents = contents.replace('$(PREFIX)', self.ioc_prefix)
        new = open(file_path, 'w')
        new.write(contents)
        old.close()
        new.close()
        os.remove(file_path+'_OLD')


    def create_path_scripts(self, bin_loc, bin_flat, ioc_top):
        """
        Function that attempts to create scripts for setting the dev environment for the IOC given the location of the binaries.
        Parameters
        ----------
        bin_loc : str
            given path to binaries
        bin_flat : bool
            toggle that determines if the binaries have a flat structure or not
        ioc_top : str
            path to the ioc output_directory
        """

        if platform == "win32":
            delimeter = ';'
            closer = '%PATH%"'
            arch='windows-x64-static'
            path_file = open(ioc_top + '/' + self.ioc_name + '/dllPath.bat', 'w+')
            path_file.write('@ECHO OFF\n')
            path_file.write('SET "PATH=')
        else:
            delimeter = ':'
            closer = '$LD_LIBRARY_PATH'
            arch = 'linux-x86_64'
            path_file = open(ioc_top + '/' + self.ioc_name + '/ldpath.sh', 'w+')
            path_file.write('export LD_LIBRARY_PATH=')
        path_file.write(bin_loc + '/base/lib/' + arch)
        path_file.write(delimeter)
        support_dir = bin_loc
        if not bin_flat:
            support_dir = bin_loc + '/support'

        if os.path.exists(support_dir) and os.path.isdir(support_dir):
            for dir in os.listdir(support_dir):
                if os.path.isdir(support_dir + '/' + dir) and dir != "base" and dir != "areaDetector":
                    path_file.write(support_dir + '/' + dir + '/lib/' + arch)
                    path_file.write(delimeter)

        path_file.write(closer)
        path_file.close()


    def cleanup(self, ioc_top):
        """ Function that runs the cleanup.sh/cleanup.bat script in ioc-template to remove unwanted files """

        cleanup_completed = False

        if platform == "win32":
            if os.path.exists(ioc_top + '/' + self.ioc_name + '/cleanup.bat'):
                initIOC_print('Performing cleanup for {}'.format(self.ioc_name))
                out = subprocess.call([ioc_top + '/' + self.ioc_name + '/cleanup.bat'])
                initIOC_print('')
                cleanup_completed = True
                os.remove(ioc_top + '/' + self.ioc_name + '/cleanup.bat')
        else:
            if os.path.exists(ioc_top + '/' + self.ioc_name + '/cleanup.sh'):
                initIOC_print('Performing cleanup for {}'.format(self.ioc_name))
                out = subprocess.call(['bash', ioc_top + '/' + self.ioc_name + '/cleanup.sh'])
                initIOC_print('')
                cleanup_completed = True
                os.remove(ioc_top + '/' + self.ioc_name + '/cleanup.sh')
        if os.path.exists(ioc_top + '/' + self.ioc_name + '/st.cmd'):
            os.chmod(ioc_top + '/' + self.ioc_name + '/st.cmd', 0o755)
        if not cleanup_completed:
            initIOC_print('No cleanup script found, using outdated version of Motor IOC template')


def initIOC_print(text):
    """
    A wrapper function for 'print' that allows for printing to CLI or to log
    """

    print(text)


def print_start_message():
    """ Function for printing initial message """

    initIOC_print("+----------------------------------------------------------------+")
    initIOC_print("+ initMotorIOCs, Version: " + version +"                                 +")
    initIOC_print("+ Author: Jakub Wlodek                                           +")
    initIOC_print("+ Copyright (c): Brookhaven National Laboratory 2018-2019        +")
    initIOC_print("+ This software comes with NO warranty!                          +")
    initIOC_print("+----------------------------------------------------------------+")
    initIOC_print('')


def print_supported_drivers():
    """ Function that prints list of supported drivers """

    initIOC_print('Supported Drivers:')
    initIOC_print("+-----------------------------+")
    for driver in supported_drivers:
        initIOC_print('+ {}'.format(driver))
    initIOC_print('')


def execute_ioc_action(action, configuration, bin_flat):
    """
    Function that runs all required IOC action functions with a given configuration
    Parameters
    ----------
    action : IOCAction
        currently executing IOC action
    configuration : dict of str to str
        configuration settings as read from CONFIGURE or inputted by user
    bin_flat : bool
        toggle that tells the script if binaries are flat of not
    """

    # Perform the overall process action
    out = action.process(configuration["IOC_DIR"], configuration["TOP_BINARY_DIR"], bin_flat)
    # if successfull, update any remaining required files
    if out == 0:
        action.update_unique(configuration["IOC_DIR"], configuration["TOP_BINARY_DIR"], bin_flat, 
                action.ioc_prefix, configuration["ENGINEER"], configuration["HOSTNAME"], 
            configuration["CA_ADDRESS"])
        action.update_config(configuration["IOC_DIR"], configuration["HOSTNAME"])
        action.fix_env_paths(configuration["IOC_DIR"], bin_flat)
        action.create_path_scripts(configuration["TOP_BINARY_DIR"], bin_flat, configuration["IOC_DIR"])
        action.cleanup(configuration["IOC_DIR"])


def guided_init():
    """ Function that guides the user through generating a single IOC through the CLI """

    print_start_message()
    initIOC_print('Welcome to initMotorIOCs!')
    configuration = {}
    configuration['IOC_DIR']        = input('Enter the ioc output location. > ')
    configuration['TOP_BINARY_DIR'] = input('Enter the location of your compiled binaries. > ')
    bin_flat = True
    if os.path.exists(configuration['TOP_BINARY_DIR']):
        if os.path.exists(os.path.join(configuration['TOP_BINARY_DIR'], 'support')):
            bin_flat = False
    configuration['HOSTNAME']   = input('Enter the IOC server hostname. > ')
    configuration['ENGINEER']   = input('Enter your name and contact information. > ')
    configuration['CA_ADDRESS'] = input('Enter the CA_ADDRESS IP. > ')
    another_ioc = True
    while another_ioc:
        driver_type = None
        while driver_type is None:
            driver_type = input('What driver type would you like to generate? > ')
            if driver_type not in supported_drivers:
                driver_type = None
                initIOC_print('The selected driver type is not supported. See list of supported drivers below.')
                print_supported_drivers()
        ioc_name = input('What should the IOC name be? > ')
        #port = input('What port should the IOC use? (ex. P0). > ')
        #controller_port = input('What should the controller port be? (ex. M0) > ')
        mc_number = input('What should the motion controller number be? (ex. MC:37) > ')
        prefix = input('What should the controller prefix be? (ex. XF:10IDC-CT) > ')
        ioc_port = input('What telnet port should procServer use to run the IOC? > ')
        connection = input('Enter the connection param for your device. (ex. IP, serial number etc.) enter NA if not sure. > ')
        #ioc_action = MotorIOCAction(driver_type, ioc_name, port, controller_port, mc_number, ct_prefix, ioc_port, connection)
        ioc_action = MotorIOCAction(driver_type, ioc_name, prefix, ioc_port, connection, mc_number)
        execute_ioc_action(ioc_action, configuration, bin_flat)
        another = input('Would you like to generate another IOC? (y/n). > ')
        if another != 'y':
            another_ioc = False
    initIOC_print('Done.')


guided_init()