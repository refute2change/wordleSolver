import collections
import csv
import json
import os
import time
import pickle
import game
import random
# import tracemalloc
import sys
import numpy as np  # Required

# --- 1. GLOBAL RESOURCES ---
ALLOWED_MAP = {}
MATRIX = np.array([]) # Placeholder
ALLOWED_WORDS = []
ANSWER_WORDS = []

def load_resources():
    global MATRIX, ALLOWED_WORDS, ANSWER_WORDS, ALLOWED_MAP
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    matrix_path = os.path.join(base_path, "pattern_matrix.pkl")
    json_path = os.path.join(base_path, "pattern_matrix.json")
    
    print(f"Loading resources...")
    
    data = None
    if os.path.exists(matrix_path):
        print(f"Loading from pickle: {matrix_path}")
        with open(matrix_path, "rb") as f:
            data = pickle.load(f)
    elif os.path.exists(json_path):
        print(f"Loading from json: {json_path}")
        with open(json_path, "r") as f:
            data = json.load(f)

    if data:
        # Convert List-of-Lists to NumPy Uint8 Array (0-242 fits in 8 bits)
        # This reduces memory from ~800MB to ~30MB
        print("Converting Matrix to NumPy...")
        MATRIX = np.array(data["matrix"], dtype=np.uint8)
        
        ALLOWED_WORDS = data["allowed_words"]
        ANSWER_WORDS = data["answer_words"]

        ALLOWED_MAP = {w: i for i, w in enumerate(ALLOWED_WORDS)}
        
        print(f"Matrix Size: {MATRIX.nbytes / 1024 / 1024:.2f} MB")
        del data
        print("Resources loaded.")
    else:
        print("Error: pattern_matrix not found.")

load_resources()

# --- 2. HELPER: MINIMAX LOGIC (DEFERRED BUILD) ---
def find_best_move_for_state(current_indices, depth):
    """
    Calculates the single best move using Vectorized NumPy operations.
    OPTIMIZED: Uses Deferred Group Construction to avoid memory churn.
    """
    if not current_indices:
        return None, {}

    best_idx = -1
    min_worst = float('inf')
    # We NO LONGER build best_groups inside the loop
    
    # Convert candidates to numpy array once for fast indexing
    candidates_arr = np.array(current_indices)

    # Logic: If last guess (Depth 5), must pick candidate.
    if depth == 5:
        search_indices = [ALLOWED_MAP[ANSWER_WORDS[i]] for i in current_indices]
    else:
        search_indices = range(len(ALLOWED_WORDS))

    for guess_idx in search_indices:
        # 1. VECTORIZED LOOKUP
        # Get the pattern for this guess against ALL candidates instantly
        patterns = MATRIX[guess_idx, candidates_arr]
        
        # 2. VECTORIZED COUNTING
        # np.bincount is insanely fast for small integers (0-242)
        counts = np.bincount(patterns, minlength=243)
        
        # 3. MINIMAX CHECK
        worst = counts.max()

        if worst >= min_worst:
            continue

        min_worst = worst
        best_idx = guess_idx
        
        # --- OPTIMIZATION: DO NOT BUILD LISTS YET ---
        # We just remember that this index is the winner so far.
        
        if min_worst == 1: 
            break
            
    if best_idx != -1:
        # --- NOW WE BUILD THE GROUPS ---
        # We do this exactly ONCE per node.
        best_groups = collections.defaultdict(list)
        # Re-fetch patterns for the winner (cheap O(1) access)
        patterns = MATRIX[best_idx, candidates_arr]
        
        for idx, pat in zip(current_indices, patterns):
            best_groups[pat].append(idx)
            
        return ALLOWED_WORDS[best_idx], best_groups
    
    if current_indices:
        return ANSWER_WORDS[current_indices[0]], {}
        
    return None, {}

