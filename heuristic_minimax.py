from typing import List
from time import perf_counter
from collections import Counter
import os
import csv
import math
import json
import random
import game
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

words = []
final_words = []
words = read_wordle_words("allowed_words.txt")
final_words = read_wordle_words("answers.txt")

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
    guesses = game_state['progress']
    responses = game_state['response']

    if len(guesses) == 1:
        return "salet"  # Best known first guess 

    ranged_final_words = final_words.copy()
    print(responses)
    for i in range(len(guesses) - 1):
        guess = guesses[i]
        response = responses[i]
        ranged_final_words = [
            word for word in ranged_final_words
            if wordHandle.response_to_str(wordHandle.get_response(guess, word)) == wordHandle.response_to_str(response)
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
    result = ""
    g = game.Game()
    g.new_game()
    mem = 0
    while True:
        state = g.response
        next_guess = get_next_guess(state)
        print(f"My recommendations for next guess is {next_guess}.")
        guess = input(f"Please input your choice: ")
        res = g.add_guess(guess)
        state = g.response
        print(res)
        print(f"Progress: {state['progress']}")
        print(f"Response: {state['response']}")
        if state["is_game_over"]:
            if res == "Win":
                print("You win")
            elif res == "Lose":
                print("Noob")
            break
        import os, psutil; mem = max(mem, psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)
    print(f"Result: {result}")
    print(f"Board: {g.state.progress}")
    print(f"Colors: {g.state.response}")
    t1 = perf_counter()
    print(f"Time run: {t1-t0} seconds")
    print(f"Maximum memory used: {mem} MB")

    


