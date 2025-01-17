import torch
import torch.nn as nn
from torch.autograd import Variable  
import numpy as np
import editdistance as ed
import time


def create_onehot_variable(input_x, encoding_dim=63):
    # CreateOnehotVariable function
    # *** DEV NOTE : This is a workaround to achieve one, I'm not sure how this function affects the training speed ***
    # This is a function to generate an one-hot encoded tensor with given batch size and index
    # Input : input_x which is a Tensor or Variable with shape [batch size, timesteps]
    #         encoding_dim, the number of classes of input
    # Output: onehot_x, a Variable containing onehot vector with shape [batch size, timesteps, encoding_dim]
    if type(input_x) is Variable:
        input_x = input_x.data
    input_type = type(input_x)
    batch_size = input_x.size(0)
    time_steps = input_x.size(1)
    input_x = input_x.unsqueeze(2).type(torch.LongTensor)
    onehot_x = Variable(torch.LongTensor(batch_size, time_steps, encoding_dim).zero_().scatter_(-1, input_x, 1)).type(
        input_type)

    return onehot_x


def time_distributed(input_module, input_x):
    # TimeDistributed function
    # This is a pytorch version of TimeDistributed layer in Keras I wrote
    # The goal is to apply same module on each timestep of every instance
    # Input : module to be applied timestep-wise (e.g. nn.Linear)
    #         3D input (sequencial) with shape [batch size, timestep, feature]
    # output: Processed output      with shape [batch size, timestep, output feature dim of input module]
    batch_size = input_x.size(0)
    time_steps = input_x.size(1)
    reshaped_x = input_x.contiguous().view(-1, input_x.size(-1))
    output_x = input_module(reshaped_x)
    return output_x.view(batch_size, time_steps, -1)


def letter_error_rate(pred_y, true_y, data):
    # letter_error_rate function
    # Merge the repeated prediction and calculate edit distance of prediction and ground truth
    ed_accumalate = []
    for p, t in zip(pred_y, true_y):
        compressed_t = [w for w in t if (w != 1 and w != 0)]
        
        compressed_p = []
        for p_w in p:
            if p_w == 0:
                continue
            if p_w == 1:
                break
            compressed_p.append(p_w)
        if data == 'timit':
            compressed_t = collapse_phn(compressed_t)
            compressed_p = collapse_phn(compressed_p)
        ed_accumalate.append(ed.eval(compressed_p, compressed_t)/len(compressed_t))
    return ed_accumalate


def letter_error_rate_by_phonetic_class(pred_y, true_y, data):
    def get_class(idx):
        reduce_idx2broad_class_idx = {2: 0, 4: 0, 6: 0, 8: 0, 10: 0, 12: 0, 14: 0,  # Stops      b, d, g, p, t, k, dx, q
                                      16: 1, 17: 1,  # Affricate  jh, ch
                                      18: 2, 19: 2, 20: 2, 22: 2, 23: 2, 24: 2, 25: 2,  # Fricative  s, sh, z, zh, f, th, v, dh
                                      33: 3, 34: 3, 35: 3, 36: 3, 37: 3,  # Glides     l, r, w, y, hh, hv, el
                                      26: 4, 27: 4, 28: 4,  # Nasals     m, n, ng, em, en, eng, nx
                                      40: 5, 41: 5, 42: 5, 43: 5, 44: 5, 45: 5, 46: 5, 47: 5, 48: 5, 50: 5, 51: 5, 52: 5, 53: 5, 55: 5,  # Vowels     iy, ih, eh, ey, ae, aa, aw, ay, ah, ao, oy, ow, uh, uw, ux, er, ax, ix, axr, ax-h
                                      62: 6}  # Others     pau, epi, h#
        return reduce_idx2broad_class_idx[idx]

    # letter_error_rate function
    # Merge the repeated prediction and calculate edit distance of prediction and ground truth
    ed_accumalate, ed_accumalate_by_class = [], []
    for p, t in zip(pred_y, true_y):
        compressed_t = [w for w in t if (w != 1 and w != 0)]

        compressed_p = []
        for p_w in p:
            if p_w == 0:
                continue
            if p_w == 1:
                break
            compressed_p.append(p_w)
        if data == 'timit':
            compressed_t = collapse_phn(compressed_t)
            compressed_p = collapse_phn(compressed_p)

        ed_accumalate.append(ed.eval(compressed_p, compressed_t) / len(compressed_t))

        compressed_t_by_class = [[] for _ in range(7)]
        compressed_p_by_class = [[] for _ in range(7)]

        for ta in compressed_t:
            compressed_t_by_class[get_class(ta)].append(ta)
        for pr in compressed_p:
            compressed_p_by_class[get_class(pr)].append(pr)

        by_class = []
        for ct, cp in zip(compressed_t_by_class, compressed_p_by_class):
            if not ct:
                by_class.append(0)
            else:
                by_class.append(ed.eval(cp, ct) / len(ct))
        ed_accumalate_by_class.append(by_class)
    return ed_accumalate, ed_accumalate_by_class