# --- 3. BFS STATE SOLVER ---
def bfs_solve_by_state(start_word: str = None, initial_candidates: list[str] = None):
    """
    Generates a strategy tree.
    """
    # tracemalloc.start()
    queue = collections.deque()
    strategy_map = {}
    visited_states = set()
    
    if initial_candidates:
        initial_indices = []
        for w in initial_candidates:
            if w in ALLOWED_MAP:
                initial_indices.append(ALLOWED_MAP[w])
    else:
        initial_indices = list(range(len(ANSWER_WORDS)))
    
    if start_word:
        start_idx = ALLOWED_MAP[start_word]
        initial_tuple = tuple(initial_indices)
        strategy_map[initial_tuple] = start_word
        visited_states.add(initial_tuple)
        
        # NumPy Optimized Splitting for Start Node
        c_arr = np.array(initial_indices)
        patterns = MATRIX[start_idx, c_arr]
        
        groups = collections.defaultdict(list)
        for idx, pat in zip(initial_indices, patterns):
            groups[pat].append(idx)
            
        for subset in groups.values():
            if len(subset) > 0:
                queue.append((subset, 1))
    else:
        queue.append((initial_indices, 0))

    start_time = time.time()
    nodes_processed = 0

    print(f"Starting BFS for {len(initial_indices)} candidates...")

    while queue:
        current_indices, depth = queue.popleft()
        state_id = tuple(current_indices)

        if state_id in visited_states: continue
        visited_states.add(state_id)

        if len(current_indices) == 1:
            strategy_map[state_id] = ANSWER_WORDS[current_indices[0]]
            continue
        
        if depth >= 6: continue

        best_word, best_groups = find_best_move_for_state(current_indices, depth)
        
        if best_word:
            strategy_map[state_id] = best_word
            for pat_int, subset in best_groups.items():
                if pat_int == 242: continue 
                queue.append((subset, depth + 1))
            
        nodes_processed += 1
        if nodes_processed % 100 == 0:
            # current_mem, peak_mem = tracemalloc.get_traced_memory()
            print(f"Processed: {nodes_processed} | Queue: {len(queue)} | Time: {time.time()-start_time:.1f}s")
        
    print(f"Processed: {nodes_processed} | Queue: {len(queue)} | Time: {time.time()-start_time:.1f}s")
    # current_mem, peak_mem = tracemalloc.get_traced_memory()
    # tracemalloc.stop()
    # print(f"Tree generation complete. Peak Memory Usage: {peak_mem / 1024 / 1024:.2f} MB")
    return strategy_map

# --- 4. RUNTIME HELPER ---
def load_strategy(filename="bfs_state_strategy.pkl"):
    base_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_path, "decision_tree", filename)
    if not os.path.exists(path): return {}
    with open(path, "rb") as f: return pickle.load(f)

def get_starting_word(strategy_map):
    if not strategy_map: return None
    initial_state_id = max(strategy_map.keys(), key=len)
    return strategy_map.get(initial_state_id)

def get_next_guess(game_state = {}, strategy_map = {}):
    """
    Runtime Lookup with Smart Recovery.
    Handles ANY off-script deviation by calculating the move live.
    """
    game_progress = game_state["progress"]
    game_responses = game_state["response"]
    game_finished = game_state["is_game_over"]

    # --- 1. HANDLE START OF GAME ---
    # (Optional logic commented out in your version, kept as is)

    if game_finished:
        return None

    # --- 2. FILTER CANDIDATES BASED ON HISTORY ---
    # Start with all indices as a numpy array
    current_indices = np.arange(len(ANSWER_WORDS))
    
    for guess, resp_list in zip(game_progress, game_responses):
        if not guess: continue
        if guess not in ALLOWED_MAP: continue
        guess_idx = ALLOWED_MAP[guess]
        
        target_val = 0
        for j, digit in enumerate(resp_list):
            target_val += digit * (3 ** (4 - j))
            
        # Vectorized Filtering
        patterns = MATRIX[guess_idx, current_indices]
        mask = (patterns == target_val)
        current_indices = current_indices[mask]
    
    # Convert back to list for compatibility
    current_indices = current_indices.tolist()
    
    if not current_indices:
        return None # Impossible state

    # --- 3. LOOKUP IN STRATEGY MAP ---
    state_id = tuple(current_indices)
    
    if state_id in strategy_map:
        return strategy_map[state_id]
    
    # --- 4. OFF-SCRIPT DETECTED (THE FIX) ---
    print(f"Off-script state detected ({len(current_indices)} candidates). Regenerating partial tree...")
    
    strategy_map.update(bfs_solve_by_state(initial_candidates=[ANSWER_WORDS[i] for i in current_indices]))
    save_strategy(strategy_map)

    # After regeneration, try lookup again
    if state_id in strategy_map:
        return strategy_map[state_id]
    
    return None

