import collections
import json
import os
import time
import pickle
import game
import random
import heapq  # For Priority Queue (UCS)

# --- 1. GLOBAL RESOURCES ---
ALLOWED_MAP = {}
ANSWER_MAP = {}
MATRIX = []
ALLOWED_WORDS = []
ANSWER_WORDS = []
WORD_FREQ = {}
SORTED_GUESS_INDICES = [] # Optimization: Indices sorted by frequency

def load_resources():
    global MATRIX, ALLOWED_WORDS, ANSWER_WORDS, ALLOWED_MAP, ANSWER_MAP, WORD_FREQ, SORTED_GUESS_INDICES
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    matrix_path = os.path.join(base_path, "pattern_matrix.json")
    freq_path = os.path.join(base_path, "answers", "word_frequencies.json")
    
    print(f"Loading resources...")
    
    # 1. Load Matrix
    if os.path.exists(matrix_path):
        with open(matrix_path, "r") as f:
            data = json.load(f)
        MATRIX = data["matrix"]
        ALLOWED_WORDS = data["allowed_words"]
        ANSWER_WORDS = data["answer_words"]
    else:
        print("Error: pattern_matrix.json not found.")
        return

    # 2. Load Frequencies
    if os.path.exists(freq_path):
        with open(freq_path, "r") as f:
            WORD_FREQ = json.load(f)
    else:
        print("Warning: word_frequencies.json not found. Defaulting to 0.")
        WORD_FREQ = {}

    ALLOWED_MAP = {w: i for i, w in enumerate(ALLOWED_WORDS)}
    ANSWER_MAP = {w: i for i, w in enumerate(ANSWER_WORDS)}
    
    # 3. Create Optimized Search Order (High Freq -> Low Freq)
    # This allows us to break early in the search loop once we find a minimal partition,
    # guaranteeing we picked the most common word for that partition size.
    indices_with_freq = []
    for i, w in enumerate(ALLOWED_WORDS):
        f = WORD_FREQ.get(w, 0.0)
        indices_with_freq.append((i, f))
    
    # Sort by frequency descending
    indices_with_freq.sort(key=lambda x: x[1], reverse=True)
    SORTED_GUESS_INDICES = [x[0] for x in indices_with_freq]

    print("Resources loaded and optimized.")

load_resources()

# --- 2. HELPER: FREQUENCY-AWARE SELECTION ---
def find_best_move_for_state(current_indices, depth):
    """
    Calculates the best move using a strategy that favors common words.
    """
    if not current_indices:
        return None, {}

    best_idx = -1
    min_worst = float('inf')
    best_groups = {}

    # Determine which words to search
    if depth == 5:
        # Last guess: must pick from the remaining candidates
        # We sort these local candidates by frequency on the fly
        search_indices = [ALLOWED_MAP[ANSWER_WORDS[i]] for i in current_indices]
        search_indices.sort(key=lambda idx: WORD_FREQ.get(ALLOWED_WORDS[idx], 0.0), reverse=True)
    else:
        # Normal guess: use the global pre-sorted list (High Freq -> Low Freq)
        search_indices = SORTED_GUESS_INDICES

    for guess_idx in search_indices:
        groups = collections.defaultdict(list)
        
        # Partition the current candidates based on patterns this guess would reveal
        for ans_idx in current_indices:
            pat_int = MATRIX[guess_idx][ans_idx]
            groups[pat_int].append(ans_idx)
        
        worst = 0
        if groups:
            worst = max(len(g) for g in groups.values())

        # UCS / Cost Logic:
        # We process words in order of highest frequency. 
        # Therefore, the first time we see a partition size 'worst', 
        # it is guaranteed to be the most common word achieving that size.
        if worst < min_worst:
            min_worst = worst
            best_idx = guess_idx
            best_groups = groups
            
            # Optimization: If we found a bucket size of 1 (perfect split),
            # we can stop immediately. Since we sort by frequency, this is 
            # the most common word that gives a perfect split.
            if min_worst == 1: 
                break
            
    if best_idx != -1:
        return ALLOWED_WORDS[best_idx], best_groups
    
    if current_indices:
        return ANSWER_WORDS[current_indices[0]], {}
        
    return None, {}

