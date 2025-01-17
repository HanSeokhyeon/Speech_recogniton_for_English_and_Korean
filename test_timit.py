import yaml
from util.timit_dataset import load_dataset, create_dataloader
from model.las_model import LAS, Listener, Speller
from util.functions import test
import torch
from tensorboardX import SummaryWriter
import argparse
from logger import *
import numpy as np
import pickle

# Load config file for experiment
parser = argparse.ArgumentParser(description='Training script for LAS on TIMIT .')
parser.add_argument('config_path', metavar='config_path', type=str, help='Path to config file for training.')
paras = parser.parse_args()
config_path = paras.config_path
conf = yaml.load(open(config_path, 'r'))
device = 'cuda'
if not torch.cuda.is_available():
    conf['model_parameter']['use_gpu'] = False
    device = 'cpu'

# Parameters loading
torch.manual_seed(conf['training_parameter']['seed'])
torch.cuda.manual_seed_all(conf['training_parameter']['seed'])
total_epochs = conf['training_parameter']['total_epochs']
use_pretrained = conf['training_parameter']['use_pretrained']
valid_step = conf['training_parameter']['valid_step']
tf_rate_upperbound = conf['training_parameter']['tf_rate_upperbound']
tf_rate_lowerbound = conf['training_parameter']['tf_rate_lowerbound']

# Construct LAS Model or load pretrained LAS model
log_writer = SummaryWriter(conf['meta_variable']['training_log_dir']+conf['meta_variable']['experiment_name'])

if not use_pretrained:
    listener = Listener(**conf['model_parameter'])
    speller = Speller(**conf['model_parameter'])
else:
    listener = torch.load(conf['training_parameter']['pretrained_listener_path'])
    speller = torch.load(conf['training_parameter']['pretrained_speller_path'])

model = LAS(listener, speller)
# model = nn.DataParallel(model)
model.to(device)

model_path = "{}{}.pt".format(conf['meta_variable']['checkpoint_dir'], "las_timit_mel56")
# save checkpoint with the best ler
global_step = 0

n_repeats = 5

model.load_state_dict(torch.load(model_path))
model.eval()


def shuffle_feature(x, idx):
    x_all = np.concatenate(x, axis=0)
    x_all[:, idx] = np.random.permutation(x_all[:, idx])
    # x_all[:, idx*2] = np.random.permutation(x_all[:, idx*2])
    # x_all[:, idx*3] = np.random.permutation(x_all[:, idx*3])
    x_result, start, end = [], 0, 0
    for x_tmp in x:
        end = end+x_tmp.shape[0]
        x_result.append(x_all[start:end, :])
        start = end
    return x_result


# Load preprocessed TIMIT Dataset ( using testing set directly here, replace them with validation set your self)
# X : Padding to shape [num of sample, max_timestep, feature_dim]
# Y : Squeeze repeated label and apply one-hot encoding (preserve 0 for <sos> and 1 for <eos>)
_, _, _, _, X_test, y_test = load_dataset(**conf['meta_variable'])
test_set = create_dataloader(X_test, y_test, **conf['model_parameter'], **conf['training_parameter'], shuffle=False)
max_cer, _ = test(test_set, model, conf, global_step, log_writer, logger, -1, mode='phonetic')

exit()

result = [[max_cer]]
for feature in range(conf['model_parameter']['input_feature_dim']//3):
    now_pi = []
    for i in range(n_repeats):
        X_test_shuffled = shuffle_feature(X_test, feature)

        test_set = create_dataloader(X_test_shuffled, y_test, **conf['model_parameter'], **conf['training_parameter'], shuffle=False)
        now_cer = test(test_set, model, conf, global_step, log_writer, logger, feature)
        now_pi.append(now_cer)
    result.append(now_pi)

logger.info("\n".join(map(str, result)))

with open('pfi_mel40_mfcc16_5.pkl', 'wb') as f:
    pickle.dump(result, f)
