"""
Malocher is a lightweight python library for running jobs on a cluster where nodes are accessed
via SSH and share a common network storage like traditional NFS or mountable cloud storage.

Author: Lukas Pfahler
Repo:   https://github.com/Whadup/malocher
"""
import sys
import os
import pickle
from queue import Queue, Empty
from threading import Thread
from functools import partial
from glob import glob
import cloudpickle
from .ssh import async_ssh

def submit(
    fun,
    *args,
    malocher_dir=".jobs",
    **kwargs
):
    if not os.path.exists(malocher_dir):
        print(f"make dir {malocher_dir}")
        os.mkdir(malocher_dir)

    job = ""
    existing_exp = [d.split(os.sep)[-2] for d in glob(malocher_dir+'/*/')]
    # Only consider integer experiment ids
    existing_int_exp = []
    for e in existing_exp:
        try:
            existing_int_exp.append(int(e))
        except ValueError:
            continue

    # Add one to the largest experiment number
    job = os.path.abspath(os.path.join(malocher_dir, str(max(existing_int_exp + [0,]) + 1)))
    os.mkdir(job)
    open(os.path.join(job, "globals.bin"), "wb").write(cloudpickle.dumps(globals()))
    # open(os.path.join(job, "locals.bin"), "wb").write(cloudpickle.dumps(locals()))
    open(os.path.join(job, "args.bin"), "wb").write(cloudpickle.dumps(args))
    open(os.path.join(job, "kwargs.bin"), "wb").write(cloudpickle.dumps(kwargs))
    open(os.path.join(job, "fun.bin"), "wb").write(cloudpickle.dumps(fun))
    return job



def process_all(malocher_dir=".jobs", ssh_machines=[], ssh_username="pfahler", ssh_port=22, ssh_private_key="/home/pfahler/.ssh/id_rsa"):
    """
    Runs all jobs in the `malocher_dir` and yields their return values.

    Parameters
    ----------
    malocher_dir : list of str
        The shared folder used for storing jobs and results
    ssh_machines : list of str
        List of Hostnames to run the jobs on. Can be either hostnames or IP-addresses. Must accept ssh connections with private key authorization.
    ssh_username : str or list of str
        The username for logging onto the `ssh_machines`. If a single user is provided as `str`, this user is used for all `ssh_machines`. Alternatively you can provide a list of str of the same length as `ssh_machines`.
    ssh_port : int or list of int
        The port the ssh server listens on. Provide either a single port for all machines or a list of ports, one for each machine.
    ssh_private_key: str or list of str:
        Path to the ssh key needed to log onto the `ssh_machines`. Provide either a single private key file or one for each machine.

    Yields
    -------
    job_id: str
        The job identifier for the finished job
    result: obj
        The return value of the job
    
    Warnings
    --------
    The results are not necessarily returned in the same order they were submitted. Rely on the `job_id` that is returned to match submitted jobs with finished jobs.
    """
    # repeat usernames, ports and keys if they are not provided as a list
    if not isinstance(ssh_username, list):
        ssh_username = [ssh_username for _ in ssh_machines]
    if not isinstance(ssh_port, list):
        ssh_port = [ssh_port for _ in ssh_machines]
    if not isinstance(ssh_private_key, list):
        ssh_private_key = [ssh_private_key for _ in ssh_machines]

    available_machines = Queue()
    remaining_jobs = Queue()
    results = Queue()

    def _ssh_call(args, machine=None, job=None):
        #put back machine after the ssh call and recover results
        result = async_ssh(args)
        available_machines.put(machine)
        if result == 0:
            with open(os.path.join(job, "return.bin"), "rb") as f:
                result = pickle.load(f)
                results.put((job, result))
        else:
            with open(os.path.join(job, "DONE"), "w") as f:
                f.write("ERROR")

    for m in zip(ssh_machines, ssh_username, ssh_port, ssh_private_key):
        available_machines.put(m)
    for job in os.listdir(malocher_dir):
        if not os.path.exists(os.path.join(malocher_dir, job, "DONE")):
            remaining_jobs.put(os.path.abspath(os.path.join(malocher_dir, job)))
    
    threads = []

    while not remaining_jobs.empty():
        job = remaining_jobs.get(block=True)
        machine = available_machines.get(block=True)
        ssh_address, ssh_username, ssh_port, ssh_private_key = machine
        cmd_dict = {'cmd': f"{sys.executable} -m malocher {job}",
                    'address': ssh_address,
                    'ssh_username': ssh_username, 
                    'ssh_port': ssh_port,
                    'ssh_private_key': ssh_private_key}
        thread = Thread(target=partial(_ssh_call, machine=machine, job=job), args=[cmd_dict])
        thread.daemon = True
        thread.start()
        threads.append(thread)
        
        try:
            result = results.get(block=False)
            yield result
        except Empty:
            pass
    # TODO: Timeout once in a while to yield new results.
    for thread in threads:
        thread.join()
    yield from iter(list(results.queue))

def work(job):
    globals().update(pickle.load(open(os.path.join(job, "globals.bin"), "rb")))
    # locals().update(pickle.load(open(os.path.join(job, "locals.bin"), "rb")))
    args = pickle.load(open(os.path.join(job, "args.bin"), "rb"))
    kwargs = pickle.load(open(os.path.join(job, "kwargs.bin"), "rb"))
    fun = pickle.load(open(os.path.join(job, "fun.bin"),"rb"))
    ret = fun(*args, **kwargs)
    open(os.path.join(job, "return.bin"), "wb").write(cloudpickle.dumps(ret))
    with open(os.path.join(job, "DONE"), "w") as f:
        f.write("DONE")
