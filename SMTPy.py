#!/usr/bin/python2.7
#*************************************************************************
#
# SMTPy version 0.0.1
#
# Copyright (c) 2017 Jonathan Gregson  <jdgregson@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope  that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#*************************************************************************


import sys
import os
import socket
import logging
import threading
import Queue
import mimetypes as types
from subprocess import Popen
from subprocess import PIPE
from subprocess import STDOUT
from includes import const
from includes import daemon


# Change this to whatever it is in your tests.
# TODO: This should be changed to /etc/something
# before httpy is released
CONFIG_FILE = "/mnt/c/Users/Jonathan/Google Drive/Projects/SMTPy/SMTPy.conf"


class SMTPyDaemon(daemon.Daemon):
    """
    Overrides the Daemon class's default run method.
    This tells the daemon to start main() after it
    is daemonized.
    """
    def run(self):
        while True:
            main()


def load_configuration():
    """
    Loads the configuration file. The file's path
    is set using the "CONFIG_FILE" variable.
    """

    try:
        conf_file = open(CONFIG_FILE, "r")
    except IOError as (errno, strerr):
        print "Could not load config file at '%s': %s" % (CONFIG_FILE, strerr)
        sys.exit(1)
    config = conf_file.read()
    exec(config)
    return


# TODO: Currently does not respect the LOG_MAX_SIZE
#  config setting. It simply appends always.
def log(message, message_type=None):
    """
    logs messages to the console and the log file.
    The first argument is the message to be logged.
    The second is the log entry type, and is not
    required. Valid types are 'info', 'error',
    'warning', and 'debug.' If no value is supplied,
    or the value supplied is not defined, it defaults
    to 'debug.'
    """

    print message
    if const.USE_TEXT_LOG:
        logger = logging.getLogger('SMTPy')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr = logging.FileHandler(const.LOG_LOCATION)
        hdlr.setFormatter(formatter)
        logger.setLevel(logging.INFO)
        logger.addHandler(hdlr)
        if message_type is "info":
            logger.info(message)
        elif message_type is "error":
            logger.error(message)
        elif message_type is "warning":
            logger.warning(message)
        elif message_type is "debug":
            logger.debug(message)
        else:
            logger.debug(message)
        logger.removeHandler(hdlr)
    return


def main():
    load_configuration()
    log("%s, starting..." % const.SERVER_INFO, "info")


if __name__ == "__main__":
    daemon = SMTPyDaemon('/tmp/SMTPy-daemon.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif '--no-daemon' == sys.argv[1]:
            main()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "Usage: %s start|stop|restart\n" % sys.argv[0]
        print "    --no-daemon  Stay in the foreground. For debugging.\n"
        sys.exit(2)
