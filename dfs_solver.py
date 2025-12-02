from typing import List
from time import perf_counter
from collections import Counter
import os
import csv
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

def gen_string_from_mask(mask: int) -> str:
    str = ""
    while mask > 0:
        div = mask % 3
        if div == 0:
            str = "B" + str  # Black
        elif div == 1:
            str = "Y" + str  # Yellow 
        else:
            str = "G" + str  # Green
        mask = mask // 3
    while len(str) < 5:
        str = "B" + str
    return str

def dfs(d: int, ranged_words: List[str]) -> str:
    """
    Counts the frequency of characters at index 'd' for all words in the list
    and returns the most frequent character.
    """
    #0. Base case: stop if depth reaches 5 or no words left
    if (d==5) or (len(ranged_words) == 0):
        return ""
    
    # 1. Collect all characters at position 'd'
    # We add a check (d < len(word)) to prevent IndexError if words have different lengths
    characters_at_d = [word[d] for word in ranged_words if d < len(word)]
    
    # 2. Count the frequency of each character
    # Example: Counter({'e': 5, 'a': 2, 's': 1})
    frequency_map = Counter(characters_at_d)
    
    # Debug: Print the full counts to the console so you can see the data
    # print(f"Frequencies at index {d}: {dict(frequency_map)}")
    
    # 3. Handle empty results (e.g., if the list is empty or index is out of bounds)
    if not frequency_map:
        return ""
        
    # 4. Return the character with the highest frequency
    # most_common(1) returns a list like [('e', 5)]
    most_frequent_char = frequency_map.most_common(1)[0][0]
    next_ranged_words = []
    for word in ranged_words:
        if word[d] == most_frequent_char:
            next_ranged_words.append(word)

    return most_frequent_char+dfs(d+1, next_ranged_words)

def get_next_guess(game_state: dict) -> str:
    global words
    global final_words
    ranged_words = words.copy()
    ranged_final_words = final_words.copy()
    guesses = game_state["progress"]
    responses = game_state["response"]
    for i in range(len(guesses) - 1):
        guess = guesses[i]
        response = responses[i]
        ranged_words = [
            word for word in ranged_words
            if wordHandle.get_response(guess, word) == response
        ]
        ranged_final_words = [
            word for word in ranged_final_words
            if wordHandle.get_response(guess, word) == response
        ]
    if (len(ranged_final_words) == 1 or len(guesses) >= 6):
        return ranged_final_words[0] # only one possible final word or the guess is the last one    
    else:
        return dfs(0, ranged_words)
    
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