def label_smoothing_loss(pred_y, true_y, label_smoothing=0.1):
    # Self defined loss for label smoothing
    # pred_y is log-scaled and true_y is one-hot format padded with all zero vector
    assert pred_y.size() == true_y.size()
    seq_len = torch.sum(torch.sum(true_y, dim=-1), dim=-1, keepdim=True)
    
    # calculate smoothen label, last term ensures padding vector remains all zero
    class_dim = true_y.size()[-1]
    smooth_y = ((1.0-label_smoothing)*true_y+(label_smoothing/class_dim))*torch.sum(true_y, dim=-1, keepdim=True)

    loss = - torch.mean(torch.sum((torch.sum(smooth_y * pred_y, dim=-1)/seq_len), dim=-1))

    return loss


def train(train_set, model, optimizer, tf_rate, conf, global_step, log_writer, data='timit'):
    bucketing = conf['model_parameter']['bucketing']
    use_gpu = conf['model_parameter']['use_gpu']
    label_smoothing = conf['model_parameter']['label_smoothing']

    verbose_step = conf['training_parameter']['verbose_step']

    model.train()

    # Training
    for batch_index, (batch_data, batch_label) in enumerate(train_set):
        if bucketing:
            batch_data = batch_data.squeeze(dim=0)
            batch_label = batch_data.squeeze(dim=0)
        max_label_len = min([batch_label.size()[1], conf['model_parameter']['max_label_len']])

        batch_data = Variable(batch_data).type(torch.FloatTensor)
        batch_label = Variable(batch_label, requires_grad=False)
        criterion = nn.NLLLoss(ignore_index=0)
        if use_gpu:
            batch_data = batch_data.cuda()
            batch_label = batch_label.cuda()
            criterion = criterion.cuda()

        optimizer.zero_grad()

        raw_pred_seq = model(batch_data, batch_label, tf_rate, batch_label)

        pred_y = (torch.cat([torch.unsqueeze(each_y, 1) for each_y in raw_pred_seq], 1)[:, :max_label_len, :])\
            .contiguous()

        if label_smoothing == 0.0:
            pred_y = pred_y.permute(0, 2, 1)  # pred_y.contiguous().view(-1,output_class_dim)
            true_y = torch.max(batch_label, dim=2)[1][:, :max_label_len].contiguous()  # .view(-1)

            loss = criterion(pred_y, true_y)
            # variable -> numpy before sending into LER calculator
            batch_ler = letter_error_rate(torch.max(pred_y.permute(0, 2, 1), dim=2)[1].cpu().numpy(),
                                          # .reshape(current_batch_size,max_label_len),
                                          true_y.cpu().data.numpy(),
                                          data)  # .reshape(current_batch_size,max_label_len), data)

        else:
            true_y = batch_label[:, :max_label_len, :].contiguous()
            true_y = true_y.type(torch.cuda.FloatTensor) if use_gpu else true_y.type(torch.FloatTensor)
            loss = label_smoothing_loss(pred_y, true_y, label_smoothing=label_smoothing)
            batch_ler = letter_error_rate(torch.max(pred_y, dim=2)[1].cpu().numpy(),
                                          # .reshape(current_batch_size,max_label_len),
                                          torch.max(true_y, dim=2)[1].cpu().data.numpy(),
                                          data)  # .reshape(current_batch_size,max_label_len), data)

        loss.backward()
        optimizer.step()

        batch_loss = loss.cpu().data.numpy()

        global_step += 1

        if global_step % verbose_step == 0:
            log_writer.add_scalars('loss', {'train': batch_loss}, global_step)
            log_writer.add_scalars('cer', {'train': np.array([np.array(batch_ler).mean()])}, global_step)

    return global_step


