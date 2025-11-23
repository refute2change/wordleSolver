import os

path = os.path.dirname(os.path.abspath(__file__))

with open(path + "\\answers\\allowed_words.txt", "r", encoding="utf-8") as f:
    legal_words = [line.strip() for line in f if line.strip()]

with open(path + "\\answers\\answers.txt", "r", encoding="utf-8") as f:
    answer_words = [line.strip() for line in f if line.strip()]

print("Words in answers.txt that are NOT in allowed_words.txt:")
for word in answer_words:
    if word not in legal_words:
        print(word)