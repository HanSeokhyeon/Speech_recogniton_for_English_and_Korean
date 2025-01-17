"""
그림 6. 멜-스펙트로그램, MFCC 기반 다중 특성(위)과 멜-스펙트로그램, 스파이크그램 기반 다중 특성(아래)의 상관관계 분석
"""

from util.timit_dataset import load_dataset
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 20
fig = plt.figure(figsize=(8, 11))  # (8, 11)
plt.rcParams['xtick.bottom'] = plt.rcParams['xtick.labelbottom'] = False
plt.rcParams['xtick.top'] = plt.rcParams['xtick.labeltop'] = True

# Load preprocessed TIMIT Dataset ( using testing set directly here, replace them with validation set your self)
# X : Padding to shape [num of sample, max_timestep, feature_dim]
# Y : Squeeze repeated label and apply one-hot encoding (preserve 0 for <sos> and 1 for <eos>)
X_train, _, _, _, _, _ = load_dataset(data_path='../dataset/TIMIT/timit_mel_mfcc_168.pkl')

X = np.concatenate(X_train, axis=0)[:, :56]  # mel40, g8 t8
dfx = pd.DataFrame(X, columns=range(56))  # 판다스 데이터프레임
corr = dfx.corr().abs()  # correlation
# corr = corr.iloc[::-1]

ticks = [20, 48]
tickslabel = ["$Mel_{0...39}$", "$MFCC_{0...15}$"]

# mask = np.zeros_like(corr)
# for i in range(80):
#     mask[i, :-(i+1)] = True

plt.subplot(2, 1, 1)

ax = sns.heatmap(corr, annot=False, cmap='binary', xticklabels=True, yticklabels=True, vmin=0, vmax=1)
ax.set_xticks(ticks)
ax.set_yticks(ticks)
ax.set_xticklabels(tickslabel)
ax.set_yticklabels(tickslabel)

plt.xticks(rotation=0)

for h in [0, 40, 56]:
    plt.axhline(h, color='black', alpha=0.3)
    plt.axvline(h, color='black', alpha=0.3)

# Load preprocessed TIMIT Dataset ( using testing set directly here, replace them with validation set your self)
# X : Padding to shape [num of sample, max_timestep, feature_dim]
# Y : Squeeze repeated label and apply one-hot encoding (preserve 0 for <sos> and 1 for <eos>)
X_train, _, _, _, _, _ = load_dataset(data_path='../dataset/TIMIT/timit_mel_spikegram_168.pkl')

X = np.concatenate(X_train, axis=0)[:, :56]
dfx = pd.DataFrame(X, columns=range(56))
corr = dfx.corr().abs()
# corr = corr.iloc[::-1]

ticks = [20, 44, 52]
tickslabel = ["$Mel_{0...39}$", "$G_{0...7}$", "$T_{0...7}$"]

# mask = np.zeros_like(corr)
# for i in range(80):
#     mask[i, :-(i+1)] = True

plt.subplot(2, 1, 2)

ax = sns.heatmap(corr, annot=False, cmap='binary', xticklabels=True, yticklabels=True, vmin=0, vmax=1)
ax.set_xticks(ticks)
ax.set_yticks(ticks)
ax.set_xticklabels(tickslabel)
ax.set_yticklabels(tickslabel)

plt.xticks(rotation=0)

for h in [0, 40, 48, 56]:
    plt.axhline(h, color='black', alpha=0.3)
for v in [0, 40, 48, 56]:
    plt.axvline(v, color='black', alpha=0.3)

fig1 = plt.gcf()
plt.show()

fig1.savefig("figures/figure6.png")