def evaluate(evaluate_set, model, conf, global_step, log_writer, epoch_begin, train_begin,
             logger, epoch, data='timit'):
    bucketing = conf['model_parameter']['bucketing']
    use_gpu = conf['model_parameter']['use_gpu']

    model.eval()

    # Validation
    eval_loss = []
    eval_ler = []

    with torch.no_grad():
        for _, (batch_data, batch_label) in enumerate(evaluate_set):
            if bucketing:
                batch_data = batch_data.squeeze(dim=0)
                batch_label = batch_data.squeeze(dim=0)
            max_label_len = min([batch_label.size()[1], conf['model_parameter']['max_label_len']])

            batch_data = Variable(batch_data).type(torch.FloatTensor)
            batch_label = Variable(batch_label, requires_grad=False)
            criterion = nn.NLLLoss(ignore_index=0)
            if use_gpu:
                batch_data = batch_data.cuda()
                batch_label = batch_label.cuda()
                criterion = criterion.cuda()

            raw_pred_seq = model(batch_data, batch_label, 0, None)

            pred_y = (torch.cat([torch.unsqueeze(each_y, 1) for each_y in raw_pred_seq], 1)[:, :max_label_len, :])\
                .contiguous()

            pred_y = pred_y.permute(0, 2, 1)  # pred_y.contiguous().view(-1,output_class_dim)
            true_y = torch.max(batch_label, dim=2)[1][:, :max_label_len].contiguous()  # .view(-1)

            loss = criterion(pred_y, true_y)
            # variable -> numpy before sending into LER calculator
            batch_ler = letter_error_rate(torch.max(pred_y.permute(0, 2, 1), dim=2)[1].cpu().numpy(),
                                          # .reshape(current_batch_size,max_label_len),
                                          true_y.cpu().data.numpy(),
                                          data)  # .reshape(current_batch_size,max_label_len), data)

            batch_loss = loss.cpu().data.numpy()

            eval_loss.append(batch_loss)
            eval_ler.extend(batch_ler)

    now_loss, now_cer = np.array([sum(eval_loss) / len(eval_loss)]), np.mean(eval_ler)
    log_writer.add_scalars('loss', {'dev': now_loss}, global_step)
    log_writer.add_scalars('cer', {'dev': now_cer}, global_step)

    current = time.time()
    epoch_elapsed = (current - epoch_begin) / 60.0
    train_elapsed = (current - train_begin) / 3600.0

    logger.info("epoch: {}, global step: {:6d}, loss: {:.4f}, cer: {:.4f}, elapsed: {:.2f}m {:.2f}h"
                .format(epoch, global_step, float(now_loss), float(now_cer), epoch_elapsed, train_elapsed))

    return now_cer


def test(evaluate_set, model, conf, global_step, log_writer, logger, epoch, data='timit', mode='normal'):
    bucketing = conf['model_parameter']['bucketing']
    use_gpu = conf['model_parameter']['use_gpu']

    model.eval()

    # Validation
    eval_loss = []
    eval_ler = []
    eval_cers = []

    with torch.no_grad():
        for _, (batch_data, batch_label) in enumerate(evaluate_set):
            if bucketing:
                batch_data = batch_data.squeeze(dim=0)
                batch_label = batch_data.squeeze(dim=0)
            max_label_len = min([batch_label.size()[1], conf['model_parameter']['max_label_len']])

            batch_data = Variable(batch_data).type(torch.FloatTensor)
            batch_label = Variable(batch_label, requires_grad=False)
            criterion = nn.NLLLoss(ignore_index=0)
            if use_gpu:
                batch_data = batch_data.cuda()
                batch_label = batch_label.cuda()
                criterion = criterion.cuda()

            raw_pred_seq = model(batch_data, batch_label, 0, None)

            pred_y = (torch.cat([torch.unsqueeze(each_y, 1) for each_y in raw_pred_seq], 1)[:, :max_label_len, :])\
                .contiguous()

            pred_y = pred_y.permute(0, 2, 1)  # pred_y.contiguous().view(-1,output_class_dim)
            true_y = torch.max(batch_label, dim=2)[1][:, :max_label_len].contiguous()  # .view(-1)

            loss = criterion(pred_y, true_y)

            if mode == 'normal':
                # variable -> numpy before sending into LER calculator
                batch_ler = letter_error_rate(torch.max(pred_y.permute(0, 2, 1), dim=2)[1].cpu().numpy(),
                                              # .reshape(current_batch_size,max_label_len),
                                              true_y.cpu().data.numpy(),
                                              data)  # .reshape(current_batch_size,max_label_len), data)
            elif mode == 'phonetic':
                batch_ler, batch_cers = letter_error_rate_by_phonetic_class(torch.max(pred_y.permute(0, 2, 1), dim=2)[1].cpu().numpy(),
                                              # .reshape(current_batch_size,max_label_len),
                                              true_y.cpu().data.numpy(),
                                              data)  # .reshape(current_batch_size,max_label_len), data)
                eval_cers.extend(batch_cers)
            batch_loss = loss.cpu().data.numpy()

            eval_loss.append(batch_loss)
            eval_ler.extend(batch_ler)

    now_loss, now_cer = np.array([sum(eval_loss) / len(eval_loss)]), np.mean(eval_ler)
    log_writer.add_scalars('loss', {'test': now_loss}, global_step)
    log_writer.add_scalars('cer', {'test': now_cer}, global_step)

    logger.info("test epoch: {}, cer: {:.6f}".format(epoch, float(now_cer)))
    if mode == 'normal':
        return now_cer
    elif mode == 'phonetic':
        now_cers = np.mean(np.array(eval_cers), axis=0)
        logger.info(" ".join(map(str, now_cers)))
        return now_cer, now_cers


