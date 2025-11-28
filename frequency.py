import json
import os
from wordfreq import zipf_frequency

with open(os.path.join(os.path.dirname(__file__), 'answers', 'allowed_words.txt'), 'r') as f:
    ALLOWED_WORDS = [line.strip() for line in f.readlines()]

target_freq = {}
for word in ALLOWED_WORDS:
    freq = zipf_frequency(word, 'en')
    target_freq[word] = freq

with open(os.path.join(os.path.dirname(__file__), 'answers', 'word_frequencies.json'), 'w', newline='') as f:
    json.dump(target_freq, f, indent=4)