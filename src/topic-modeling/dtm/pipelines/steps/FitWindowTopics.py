from time import sleep
from sklearn.base import BaseEstimator, TransformerMixin
import os, subprocess, logging
import threading
from models.TimeWindow import TimeWindow

class FitWindowTopics(BaseEstimator, TransformerMixin):
    N_MACHINES = 1
    PRIVATE_KEY = "ssh/sgparl_private.ppk"

    def __init__(self):
        #self.machines = [f"machine{str(machine).zfill(2)}" for machine in range(1, self.N_MACHINES+1)]
        self.machines = [
            "35.230.145.133", #01
        ]

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        w2v, vocab, time_windows = X

        self.run_machine(self.setup)
        self.upload_data()
        self.run_machine(self.fit_windows)
        self.download_data()
        time_windows = self.concat()        
        return w2v, vocab, time_windows

    def run_machine(self, target):
        threads = []
        for host in self.machines:
            t = threading.Thread(target=target, args=(host,))
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()

    def setup(self, host):
        logger = logging.getLogger(__name__)
        logger.info(f"{host} setup ...")
        commands = [
            "rm -rf cloud",
            "git clone -b cloud --single-branch https://github.com/ktkhuong/sgparl.git cloud",
            "sudo chmod 777 cloud/data",
        ]
        batch = ";".join(commands)
        p = subprocess.Popen(f'plink -i {self.PRIVATE_KEY} -batch sgparl@{host} "{batch}"', creationflags=subprocess.CREATE_NEW_CONSOLE)
        p.wait()
        
    def fit_windows(self, host):
        commands = [
            "cd cloud",
            "python3 -m venv env",
            "source env/bin/activate",
            "pip install -r requirements.txt",
            "python3 main.py",
        ]
        batch = ";".join(commands)
        p = subprocess.Popen(f'plink -i {self.PRIVATE_KEY} -batch sgparl@{host} "{batch}"', creationflags=subprocess.CREATE_NEW_CONSOLE)
        p.wait()

    def upload_data(self):
        logger = logging.getLogger(__name__)

        years = set([f[:4] for f in os.listdir("out") if f.find("Q") != -1])
        machine = 1
        for year in years:
            logger.info(f"machine{str(machine).zfill(2)}: {year}")
            p = subprocess.Popen(f"gcloud compute scp --recurse out/{year}*.pkl machine{str(machine).zfill(2)}:/home/sgparl/cloud/data", shell=True)
            p.wait()
            machine += 1
            # load balancing: round-robin
            if machine > self.N_MACHINES:
                machine = 1
        
        for _ in range(1, self.N_MACHINES+1):
            p = subprocess.Popen(f"gcloud compute scp --recurse out/w2v.model machine{str(machine).zfill(2)}:/home/sgparl/cloud/data", shell=True)
            p.wait()
            p = subprocess.Popen(f"gcloud compute scp --recurse out/vocab.pkl machine{str(machine).zfill(2)}:/home/sgparl/cloud/data", shell=True)
            p.wait()

    def download_data(self):
        for i in range(1, self.N_MACHINES+1):
            p = subprocess.Popen(f"gcloud compute scp --recurse machine{str(i).zfill(2)}:/home/sgparl/cloud/out/* in", shell=True)
            p.wait()

    def concat(self):
        paths = ["in/"+f for f in os.listdir("in") if f.endswith(".pkl")]
        time_windows = [TimeWindow.load(path) for path in paths]
        return time_windows
