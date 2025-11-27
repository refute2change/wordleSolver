import collections
import wordHandle
import csv
import json
import os
import time
import game
import random

# --- 1. LOAD THE MATRIX (Global) ---
print("Loading Pattern Matrix... (This takes a few seconds)")
base_path = os.path.dirname(os.path.abspath(__file__))
# Adjust this path if your json is in a different folder
matrix_path = os.path.join(base_path, "pattern_matrix.json")

if not os.path.exists(matrix_path):
    raise FileNotFoundError(f"Please run generate_matrix.py first. Could not find: {matrix_path}")

with open(matrix_path, "r") as f:
    DATA = json.load(f)

ALLOWED_WORDS = DATA["allowed_words"] # List[str]
ANSWER_WORDS = DATA["answer_words"]   # List[str]
MATRIX = DATA["matrix"]               # List[List[int]]

# Create Fast Lookup Maps (Word -> Index)
ALLOWED_MAP = {w: i for i, w in enumerate(ALLOWED_WORDS)}
ANSWER_MAP = {w: i for i, w in enumerate(ANSWER_WORDS)}

# --- 2. HELPER: Integer to String ---
def int_to_pattern_str(val: int) -> str:
    """
    Converts the compressed integer (Base 3) back to 'BGYBB' string.
    The matrix stores: 0=Grey, 1=Yellow, 2=Green
    """
    if val == 242: return "GGGGG" # Optimization for common win case
    
    s = ""
    temp = val
    for _ in range(5):
        rem = temp % 3
        if rem == 0: s = "B" + s
        elif rem == 1: s = "Y" + s
        else: s = "G" + s
        temp //= 3
    return s

# --- 3. THE OPTIMIZED SOLVER ---
def bfs_build_decision_tree_fast(start_word: str = None):
    """
    Uses BFS + Matrix Lookup to build the decision tree.
    If start_word is provided, forces that as the first move.
    """
    queue = collections.deque()
    csv_rows = []
    
    # Start with all answer indices [0, 1, 2, ... 2314]
    all_candidate_indices = list(range(len(ANSWER_WORDS)))
    
    start_time = time.time()
    nodes_solved = 0

    # --- INITIALIZATION LOGIC ---
    if start_word:
        # 1. FORCE THE START WORD
        if start_word not in ALLOWED_MAP:
            print(f"Error: '{start_word}' is not a valid guess.")
            return []
            
        print(f"Forcing start word: {start_word}")
        guess_idx = ALLOWED_MAP[start_word]
        
        # Record the forced decision
        csv_rows.append(["", "N/A", start_word])
        
        # Calculate the immediate split (Depth 0)
        groups = collections.defaultdict(list)
        
        for ans_idx in all_candidate_indices:
            # MATRIX LOOKUP (List of Lists)
            pattern_int = MATRIX[guess_idx][ans_idx]
            groups[pattern_int].append(ans_idx)
            
        # Enqueue the results as the starting points for BFS (Depth 1)
        for pattern_int, subset_indices in groups.items():
            pattern_str = int_to_pattern_str(pattern_int)
            
            if pattern_str == "GGGGG":
                # Instant win case
                final_key = start_word + "GGGGG"
                csv_rows.append([final_key, "GGGGG", "OKAY"])
                continue
            
            new_history = start_word + pattern_str
            queue.append((new_history, subset_indices, 1))
            
    else:
        # 2. STANDARD: FIND BEST OPENER
        print(f"Starting BFS to find optimal opener for {len(all_candidate_indices)} candidates...")
        queue.append(("", all_candidate_indices, 0))

    # --- MAIN BFS LOOP ---
    while queue:
        history_key, current_indices, depth = queue.popleft()

        # BASE CASE: Solved (Only 1 option left)
        if len(current_indices) == 1:
            ans_word = ANSWER_WORDS[current_indices[0]]
            csv_rows.append([history_key, "N/A", ans_word])
            csv_rows.append([history_key + ans_word + "GGGGG", "GGGGG", "OKAY"])
            continue

        if not current_indices: continue

        # DEPTH LIMIT
        if depth >= 6: continue

        # LOGIC
        best_word_idx = -1
        min_worst_case = float('inf')
        best_groups = {}

        # OPTIMIZATION: Adaptive Search Space
        # 1. If we have very few candidates (< 20), checking 12,000 words is overkill.
        #    Just check the candidates themselves (Greedy approach).
        # 2. CRITICAL: If depth == 5 (Last Guess), we MUST pick a candidate. 
        #    Information gathering is useless now. We must attempt a win.
        if depth == 5 or len(current_indices) < 20:
             # Look up the ALLOWED_INDEX for every ANSWER_INDEX we have left
             search_indices = [ALLOWED_MAP[ANSWER_WORDS[i]] for i in current_indices]
        else:
             search_indices = range(len(ALLOWED_WORDS))

        for guess_idx in search_indices:
            # Group candidates by the pattern this guess produces
            # Key = Pattern Integer (from Matrix), Value = List of Answer Indices
            groups = collections.defaultdict(list)
            
            for ans_idx in current_indices:
                # INSTANT LOOKUP (List of Lists)
                pattern_int = MATRIX[guess_idx][ans_idx]
                groups[pattern_int].append(ans_idx)
            
            # Max Group Size (Minimax)
            worst_case = 0
            if groups:
                worst_case = max(len(g) for g in groups.values())

            if worst_case < min_worst_case:
                min_worst_case = worst_case
                best_word_idx = guess_idx
                best_groups = groups
                
                # Pruning: Perfect split?
                if min_worst_case == 1:
                    break
        
        # --- RECORD RESULT ---
        # Safety check if search_indices was empty
        if best_word_idx == -1:
            continue

        best_word = ALLOWED_WORDS[best_word_idx]
        csv_rows.append([history_key, "N/A", best_word])

        nodes_solved += 1
        if nodes_solved % 100 == 0:
            elapsed = time.time() - start_time
            print(f"Solved {nodes_solved} nodes | Queue: {len(queue)} | Depth: {depth} | Time: {elapsed:.1f}s")

        # --- ENQUEUE NEXT ---
        for pattern_int, subset_indices in best_groups.items():
            pattern_str = int_to_pattern_str(pattern_int)
            
            if pattern_str == "GGGGG":
                # Win state logic
                final_key = history_key + best_word + "GGGGG"
                csv_rows.append([final_key, "GGGGG", "OKAY"])
                continue

            new_history = history_key + best_word + pattern_str
            # Add to queue with INCREASED DEPTH
            queue.append((new_history, subset_indices, depth + 1))

    return csv_rows

