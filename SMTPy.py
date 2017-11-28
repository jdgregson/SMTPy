#!/usr/bin/python2.7
#*******************************************************************************
#
# SMTPy version 0.0.1
#
# Copyright (c) 2017 Jonathan Gregson  <jdgregson@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope  that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#*******************************************************************************


import sys
import os
import socket
import logging
import threading
import Queue
import re
import mimetypes as types
from subprocess import Popen
from subprocess import PIPE
from subprocess import STDOUT
from includes import const
from includes import daemon


# Change this to whatever it is in your tests.
# TODO: This should be changed to /etc/something before SMTPy is released
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


class ClientHandler(threading.Thread):
    """
    An instance of this class will take a client from the queue, have an SMTP
    conversation with the client, put the client's email on the send queue,
    close the connection, and then get another client from the queue.
    """

    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # grab a client from the queue
            client, address = self.queue.get()
            #client.settimeout(0.1)
            client.settimeout(100)
            # client communication loop
            FROM_HOST = ''
            MAIL_FROM = ''
            RECEIVING_DATA = False
            RCPT_TO = []
            DATA = []
            HEADERS = []
            FROM_HEADER_SET = False
            client.send('220 example.com ESMTP %s\r\n' % const.HOSTNAME)
            while True:
                try:
                    message = client.recv(1024)
                except:
                    log("The connection to %s timed out"
                         % address[0], "info")
                    message = None
                # HELO
                # EHLO
                if bool(re.search('^HELO', message)) or bool(re.search('^EHLO',
                    message)):
                    if not FROM_HOST:
                        FROM_HOST = message.split()[1]
                        client.send('250 Nice to meet you, %s\r\n' % FROM_HOST)
                # MAIL FROM
                elif bool(re.search('^MAIL FROM', message)):
                    MAIL_FROM = message.split(':')[1]
                    client.send('250 Ok\r\n')
                # RCPT TO
                elif bool(re.search('^RCPT TO', message)):
                    RCPT_TO.append(message.split(':')[1])
                    client.send('250 Ok\r\n')
                # SIZE
                elif bool(re.search('^SIZE', message)):
                    client.send('504 NOT IMPLEMENTED\r\n')
                # VRFY
                elif bool(re.search('^VRFY', message)):
                    client.send('504 NOT IMPLEMENTED\r\n')
                # TURN
                elif bool(re.search('^TURN', message)):
                    client.send('504 NOT IMPLEMENTED\r\n')
                # AUTH
                elif bool(re.search('^AUTH', message)):
                    client.send('504 NOT IMPLEMENTED\r\n')
                # RSET
                elif bool(re.search('^RSET', message)):
                    client.send('504 NOT IMPLEMENTED\r\n')
                # EXPN
                elif bool(re.search('^EXPN', message)):
                    client.send('504 NOT IMPLEMENTED\r\n')
                # HELP
                elif bool(re.search('^HELP', message)):
                    client.send('504 NOT IMPLEMENTED\r\n')
                # QUIT
                elif bool(re.search('^QUIT', message)):
                    client.send('221 Bye\r\n')
                    log(''.join(DATA))
                    break
                # DATA
                elif bool(re.search('^DATA', message)):
                    client.send('354 End data with <CR><LF>.<CR><LF>\r\n')
                    RECEIVING_DATA = True
                # .
                elif RECEIVING_DATA and (bool(re.search('^\.', message))
                  or bool(re.search('\r\n\.\r\n', message))):
                    RECEIVING_DATA = False
                    client.send('250 Ok: message queued as %i\r\n' % 462456345)
                # MESSAGE BODY
                elif RECEIVING_DATA:
                    DATA.append(message)
                # ANYTHING ELSE
                else:
                    client.send('504 NOT IMPLEMENTED\r\n')
            client.close()

            # tell queue that the client has been served
            self.queue.task_done()


def main():
    load_configuration()
    log("%s, starting..." % const.SERVER_INFO, "info")
    # create queue for threading
    queue = Queue.Queue()
    for i in range(const.THREADS):
        handler = ClientHandler(queue)
        handler.setDaemon(True)
        handler.start()
    # open socket, bind port, and listen
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((const.LISTEN_IP_ADDRESS, const.SERVER_PORT))
        log("Listening on port %s\n" % str(const.SERVER_PORT), "info")
    except socket.error as (errno, strerr):
        log("Could not bind port %s: %s. Exiting..." % (const.SERVER_PORT,
                                                        strerr), "error")
        sys.exit(1)
    else:
        sock.listen(5)
        while True:
            client, address = sock.accept()
            log("accepted connection from %s" % str(address), "info")
            # place the client in the queue
            queue.put((client, address))
    finally:
        sock.close()


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
            print "Unknown argument"
            sys.exit(2)
        sys.exit(0)
    else:
        print "Usage: %s start|stop|restart\n" % sys.argv[0]
        print "    --no-daemon  Stay in the foreground. For debugging.\n"
        sys.exit(2)
