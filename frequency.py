import json
import os
# from wordfreq import zipf_frequency

# # with open(os.path.join(os.path.dirname(__file__), 'answers', 'allowed_words.txt'), 'r') as f:
# #     ALLOWED_WORDS = [line.strip() for line in f.readlines()]

# # target_freq = {}
# # for word in ALLOWED_WORDS:
# #     freq = zipf_frequency(word, 'en')
# #     target_freq[word] = freq

# # with open(os.path.join(os.path.dirname(__file__), 'answers', 'word_frequencies.json'), 'w', newline='') as f:
# #     json.dump(target_freq, f, indent=4)

with open(os.path.join(os.path.dirname(__file__), 'answers', 'word_frequencies.json'), 'r') as f:
    data = json.load(f)

data = list(data.values())

print(data)

import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Setup your data (Example: a slightly right-skewed distribution)
# Replace this with your actual list: data = [1, 5, 2, ...]
np.random.seed(42)

# Convert to a Pandas Series for easier handling
series = pd.Series(data)

# --- PART 1: NUMERICAL SUMMARIES ---
print("### 1. Central Tendency & Dispersion ###")
# .describe() gives count, mean, std, min, 25%, 50% (median), 75%, max
print(series.describe()) 
print(f"Mode: {series.mode()[0]:.2f}") # Mode needs special handling
print("-" * 30)

# --- PART 2: SHAPE ANALYSIS ---
print("### 2. Shape Metrics ###")
# Skewness: 0 is symmetric. >0 is right-skewed. <0 is left-skewed.
skew = series.skew()
# Kurtosis: 0 is normal (Fisher's definition). >0 is heavy tails.
kurt = series.kurtosis() 

print(f"Skewness: {skew:.4f} ({'Right/Positive' if skew > 0 else 'Left/Negative'} skew)")
print(f"Kurtosis: {kurt:.4f} ({'Heavy tails' if kurt > 0 else 'Light tails'})")
print("-" * 30)

# --- PART 3: NORMALITY TEST ---
print("### 3. Normality Test (Shapiro-Wilk) ###")
# Note: Shapiro-Wilk is most accurate for N < 5000.
stat, p_value = stats.shapiro(series)
print(f"Statistic: {stat:.4f}, p-value: {p_value:.4g}")

alpha = 0.05
if p_value > alpha:
    print("Result: Data looks Gaussian (fail to reject H0)")
else:
    print("Result: Data does NOT look Gaussian (reject H0)")

# --- PART 4: VISUALIZATION ---
plt.figure(figsize=(12, 5))

# Plot 1: Histogram with Kernel Density Estimate (KDE)
plt.subplot(1, 2, 1)
sns.histplot(series, kde=True, color='skyblue')
plt.title('Distribution (Histogram + KDE)')
plt.xlabel('Value')
plt.axvline(series.mean(), color='red', linestyle='--', label='Mean')
plt.axvline(series.median(), color='green', linestyle='-', label='Median')
plt.legend()

# Plot 2: Q-Q Plot (Quantile-Quantile)
plt.subplot(1, 2, 2)
stats.probplot(series, dist="norm", plot=plt)
plt.title('Q-Q Plot (Normality Check)')

plt.tight_layout()
plt.show()