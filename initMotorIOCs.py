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

supported_motor_drivers = [
    'motorNewFocus'
]

class MotorIOCAction:


    def __init__(self, ioc_type, ioc_name):



    def process(self, ioc_top, bin_loc, bin_flat):


    
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
            configuration["PREFIX"], configuration["ENGINEER"], configuration["HOSTNAME"], 
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
        port = input('What port should the IOC use? (ex. P0). > ')
        controller_port = input('What should the controller port be? (ex. M0) > ')
        mc_number = input('What should the motion controller number be? (ex. MC:37) > ')
        ct_prefix = input('What should the controller prefix be? (ex. XF:10IDC-CT) > ')
        ioc_port = input('What telnet port should procServer use to run the IOC? > ')
        connection = input('Enter the connection param for your device. (ex. IP, serial number etc.) enter NA if not sure. > ')
        ioc_action = MotorIOCAction(driver_type, ioc_name, port, controller_port, mc_number, ct_prefix, ioc_port, connection)
        execute_ioc_action(ioc_action, configuration, bin_flat)
        another = input('Would you like to generate another IOC? (y/n). > ')
        if another != 'y':
            another_ioc = False
    initIOC_print('Done.')


guided_init()