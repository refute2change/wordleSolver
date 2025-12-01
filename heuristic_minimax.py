from typing import List
from time import perf_counter
from collections import Counter
import os
import csv
import math
import json
import random
# import game
import wordHandle

# test.py
def read_wordle_words(path: str) -> List[str]:
    """
    Read the given file and return a list where each element is one line's text (stripped).
    Empty lines are ignored.
    """
    words: List[str] = []
    first_path = os.path.dirname(os.path.abspath(__file__))
    with open(first_path + "\\answers\\" + path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                words.append(s)
    return words

longest_path = []
words = []
final_words = []
words = read_wordle_words("allowed_words.txt")
final_words = read_wordle_words("answers.txt")
hsh = ""
data = []
# pattern_matrix = {}
precompute_log = {i: math.log(i, 2) if i > 0 else 0.0 for i in range(len(final_words) + 1)}
# with open("pattern_matrix.json", "r") as f:
    # pattern_matrix = json.load(f)

def response_str_to_int(response_str: str) -> int:
    result = 0
    for i in range(5):
        if response_str[i] == 'G':
            val = 2
        elif response_str[i] == 'Y':
            val = 1
        else:
            val = 0
        result += val * (3 ** (4 - i))
    return result

def get_next_guess(game_state: dict) -> str:
    global words
    global final_words
    # global pattern_matrix
    global precompute_log
    guesses = game_state["progress"]
    responses = game_state["response"]

    if len(guesses) == 0:
        return "salet"  # Best known first guess 

    ranged_final_words = final_words.copy()
    for i in range(len(guesses)):
        guess = guesses[i]
        response = responses[i]
        ranged_final_words = [
            word for word in ranged_final_words
            if wordHandle.response_to_str(wordHandle.get_response(guess, word)) == response
        ]

    if len(ranged_final_words) == 1 or len(guesses) >= 5:
        return ranged_final_words[0]  # Only one possible final word or the guess is the last one

    best_word = ""
    total = len(ranged_final_words)
    minimax = 30000
    for word in words:
        max_bin = 0
        cnt = []
        for i in range(243):
            cnt.append(0)
        for final_word in ranged_final_words:
            resp = wordHandle.response_to_int(wordHandle.get_response(word, final_word))
            cnt[resp] += 1
            if cnt[resp] > max_bin:
                max_bin = cnt[resp]
            if cnt[resp] > minimax:
                break
        if max_bin < minimax:
            minimax = max_bin
            best_word = word

    return best_word
            
    
if __name__ == "__main__":
    first_path = os.path.dirname(os.path.abspath(__file__))
    t0 = perf_counter()
    longest_path = []
    # print(f"Loaded {len(words)} words.")
    # print first 10 as a quick check
    game_state = {
        "progress": [],
        "response": [] 
    }
    max_depth = 0
    s = 0
    cnt = 0
    # for word in final_words:
    game_state = {
        "progress": [],
        "response": []
    }
    word = random.choice(final_words)
    while (cnt < 5) and (cnt == 0 or game_state["response"][-1] != "GGGGG"):
        recommendation = get_next_guess(game_state)
        print(f"My recommendation is {recommendation}.")
        guess = input("Or you follows the best heuristic or you type your own guess and be a loser here <(\"): ").strip().lower()
        response = wordHandle.response_to_str(wordHandle.get_response(guess, word))
        game_state["progress"].append(guess)
        game_state["response"].append(response)
        print(f"Guess: {guess}, Response: {response}")
        cnt += 1
    if max_depth <  len(game_state["progress"]):
        max_depth = len(game_state["progress"])
        longest_path = game_state["progress"].copy()
    s += len(game_state["progress"])
    if (game_state["response"][-1] == "GGGGG"):
        # cnt += 1
        print(f"Solved the word {word} in {len(game_state['progress'])} guesses.")
    else:
        print(f"Failed to solve the word {word} in 6 guesses.")
    # if len(game_state["response"]) == 5 and game_state["response"][-1] != "GGGGG":
    #    print("Sorry, you've used all your guesses and you're a failed human.")
    t1 = perf_counter()
    # print(f"Time taken per word (without calculating best-first guess): {(t1 - t0)/len(final_words)} seconds")
    # print(f"Average depth for single-word resolutions: {s / len(final_words)}")
    # print(f"Maximum depth for single-word resolutions: {max_depth}")
    # print(f"Longest path: {longest_path}")
    # print(f"Number of words solved within 6 guesses: {cnt} out of {len(final_words)}, with success rate {cnt/len(final_words)*100:.2f}%")

