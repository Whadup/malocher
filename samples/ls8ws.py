import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import malocher


def fake_experiment(model, data_path=None):
    print(model)
    train = pd.read_csv(os.path.join(data_path, "train.csv"))
    y_train = train["class"]
    X_train = train.drop(columns="class")
    test = pd.read_csv(os.path.join(data_path, "test.csv"))
    y_test = train["class"]
    X_test = train.drop(columns="class")
    model.fit(X_train, y_train)
    if np.random.uniform() < 0.25:
        raise RuntimeError("oups")
    return dict(accuracy = model.score(X_test, y_test))

if __name__ == "__main__":
    print("running")
    CONFIGS = {}
    for D in range(1,10):
        MODEL = RandomForestClassifier(max_depth=D)
        # Store our Configuration under the Job's ID
        CONFIGS[malocher.submit(fake_experiment, MODEL, data_path="/home/share/datensaetze/pamono")] = D
    RESULTS = malocher.process_all(ssh_machines=["ls8ws020", "ls8ws021", "ls8ws022", "ls8ws023", "ls8ws024", "ls8ws025"])
    # print(configs)
    # Retrieve the config by the result's ID
    for JOB, RESULT in RESULTS:
        print(CONFIGS[JOB], RESULT)