# --- 5. PERSISTENCE HELPERS ---
def save_strategy(strategy_map):
    STRATEGY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decision_tree", "bfs_strategy_map.pkl")
    os.makedirs(os.path.dirname(STRATEGY_FILE), exist_ok=True)
    with open(STRATEGY_FILE, "wb") as f:
        pickle.dump(strategy_map, f)
    print(f"Strategy map saved to {STRATEGY_FILE}. Size: {len(strategy_map)} states.")

def load_strategy():
    STRATEGY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decision_tree", "bfs_strategy_map.pkl")
    if os.path.exists(STRATEGY_FILE):
        try:
            with open(STRATEGY_FILE, "rb") as f:
                strategy = pickle.load(f)
            print(f"Loaded strategy map with {len(strategy)} states.")
            return strategy
        except Exception as e:
            print(f"Error loading strategy: {e}")
            return {}
    return {}

if __name__ == "__main__":
    # input()
    # strategy = bfs_solve_by_state(start_word="crane")
    # save_strategy(strategy)
    strategy = load_strategy()

    # input()
    # with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "answers", "answers.txt"), "r") as f:
    #     answer_list = f.read().splitlines()
    
    g = game.Game()
    # success = 0
    # fail = 0
    # totalmoves = 0
    # fails = []

    g.new_game()
    while True:
        state = g.response
        # Strategy map is mutable dict, updates happen inside use_strategy_map
        next_guess = get_next_guess(game_state=state, strategy_map=strategy)
        print(f"The bot suggests: {next_guess}.")
        if not next_guess:
            print("No valid guess found. Exiting game.")
            # fail += 1
            break
        guess = input("Enter your guess (or 'exit' to quit): ").strip().lower()
        if guess == 'exit':
            print("Exiting game.")
            break
        res = g.add_guess(guess)
        print(f"Response: {res}")
        print(f"Progress: {g.response['progress']}")
        print(f"Responses: {g.response['response']}")
        if g.response["is_game_over"]:
            if res == "Win":
                print(f"Won in {len(state['response'])} moves.")
            else:
                # fail += 1
                print(f"Lost. The answer was: {g.answer}.")
            break

    

    # for i in range(len(answer_list)):
    #     print(f"--- BFS Test Game {i+1} ---")
    #     g.new_game(answer_list[i])
    #     while True:
    #         state = g.response
    #         # Strategy map is mutable dict, updates happen inside use_strategy_map
    #         next_guess = get_next_guess(game_state=state, strategy_map=strategy)
    #         print(f"Next Guess: {next_guess}")
    #         if not next_guess:
    #             print("No valid guess found. Exiting game.")
    #             fail += 1
    #             break
    #         res = g.add_guess(next_guess)
    #         print(f"Response: {res}")
    #         print(f"Progress: {g.response['progress']}")
    #         print(f"Responses: {g.response['response']}")
    #         if res == "Win":
    #             print(f"Solved in {len(g.response['progress'])} moves!")
    #             success += 1
    #             totalmoves += len(g.response['progress'])
    #             break
    #         elif res == "Loss":
    #             fail += 1
    #             print(f"Lost.")
    #             fails.append(answer_list[i])
    #             break
    # print(f"--- BFS Solver Results ---")
    # print(f"Total Games: {len(answer_list)}")
    # print(f"Successes: {success}")
    # print(f"Failures: {fail}")
    # if success > 0:
    #     print(f"Average Moves (Successful Games): {totalmoves / success:.2f}")

    # for i in fails:
    #     print(f"--- BFS Fail Test Game ---")
    #     g.new_game(i)
    #     while True:
    #         state = g.response
    #         # Strategy map is mutable dict, updates happen inside use_strategy_map
    #         next_guess = get_next_guess(game_state=state, strategy_map=strategy)
    #         print(f"Next Guess: {next_guess}")
    #         if not next_guess:
    #             print("No valid guess found. Exiting game.")
    #             fail += 1
    #             break
    #         res = g.add_guess(next_guess)
    #         print(f"Response: {res}")
    #         print(f"Progress: {g.response['progress']}")
    #         print(f"Responses: {g.response['response']}")
    #         if res == "Win":
    #             print(f"Solved in {len(g.response['progress'])} moves!")
    #             break
    #         elif res == "Loss":
    #             print(f"Lost.")
    #             break
