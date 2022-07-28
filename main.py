import os, pickle, warnings, logging, socket, getopt, sys, re
from models.TimeWindow import TimeWindow
from models.Topic import Topic
from gensim.models import Word2Vec
from read_dataset import speeches_from_json
import pandas as pd
from preprocess import preprocess_df
from models.CoherenceModel import Word2VecCoherenceModel, CvCoherenceModel
from optparse import OptionParser
from nmf import choose_topics
import numpy as np
from sklearn.preprocessing import normalize

OUT_PATH = "out"
DATA_PATH = "data"
DATASET_PATH = "dataset/parliament"

logging.basicConfig(
    format="%(asctime)s - %(funcName)s - %(message)s", 
    level=logging.INFO,
    handlers=[
        logging.FileHandler(f"out/{socket.gethostname()}.log"),
        logging.StreamHandler()
    ]
)

def clear_dir(path):
    for f in os.listdir(path):
        fp = f"{path}/{f}"
        os.remove(fp)

def fit_window_topics(min_k=10, max_k=25):
    logger = logging.getLogger(__name__)

    clear_dir(OUT_PATH)

    # 1. Read time windows
    time_windows = [TimeWindow.load(DATA_PATH+"/"+f) for f in os.listdir("data") if f.endswith(".pkl") and not f.startswith("vocab")]
    # 2. Read coherence_model.model 
    if os.path.exists(DATA_PATH+"/w2v.model"):
        logger.info("using Word2VecCoherenceModel")
        coherence_model = Word2VecCoherenceModel.load(DATA_PATH+"/w2v.model")
    elif os.path.exists(DATA_PATH+"/cv.model"):
        logger.info("using CvCoherenceModel")
        coherence_model = CvCoherenceModel.load(DATA_PATH+"/cv.model")
    else:
        raise RuntimeError("Coherence model NOT found!")
    # 3. Read vocab
    with open(DATA_PATH+'/vocab.pkl', 'rb') as f:
        vocab = pickle.load(f)
    # 4. Fit window topics
    for time_window in time_windows:
        time_window.fit(coherence_model, min_k, max_k)

    clear_dir(DATA_PATH)

def preprocess(parl_num):
    logger = logging.getLogger(__name__)

    path = f"{DATASET_PATH}/{parl_num}"
    records = [speech for f in os.listdir(path) if f.lower().endswith(".json") 
                      for speech in speeches_from_json(f"{path}/{f}")]
    with open(f"{DATASET_PATH}/mp.txt") as f:
        members = [re.sub(r"[^a-z. ]", "", line.replace("\n","").lower().strip()) for line in f.readlines() if line.strip()]
    df = pd.DataFrame.from_records(records)
    df['date'] = pd.to_datetime(df['date'])
    df_members = pd.DataFrame(members, columns=["name"])
    df_members = df_members.drop_duplicates(["name"]).reset_index(drop=True)
    df = preprocess_df(df, df_members['name'].values)
    df.to_csv(f"{OUT_PATH}/parliament_{parl_num}.csv")
    logger.info(f"Data frame: {df.shape}")

def main():
    parser = OptionParser(usage="usage: %prog [options]")
    parser.add_option("-f", "--fit", action="store_true", dest="run_fit", help="fit window topics")
    parser.add_option("-k", "--num-topics", action="store", type="string", dest="num_topics", help="range of number of topics, comma separated", default="10,25")
    parser.add_option("-p", "--preprocess", action="store_true", dest="run_preprocess", help="preprocess data")
    parser.add_option("-n", "--parlnum", action="store", type=int, dest="parl_num", help="number of available virtual machines", default=1)
    (options, args) = parser.parse_args()
    if options.run_fit == None and options.run_preprocess == None:
        parser.error("Must specify either -f or -p to dataset")

    if options.run_fit:
        min_k, max_k = list(map(int, options.num_topics.split(",")))
        fit_window_topics(min_k, max_k)
    elif options.run_preprocess:
        logging.basicConfig(
            format="%(asctime)s - %(funcName)s - %(message)s", 
            level=logging.INFO,
            handlers=[
                logging.FileHandler(f"out/{socket.gethostname()}_preprocess.log"),
                logging.StreamHandler()
            ]
        )
        preprocess(options.parl_num)
    

if __name__ == "__main__":
    main()