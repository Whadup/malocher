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
    open(os.path.join(job, "locals.bin"), "wb").write(cloudpickle.dumps(locals()))
    open(os.path.join(job, "args.bin"), "wb").write(cloudpickle.dumps(args))
    open(os.path.join(job, "kwargs.bin"), "wb").write(cloudpickle.dumps(kwargs))
    open(os.path.join(job, "fun.bin"), "wb").write(cloudpickle.dumps(fun))
    return job



def process_all(machines=[], malocher_dir=".jobs", ssh_username="pfahler", ssh_port=22, ssh_private_key="/home/pfahler/.ssh/id_rsa"):
    available_machines = Queue()
    remaining_jobs = Queue()
    results = Queue()

    def _ssh_call(args, machine=None, job=None):
        #put back machine after the ssh call and recover results
        async_ssh(args)
        available_machines.put(machine)
        with open(os.path.join(job, "return.bin"), "rb") as f:
            result = pickle.load(f)
            results.put((job, result))

    for m in machines:
        available_machines.put(m)
    for job in os.listdir(malocher_dir):
        if not os.path.exists(os.path.join(malocher_dir, job, "DONE")):
            remaining_jobs.put(os.path.abspath(os.path.join(malocher_dir, job)))
    
    threads = []

    while not remaining_jobs.empty():
        job = remaining_jobs.get(block=True)
        machine = available_machines.get(block=True)
        cmd_dict = {'cmd': f"{sys.executable} -m malocher {job}",
                    'address': machine,
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
    for thread in threads:
        thread.join()
    yield from iter(list(results.queue))

def work(job):
    globals().update(pickle.load(open(os.path.join(job, "globals.bin"), "rb")))
    locals().update(pickle.load(open(os.path.join(job, "locals.bin"), "rb")))
    args = pickle.load(open(os.path.join(job, "args.bin"), "rb"))
    kwargs = pickle.load(open(os.path.join(job, "kwargs.bin"), "rb"))
    fun = pickle.load(open(os.path.join(job, "fun.bin"),"rb"))
    ret = fun(*args, **kwargs)
    open(os.path.join(job, "return.bin"), "wb").write(cloudpickle.dumps(ret))
    with open(os.path.join(job, "DONE"), "w") as f:
        f.write("DONE")
