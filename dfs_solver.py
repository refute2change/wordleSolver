from typing import List
from time import perf_counter
import os
import csv
import game
import wordHandle

# test.py

cnt = 0
longest_path = []
words = []
final_words = []
hsh = ""
data = []
ma = 0

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

def check_wordle_guess(guess, target):
    # 1. Convert to lists for mutability
    guess = list(guess.upper())
    target = list(target.upper())
    
    # Result array: default to Gray
    result = "BBBBB"
    
    # Frequency map of the TARGET word
    target_counts = {}
    for char in target:
        target_counts[char] = target_counts.get(char, 0) + 1
        
    # --- PASS 1: Find GREENs ---
    for i in range(5):
        if guess[i] == target[i]:
            result = result[:i] + 'G' + result[i+1:]
            target_counts[guess[i]] -= 1
            
    # --- PASS 2: Find YELLOWs ---
    for i in range(5):
        # Only check if it wasn't already marked GREEN
        if result[i] == 'B':
            letter = guess[i]
            # If the letter exists in target and we haven't used up all instances
            if target_counts.get(letter, 0) > 0:
                result = result[:i] + 'Y' + result[i+1:]
                target_counts[letter] -= 1

    return result

def max_depth(last_state, ranged_words, depth, path) -> tuple:
    """
    Return a tuple `(max_depth, best_path)` for the Wordle solver's decision tree.
    `best_path` is a list of guesses (and final solution when applicable) that
    lead to the deepest resolution discovered in `ranged_words`.
    """
    global ma
    global words
    global cnt
    global longest_path
    global data
    global hsh
    # Base case: no more words to consider
    if ranged_words == [] or len(ranged_words) == 1:
        candidate_path = path.copy()
        if len(ranged_words) == 1:
            cnt += depth
            # append final solved word for a complete path
            candidate_path.append(ranged_words[0])
            data.append([hsh, last_state, ranged_words[0]])
            hsh += ranged_words[0]+"GGGGG"
            data.append([hsh, "GGGGG", "OKAY"])
            hsh = hsh[:-10]
        # update global maximum depth + path
        if depth > ma:
            ma = depth
            longest_path = candidate_path.copy()
        return depth, candidate_path
    """
    if len(ranged_words) == 1:
        print(f"Solved! The word is {ranged_words[0]}. Path taken: {path + [ranged_words[0]]}")
        return
    if len(ranged_words) == 0:
        print("No possible words left!")
        return
    """
    # Try each word as a guess and see which gives the best depth, with minimum largest partition
    min_size = 30000
    ans = 0
    word_used = ""
    ind = {}
    for mask in range(0, 243):  # 3^5 = 243 possible feedback patterns
        str = gen_string_from_mask(mask)
        ind[str] = mask
    """
    if depth == 0:
        word_used = "serai"
    else:
    """
    for guess in words:
        s = []
        flag = True
        for mask in range(0, 243):
            s.append([])
        for target in ranged_words:
            str = wordHandle.response_to_str(wordHandle.get_response(guess, target))
            num = ind[str]
            if (len(s[num]) == min_size):
                flag = False
                break  # No need to continue, this guess is worse than the best so far
            s[num].append(target)
        if not flag:
            continue
        maxd = 0
        for lst in s:
            if len(lst) > maxd:
                maxd = len(lst)
        if maxd < min_size:
            min_size = maxd
            word_used = guess
            # print(f"New best word: {word_used} with max partition size {min_size} / total size of {len(ranged_words)} at depth {depth}")
        if maxd == 1:
            break  # Can't do better than this

    # print(f"Using word {word_used} at depth {depth}")
    data.append([hsh, last_state, word_used])
    hsh += word_used
    s = []
    for mask in range(0, 243):
        s.append([])
    for target in ranged_words:
        str = wordHandle.response_to_str(wordHandle.get_response(word_used, target))
        s[ind[str]].append(target)

    best_path_for_node = path.copy()
    for mask in range(0, 243):
        path.append(word_used)
        hsh += gen_string_from_mask(mask)
        if s[mask] != []:
            if mask == ind["GGGGG"]:
                data.append([hsh, "GGGGG", "OKAY"])
                cnt += depth
                if depth > ans:
                    ans = depth
                    # record current path (no further recursion for mask==0)
                    best_path_for_node = path.copy()
            else:
                d, child_path = max_depth(gen_string_from_mask(mask), s[mask], depth + 1, path)
                if d > ans:
                    ans = d
                    best_path_for_node = child_path.copy()
        path.pop()
        hsh = hsh[:-5]
    hsh = hsh[:-5]
    return ans, best_path_for_node
    
if __name__ == "__main__":
    first_path = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(first_path+"\\decision_tree\\dfs_decision_tree.csv", "r") as f:
            pass
    except FileNotFoundError:
        header = ["current_progress","state","next_word"]
        t0 = perf_counter()
        words = read_wordle_words("allowed_words.txt")
        final_words = read_wordle_words("answers.txt")
        # print(f"Loaded {len(words)} words.")
        # print first 10 as a quick check
        ans, best_path = max_depth("", final_words, 1, [])
        print(f"Best max depth with this strategy: {ans}")
        print(f"Longest path (returned): {best_path}")
        print(f"Longest path (global): {longest_path}")
        t1 = perf_counter()
        print(f"Time taken: {t1 - t0} seconds")
        print(f"Average depth for single-word resolutions: {cnt / len(final_words)}")
        with open(first_path + "\\decision_tree\\dfs_decision_tree.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(data)
        # print("CSV file write successfully.")
    decision_tree = {}
    with open(first_path+"\\decision_tree\\dfs_decision_tree.csv", "r") as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            current_word = row["current_progress"]
            state = row["state"]
            next_word = row["next_word"]
            if current_word not in decision_tree:
                decision_tree[current_word] = {}
            decision_tree[current_word][state] = next_word
    state = ""
    g = game.game()
    g.new_game()
    while g.guess < 6:
        if state not in decision_tree[hsh]:
            print(f"{state} not consist in the decision tree")
            print(f"Word we need to find is {g.get_answer()}")
        else:
            guess_word = decision_tree[hsh][state]
        g.add_guess(guess_word)
        g.submit_guess()
        print(f"Guess {g.guess}: {guess_word}")
        state = wordHandle.response_to_str(g.response[g.guess - 1])
        print(f"Result state: {state}")
        hsh+=guess_word+state
        if g.stop:
            break
    if state == "GGGGG":
        print(f"Solved in {g.guess}!")
    else:
        print(f"Fail to solve :(")
    