def log_parser(log_file_path):
    tr_loss, tt_loss, tr_ler, tt_ler = [], [], [], []
    with open(log_file_path, 'r') as log_f:
        for line in log_f:
            tmp = line.split('_')
            tr_loss.append(float(tmp[3]))
            tr_ler.append(float(tmp[5]))
            tt_loss.append(float(tmp[7]))
            tt_ler.append(float(tmp[9]))

    return tr_loss, tt_loss, tr_ler, tt_ler


def collapse_phn(seq, return_phn = False, drop_q = True):
    # Collapse 61 phns to 39 phns
    # http://cdn.intechopen.com/pdfs/15948/InTech-Phoneme_recognition_on_the_timit_database.pdf
    phonemes = ["b", "bcl", "d", "dcl", "g", "gcl", "p", "pcl", "t", "tcl",
                "k", "kcl", "dx", "q", "jh", "ch", "s", "sh", "z", "zh",
                "f", "th", "v", "dh", "m", "n", "ng", "em", "en", "eng",
                "nx", "l", "r", "w", "y", "hh", "hv", "el", "iy", "ih",
                "eh", "ey", "ae", "aa", "aw", "ay", "ah", "ao", "oy", "ow",
                "uh", "uw", "ux", "er", "ax", "ix", "axr", "ax-h", "pau", "epi", "h#"]

    phonemes2index = {k: (v+2) for v, k in enumerate(phonemes)}
    index2phonemes = {(v+2): k for v, k in enumerate(phonemes)}

    phoneme_reduce_mapping = {"b": "b", "bcl": "h#", "d": "d", "dcl": "h#", "g": "g",
                               "gcl": "h#", "p": "p", "pcl": "h#", "t": "t", "tcl": "h#",
                               "k": "k", "kcl": "h#", "dx": "dx", "q": "q", "jh": "jh",
                               "ch": "ch", "s": "s", "sh": "sh", "z": "z", "zh": "sh",
                               "f": "f", "th": "th", "v": "v", "dh": "dh", "m": "m",
                               "n": "n", "ng": "ng", "em": "m", "en": "n", "eng": "ng",
                               "nx": "n", "l": "l", "r": "r", "w": "w", "y": "y",
                               "hh": "hh", "hv": "hh", "el": "l", "iy": "iy", "ih": "ih",
                               "eh": "eh", "ey": "ey", "ae": "ae", "aa": "aa", "aw": "aw",
                               "ay": "ay", "ah": "ah", "ao": "aa", "oy": "oy", "ow": "ow",
                               "uh": "uh", "uw": "uw", "ux": "uw", "er": "er", "ax": "ah",
                               "ix": "ih", "axr": "er", "ax-h": "ah", "pau": "h#", "epi": "h#",
                               "h#": "h#"}

    # inverse index into phn
    seq = [index2phonemes[idx] for idx in seq]
    # collapse phn
    seq = [phoneme_reduce_mapping[phn] for phn in seq]
    # Discard phn q
    if drop_q:
        seq = [phn for phn in seq if phn != "q"]
    else:
        seq = [phn if phn != "q" else ' ' for phn in seq]
    if return_phn:
        return seq

    # Transfer back into index sequence for Evaluation
    seq = [phonemes2index[phn] for phn in seq]

    return seq
