# Malocher

> "*Malocher*" [maˈloːxɐ] is a German colloquialism from the Ruhr-Area for "worker", particularly used for miners and steel workers.

Malocher is a lightweight python library for running jobs on a cluster where nodes are accessed via SSH and share a common network storage like traditional NFS or mountable cloud storage. We

- use SSH and `paramiko` for communication between workers,
- rely on`dill` for serializing code and data and
- assume that all python libraries and interpreters are available on all nodes, like when they're also in the NFS.

This way we do not need to use large cluster computing libraries, e.g. from the Apache universe.

## Getting started

### Installation

Simplest way is to use pip

```bash
pip install git+https://github.com/Whadup/malocher
```

### Setting up the malocher-workers

This one's easy: 

- Make sure you can access each malocher node from the supervising node using the same SSH key `ssh_private_key`.
- Make sure each malocher-worker, including the supervisor, has access to a shared directory `malocher_dir`
- Make sure every malocher-worker, including the supervisor, has the same python environment, e.g. put it into a shared directory.

BTW, we chose the terminology worker/supervisor, because [words matter](https://thenewstack.io/words-matter-finally-tech-looks-at-removing-exclusionary-language/).

### Sample

```python
import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import malocher


def fake_experiment(model, data_path=None):
    train = pd.read_csv(os.path.join(data_path, "train.csv"))
    y_train = train["class"]
    X_train = train.drop(columns="class")
    test = pd.read_csv(os.path.join(data_path, "test.csv"))
    y_test = train["class"]
    X_test = train.drop(columns="class")
    model.fit(X_train, y_train)
    return dict(accuracy = model.score(X_test, y_test))

if __name__ == "__main__":
    print("running")
    CONFIGS = {}
    for D in range(1,10):
        MODEL = RandomForestClassifier(max_depth=D)
        # Store our Configuration under the Job's ID
        CONFIGS[malocher.submit(fake_experiment, MODEL, data_path="/home/share/datensaetze/pamono")] = D
    RESULTS = malocher.process_all(
        ssh_machines=["ls8ws020", "ls8ws021", "ls8ws022", "ls8ws023", "ls8ws024", "ls8ws025"],
        ssh_port=22,
        ssh_username="dummy",
        ssh_private_key="malocher_id_rsa"
    )
    # Retrieve the config by the result's ID
    for JOB, RESULT in RESULTS:
        print(CONFIGS[JOB], RESULT)
```

## Software-Cosmos
Malocher is used in [Experiment Runner](https://github.com/sbuschjaeger/experiment_runner) to execute experiments on a number of machines.
For experiment tracking, we advice the use of [meticulous](https://github.com/AshwinParanjape/meticulous-ml/).