def load_decision_tree(csv_filename="bfs_decision_tree.csv"):
    """
    Loads the BFS CSV into a fast lookup dictionary.
    Call this ONCE at the start of your program.
    """
    tree = {}
    
    # Construct absolute path to the decision_tree folder
    # Adjust this path logic if your folder structure is different
    base_path = os.path.dirname(os.path.abspath(__file__))

    with open(base_path + "\\decision_tree\\bfs_decision_tree.csv", "r", newline="") as f:
        reader = csv.reader(f)
        # Skip header if your CSV has one
        # next(reader, None) 
        
        for row in reader:
            # Your BFS solver outputs: [history_key, state, next_word]
            # We map history_key -> next_word
            if len(row) >= 3:
                history_key = row[0]
                next_word = row[2]
                tree[history_key] = next_word
                
    return tree

def get_next_guess(game_state: dict, decision_tree: dict) -> str:
    """
    Calculates the correct history key from the game state and 
    looks it up in the decision tree.
    
    Args:
        game_state: The dict returned by game.get_data() 
                    {"progress": [...], "response": [...]}
        decision_tree: The dict returned by load_decision_tree()
        
    Returns:
        str: The best word to guess next, or None if off-track.
    """
    # 1. Extract Data
    guesses = game_state["progress"]
    responses = game_state["response"]
    
    # 2. Build the History Key
    # The key represents the path taken so far: e.g. "raiseYYBBYcratedGBBBB"
    # We must match exactly how bfs_solver.py constructs 'new_history'
    history_key = ""
    
    # We zip them because 'progress' might have an extra empty string at the end 
    # which we want to ignore. Zip stops at the shortest list (responses).
    for guess_word, response_data in zip(guesses, responses):
        # Convert the list of ints [0, 2, 0...] into string "BGB..."
        # using your existing helper
        resp_str = wordHandle.response_to_str(response_data)
        
        history_key += guess_word + resp_str
        
    # 3. Lookup
    if history_key in decision_tree:
        return decision_tree[history_key]
    else:
        # If not found, it means the player made a move that wasn't the optimal
        # move recommended by the BFS, so we stepped off the pre-calculated path.
        return None

if __name__ == "__main__":
    success = 0
    fail = 0
    word_record = {}
    with open(base_path + "\\answers\\allowed_words.txt", "r") as f:
        allowed_words = f.read().splitlines()
    
    index = random.randint(0, len(allowed_words)-1)

    to_write = []

    for start_word in allowed_words[:1000]:
    # Build the decision tree in-memory and monkey-patch the CSV loader to return it
        csv_rows = bfs_build_decision_tree_fast(start_word = start_word)  # optionally pass start_word="raise"

        _memory_tree = {}
        for row in csv_rows:
            if len(row) >= 3:
                _memory_tree[row[0]] = row[2]

        # Override the loader so subsequent calls return the in-memory tree
        def load_decision_tree(*args, **kwargs):
            return _memory_tree

        tree = load_decision_tree()
        g = game.Game()
        for word in ANSWER_WORDS:
            g.new_game(answer=word)

            while 1:
                state = g.response
                word = get_next_guess(state, tree)
                g.add_guess(word)
                state = g.response
                if state["is_game_over"]:
                    if state['response'][-1] == [2,2,2,2,2]:
                        success += 1
                    else:
                        fail += 1
                    break
        
        to_write.append(f"\nTotal Success: {success} | Total Fail: {fail}")
    
    with open("bfs_results.txt", "w+") as f:
        f.writelines(to_write)