# --- 3. UCS STATE SOLVER (Priority Queue) ---
def ucs_solve_by_state(start_word: str = None, initial_candidates: list[str] = None):
    """
    Generates a strategy tree using Uniform Cost Search.
    Priority is determined by depth (standard UCS) but node selection 
    heavily favors common words.
    """
    # Priority Queue stores tuples: (cost, state_id_hash, indices, depth)
    # Using hash/id as tiebreaker for stability
    pq = [] 
    strategy_map = {}
    visited_states = set()
    
    # Initialize candidates
    if initial_candidates:
        initial_indices = []
        for w in initial_candidates:
            if w in ANSWER_MAP:
                initial_indices.append(ANSWER_MAP[w])
    else:
        initial_indices = list(range(len(ANSWER_WORDS)))
    
    # Push initial state
    if start_word:
        start_idx = ALLOWED_MAP[start_word]
        initial_tuple = tuple(initial_indices)
        strategy_map[initial_tuple] = start_word
        visited_states.add(initial_tuple)
        
        # Partition immediately for the start word
        groups = collections.defaultdict(list)
        for ans_idx in initial_indices:
            pat_int = MATRIX[start_idx][ans_idx]
            groups[pat_int].append(ans_idx)
            
        for subset in groups.values():
            if len(subset) > 0:
                # Cost = depth (Uniform Cost)
                heapq.heappush(pq, (1, id(subset), subset, 1))
    else:
        heapq.heappush(pq, (0, id(initial_indices), initial_indices, 0))

    start_time = time.time()
    nodes_processed = 0

    print(f"Starting UCS for {len(initial_indices)} candidates...")

    while pq:
        # Pop state with lowest cost (depth)
        cost, _, current_indices, depth = heapq.heappop(pq)
        state_id = tuple(current_indices)

        if state_id in visited_states and not start_word: 
            continue
        visited_states.add(state_id)

        # Leaf node (Solved)
        if len(current_indices) == 1:
            strategy_map[state_id] = ANSWER_WORDS[current_indices[0]]
            continue
        
        if depth >= 6: continue

        # Find best move favoring frequency
        best_word, best_groups = find_best_move_for_state(current_indices, depth)
        
        if best_word:
            strategy_map[state_id] = best_word
            for pat_int, subset in best_groups.items():
                if pat_int == 242: continue # All Green pattern (solved)
                
                # Add children to Priority Queue
                # Cost is uniform (depth + 1)
                new_cost = depth + 1
                heapq.heappush(pq, (new_cost, id(subset), subset, new_cost))
            
        nodes_processed += 1
        if nodes_processed % 100 == 0:
            print(f"Processed: {nodes_processed} | PQ Size: {len(pq)} | Time: {time.time()-start_time:.1f}s")

    return strategy_map

# --- 4. RUNTIME HELPER ---
def use_strategy_map(game_state, strategy_map):
    game_progress = game_state["progress"]
    game_responses = game_state["response"]
    game_finished = game_state["is_game_over"]

    # 1. Start Game
    if len(game_responses) == 0:
        # Pick a high frequency starter like 'stare' or 'salet' dynamically
        # or calculate specifically. For speed, we calculate one live.
        if not strategy_map:
            print("Generating initial strategy...")
            # We seed with 'salet' or similar to save time, or let UCS pick (slower)
            # Let's let UCS pick the very best frequency-weighted opener
            strategy_map.update(ucs_solve_by_state(start_word="crane")) 
        return strategy_map.get(max(strategy_map.keys(), key=len))

    if game_finished:
        return None

    # 2. Filter Candidates
    current_indices = list(range(len(ANSWER_WORDS)))
    for guess, resp_list in zip(game_progress, game_responses):
        if not guess or guess not in ALLOWED_MAP: continue
        guess_idx = ALLOWED_MAP[guess]
        
        target_val = 0
        for j, digit in enumerate(resp_list):
            target_val += digit * (3 ** (4 - j))
            
        current_indices = [
            idx for idx in current_indices 
            if MATRIX[guess_idx][idx] == target_val
        ]
    
    if not current_indices: return None

    # 3. Lookup or Regenerate
    state_id = tuple(current_indices)
    if state_id in strategy_map:
        return strategy_map[state_id]
    
    print(f"Off-script state ({len(current_indices)} candidates). Recovering with UCS...")
    strategy_map.update(ucs_solve_by_state(initial_candidates=[ANSWER_WORDS[i] for i in current_indices]))
    
    return strategy_map.get(state_id)

if __name__ == "__main__":
    strategy = {}
    g = game.Game()

    
    success = 0
    fail = 0
    totalmoves = 0
    
    # Test on a few games
    for i in range(len(ANSWER_WORDS)): 
        print(f"--- UCS Test Game {i+1} ---")
        g.new_game(ANSWER_WORDS[i])
        while True:
            state = g.response
            next_word = use_strategy_map(state, strategy)
            if next_word is None: break
            
            print(f"Guess: {next_word}")
            res = g.add_guess(next_word)
            
            state = g.response
            print(f"Response: {res}")
            print(f"Progress: {state['progress']}")
            print(f"Responses: {state['response']}")            

            if state["is_game_over"]:
                if res == "Win":
                    success += 1
                    totalmoves += len(state['response'])
                    print(f"Won in {len(state['response'])} moves.")
                else:
                    fail += 1
                    print("Lost.")
                break
    
    print(f"UCS Solver Results: {success} Wins, {fail} Losses, Average Moves: {totalmoves/success if success > 0 else 0:.2f}")