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
SORTED_GUESS_INDICES = [] 

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
        print("Frequencies loaded.")
    else:
        print("Warning: word_frequencies.json not found. Defaulting to 0.")
        WORD_FREQ = {}

    ALLOWED_MAP = {w: i for i, w in enumerate(ALLOWED_WORDS)}
    ANSWER_MAP = {w: i for i, w in enumerate(ANSWER_WORDS)}
    
    # 3. Create Optimized Search Order
    indices_with_freq = []
    for i, w in enumerate(ALLOWED_WORDS):
        f = WORD_FREQ.get(w, 0.0)
        indices_with_freq.append((i, f))
    
    indices_with_freq.sort(key=lambda x: x[1], reverse=True)
    SORTED_GUESS_INDICES = [x[0] for x in indices_with_freq]

    print("Resources loaded and optimized.")

load_resources()

# --- 2. COST HELPER (NEW) ---
def get_word_cost(word):
    """
    Calculates cost based on specific distribution metrics:
    Mean: 1.75, Max: 6.4, Min: 0.0
    
    Strategy: Piecewise Linear Interpolation
    - Freq 0.0 (Rare)  -> Cost 2.0 (High Penalty: counts as 2 turns)
    - Freq 1.75 (Mean) -> Cost 1.0 (Baseline: counts as 1 turn)
    - Freq 6.4 (Max)   -> Cost 0.6 (Reward: cheap info)
    """
    f = WORD_FREQ.get(word, 0.0)
    
    # Thresholds from your data
    MEAN_FREQ = 1.75
    MAX_FREQ = 6.4
    
    # Costs
    COST_RARE = 2.0
    COST_MEAN = 1.0
    COST_COMMON = 0.6

    if f <= MEAN_FREQ:
        # Interpolate between 0.0 and 1.75
        # Slope = (1.0 - 2.0) / (1.75 - 0) = -1.0 / 1.75 = -0.57
        ratio = f / MEAN_FREQ
        return COST_RARE - (ratio * (COST_RARE - COST_MEAN))
    else:
        # Interpolate between 1.75 and 6.4
        ratio = (f - MEAN_FREQ) / (MAX_FREQ - MEAN_FREQ)
        return COST_MEAN - (ratio * (COST_MEAN - COST_COMMON))

# --- 3. HELPER: FREQUENCY-AWARE SELECTION ---
def find_best_move_for_state(current_indices, depth):
    """
    Calculates the best move using a strategy that favors common words.
    """
    if not current_indices:
        return None, {}

    best_idx = -1
    min_worst = float('inf')
    best_groups = {}

    if depth == 5:
        search_indices = [ALLOWED_MAP[ANSWER_WORDS[i]] for i in current_indices]
        search_indices.sort(key=lambda idx: WORD_FREQ.get(ALLOWED_WORDS[idx], 0.0), reverse=True)
    else:
        search_indices = SORTED_GUESS_INDICES

    for guess_idx in search_indices:
        groups = collections.defaultdict(list)
        
        for ans_idx in current_indices:
            pat_int = MATRIX[guess_idx][ans_idx]
            groups[pat_int].append(ans_idx)
        
        worst = 0
        if groups:
            worst = max(len(g) for g in groups.values())

        if worst < min_worst:
            min_worst = worst
            best_idx = guess_idx
            best_groups = groups
            if min_worst == 1: 
                break
            
    if best_idx != -1:
        return ALLOWED_WORDS[best_idx], best_groups
    
    if current_indices:
        return ANSWER_WORDS[current_indices[0]], {}
        
    return None, {}

# --- 4. UCS STATE SOLVER (Priority Queue) ---
def ucs_solve_by_state(start_word: str = None, initial_candidates: list[str] = None):
    """
    Generates a strategy tree using Uniform Cost Search with Variable Costs.
    """
    pq = [] 
    strategy_map = {}
    visited_states = set()
    
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
        
        groups = collections.defaultdict(list)
        for ans_idx in initial_indices:
            pat_int = MATRIX[start_idx][ans_idx]
            groups[pat_int].append(ans_idx)
            
        for subset in groups.values():
            if len(subset) > 0:
                # Initial Cost = Cost of the start word
                start_cost = get_word_cost(start_word)
                heapq.heappush(pq, (start_cost, id(subset), subset, 1))
    else:
        heapq.heappush(pq, (0, id(initial_indices), initial_indices, 0))

    start_time = time.time()
    nodes_processed = 0

    print(f"Starting UCS for {len(initial_indices)} candidates...")

    while pq:
        # Pop state with lowest ACCUMULATED COST
        cost, _, current_indices, depth = heapq.heappop(pq)
        state_id = tuple(current_indices)

        if state_id in visited_states and not start_word: 
            continue
        visited_states.add(state_id)

        if len(current_indices) == 1:
            strategy_map[state_id] = ANSWER_WORDS[current_indices[0]]
            continue
        
        if depth >= 6: continue

        best_word, best_groups = find_best_move_for_state(current_indices, depth)
        
        if best_word:
            strategy_map[state_id] = best_word
            
            # --- CALCULATE VARIABLE COST ---
            move_cost = get_word_cost(best_word)
            new_total_cost = cost + move_cost
            
            for pat_int, subset in best_groups.items():
                if pat_int == 242: continue 
                
                # Push children with the new accumulated cost
                heapq.heappush(pq, (new_total_cost, id(subset), subset, depth + 1))
            
        nodes_processed += 1
        if nodes_processed % 100 == 0:
            print(f"Processed: {nodes_processed} | PQ Size: {len(pq)} | Cost: {cost:.2f} | Time: {time.time()-start_time:.1f}s")

    return strategy_map

# --- 5. RUNTIME HELPER ---
def use_strategy_map(game_state, strategy_map):
    game_progress = game_state["progress"]
    game_responses = game_state["response"]
    game_finished = game_state["is_game_over"]

    if len(game_responses) == 0:
        if not strategy_map:
            print("Generating initial strategy...")
            strategy_map.update(ucs_solve_by_state(start_word="salet")) 
        return strategy_map.get(max(strategy_map.keys(), key=len))

    if game_finished:
        return None

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