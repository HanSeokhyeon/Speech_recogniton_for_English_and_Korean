"""
그림 7. 멜-스펙트로그램, MFCC 기반 다중 특성(위)과 멜-스펙트로그램, 스파이크그램 기반 다중 특성(아래)의 PFI
"""

import pickle
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 20
fig = plt.figure(figsize=(8, 8))

###################################################

with open("pfi_mel40_mfcc16_5.pkl", "rb") as f:
    data = pickle.load(f)

max_cer, cers = data[0][0], data[1:]  # cer: (56, 5), 5번의 실험

df = pd.DataFrame(columns=['Features', 'PFI'])
for i, cer in enumerate(cers):
    pfi = []
    for j, c in enumerate(cer):
        now_pfi = (c-max_cer)/max_cer*100
        pfi.append(["f{}".format(i), now_pfi])
    pfi = pd.DataFrame(pfi, columns=['Features', 'PFI'])
    df = df.append(pfi, ignore_index=True)

plt.subplot(2, 1, 1)

# 막대그래프
sns.barplot(x='Features', y='PFI', data=df, ci=None, color='gray')

plt.xticks([20-0.5, 48-0.5], ["$Mel_{0...39}$", "$MFCC_{0...15}$"])
plt.axvline(39.5, color='black', alpha=0.7)

plt.ylim(-1.5, 6.5)

###################################################

with open("pfi_mel40_spikegram_8_8_5.pkl", "rb") as f:
    data = pickle.load(f)

max_cer, cers = data[0][0], data[1:]

df = pd.DataFrame(columns=['Features', 'PFI'])
for i, cer in enumerate(cers):
    pfi = []
    for j, c in enumerate(cer):
        now_pfi = (c-max_cer)/max_cer*100
        pfi.append(["f{}".format(i), now_pfi])
    pfi = pd.DataFrame(pfi, columns=['Features', 'PFI'])
    df = df.append(pfi, ignore_index=True)

plt.subplot(2, 1, 2)

sns.barplot(x='Features', y='PFI', data=df, ci=None, color='gray')

plt.xticks([20-0.5, 44-0.5, 52-0.5], ["$Mel_{0...39}$", "$G_{0...7}$", "$T_{0...7}$"])
plt.axvline(39.5, color='black', alpha=0.7)
plt.axvline(47.5, color='black', alpha=0.7)

plt.ylim(-1.5, 6.5)

###################################################

fig1 = plt.gcf()
plt.show()

fig1.savefig("figures/figure7.png")
