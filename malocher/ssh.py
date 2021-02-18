#stolen from dask.distributed
from __future__ import print_function, division, absolute_import

import logging
import socket
import os
import sys
import time
import traceback


logger = logging.getLogger(__name__)



def async_ssh(cmd_dict):
    import paramiko
    from paramiko.buffered_pipe import PipeTimeout
    from paramiko.ssh_exception import (SSHException, PasswordRequiredException)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    retries = 0
    while True:  # Be robust to transient SSH failures.
        try:
            # Set paramiko logging to WARN or higher to squelch INFO messages.
            logging.getLogger('paramiko').setLevel(logging.WARN)

            ssh.connect(hostname=cmd_dict['address'],
                        username=cmd_dict['ssh_username'],
                        port=cmd_dict['ssh_port'],
                        key_filename=cmd_dict['ssh_private_key'],
                        compress=True,
                        timeout=20,
                        banner_timeout=20)  # Helps prevent timeouts when many concurrent ssh connections are opened.
            # Connection successful, break out of while loop
            break

        except (SSHException,
                PasswordRequiredException) as e:

            print(f"SSH connection error when connecting to {cmd_dict['address']}:{cmd_dict['ssh_port']}", file=sys.stderr)

            # Print an exception traceback
            traceback.print_exc()

            # Transient SSH errors can occur when many SSH connections are
            # simultaneously opened to the same server. This makes a few
            # attempts to retry.
            retries += 1
            if retries >= 3:
                print("SSH connection failed after 3 retries. Exiting.", file=sys.stderr)

                # Connection failed after multiple attempts.  Terminate this thread.
                os._exit(1)

            # Wait a moment before retrying
            print("Retrying... (attempt {retires}/3)'.format(n=retries, total=3)", file=sys.stderr)

            time.sleep(1)

    # Execute the command, and grab file handles for stdout and stderr. Note
    # that we run the command using the user's default shell, but force it to
    # run in an interactive login shell, which hopefully ensures that all of the
    # user's normal environment variables (via the dot files) have been loaded
    # before the command is run. This should help to ensure that important
    # aspects of the environment like PATH and PYTHONPATH are configured.

    # print('[ {label} ] : {cmd}'.format(label=cmd_dict['label'],
    #                                    cmd=cmd_dict['cmd']))
    # print('$SHELL -i -c \'' + cmd_dict['cmd'] + '\'')
    stdin, stdout, stderr = ssh.exec_command('$SHELL -i -c \'' + cmd_dict['cmd'] + '\'', get_pty=True)

    # Set up channel timeout (which we rely on below to make readline() non-blocking)
    channel = stdout.channel
    channel.settimeout(0.1)

    def read_from_stdout():
        """
        Read stdout stream, time out if necessary.
        """
        try:
            line = stdout.readline()
            while len(line) > 0:    # Loops until a timeout exception occurs
                line = line.rstrip()
                print(line)
                line = stdout.readline()
        except (PipeTimeout, socket.timeout):
            pass

    def read_from_stderr():
        """
        Read stderr stream, time out if necessary.
        """
        try:
            line = stderr.readline()
            while len(line) > 0:
                line = line.rstrip()
                print(line, file=sys.stderr)
                line = stderr.readline()
        except (PipeTimeout, socket.timeout):
            pass

    def communicate():
        """
        Communicate a little bit, without blocking too long.
        Return True if the command ended.
        """
        read_from_stdout()
        read_from_stderr()

        # Check to see if the process has exited. If it has, we let this thread
        # terminate.
        if channel.exit_status_ready():
            exit_status = channel.recv_exit_status()
            # cmd_dict['output_queue'].put('[ {label} ] : '.format(label=cmd_dict['label']) +
            #                              bcolors.FAIL +
            #                              "remote process exited with exit status " +
            #                              str(exit_status) + bcolors.ENDC)
            return True
        return False

    # Wait for a message on the input_queue. Any message received signals this
    # thread to shut itself down.
    while not communicate():
        # Kill some time so that this thread does not hog the CPU.
        time.sleep(1.0)

    # Shutdown the channel, and close the SSH connection
    channel.close()
    ssh.close()