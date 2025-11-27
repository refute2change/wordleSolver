from typing import List
from time import perf_counter
import os
import csv
import json
import wordHandle

# test.py

cnt = 0
longest_path = []
words = []
final_words = []
hsh = ""
data = []
ma = 0

# GLOBAL MAPS for O(1) Index Lookup
ALLOWED_MAP = {}
ANSWER_MAP = {}
MATRIX = []

def load_resources():
    """
    Loads Matrix and Word Lists from the JSON to ensure indices match perfectly.
    """
    global MATRIX, words, final_words, ALLOWED_MAP, ANSWER_MAP
    
    first_path = os.path.dirname(os.path.abspath(__file__))
    # Assuming the file is named 'pattern_matrix.json' based on generate_matrix.py
    # Checking for your filename 'pattern_matrix' as well
    matrix_path = os.path.join(first_path, "pattern_matrix.json")
    if not os.path.exists(matrix_path):
        matrix_path = os.path.join(first_path, "pattern_matrix")
        
    print(f"Loading resources from {matrix_path}...")
    with open(matrix_path, "r") as f:
        data_json = json.load(f)
        
    MATRIX = data_json["matrix"]
    # IMPORTANT: Load lists from JSON to guarantee alignment with Matrix indices
    words = data_json["allowed_words"]
    final_words = data_json["answer_words"]
    
    # Create Maps (String -> Index)
    ALLOWED_MAP = {w: i for i, w in enumerate(words)}
    ANSWER_MAP = {w: i for i, w in enumerate(final_words)}
    print("Resources loaded successfully.")

# Load resources immediately
load_resources()

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

def max_depth(last_state, ranged_words, depth, path) -> tuple:
    """
    Return a tuple `(max_depth, best_path)` for the Wordle solver's decision tree.
    """
    global ma
    global words
    global cnt
    global longest_path
    global data
    global hsh
    # Access globals for lookup
    global ALLOWED_MAP, ANSWER_MAP, MATRIX

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
    
    # Try each word as a guess
    min_size = 30000
    ans = 0
    word_used = ""
    
    # NOTE: 'ind' map is no longer needed because Matrix gives us the mask int directly
    
    for guess in words:
        guess_idx = ALLOWED_MAP[guess] # Get Index
        
        s = []
        flag = True
        for mask in range(0, 243):
            s.append([])
            
        for target in ranged_words:
            # OPTIMIZATION: Use Matrix Lookup instead of string calculation
            target_idx = ANSWER_MAP[target]
            
            # This returns the integer mask (0-242) directly
            num = MATRIX[guess_idx][target_idx]
            
            if (len(s[num]) == min_size):
                flag = False
                break
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
        if maxd == 1:
            break 

    # Record Data
    data.append([hsh, last_state, word_used])
    hsh += word_used
    
    # Re-calculate best groups for recursion
    s = []
    for mask in range(0, 243):
        s.append([])
        
    best_guess_idx = ALLOWED_MAP[word_used]
    for target in ranged_words:
        target_idx = ANSWER_MAP[target]
        num = MATRIX[best_guess_idx][target_idx]
        s[num].append(target)

    best_path_for_node = path.copy()
    
    # Recursion
    for mask in range(0, 243):
        path.append(word_used)
        hsh += gen_string_from_mask(mask)
        if s[mask] != []:
            # 242 is the integer for "GGGGG"
            if mask == 242:
                data.append([hsh, "GGGGG", "OKAY"])
                cnt += depth
                if depth > ans:
                    ans = depth
                    # record current path
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
        
        # NOTE: words and final_words are already loaded via load_resources()
        
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
    guess = 0
    # g = game.Game()
    # g.new_game()
    while guess < 6:
        if state not in decision_tree[hsh]:
            print(f"{state} not consist in the decision tree")
            # print(f"Word we need to find is {g.get_answer()}")
        else:
            guess_word = decision_tree[hsh][state]
        # g.add_guess(guess_word)
        guess += 1
        print(f"Guess {guess}: {guess_word}")
        # response = g.response["response"]
        # state = wordHandle.response_to_str(response[-1])
        state = input("Enter the response string (e.g., BYGBB): ").strip().upper() 
        # print(f"Result state: {state}")
        hsh+=guess_word+state
        if state == "GGGGG":
            break
        # if g.stop:
            # break
    if state == "GGGGG":
        print(f"Solved in {guess}!")
    else:
        print(f"Fail to solve :(")
    