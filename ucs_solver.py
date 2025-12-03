import collections
import json
import os
import time
import pickle
import game
import random
import heapq  
import sys
import numpy as np 

# --- 1. GLOBAL RESOURCES ---
ALLOWED_MAP = {}
ANSWER_MAP = {}
MATRIX = np.array([]) 
ALLOWED_WORDS = []
ANSWER_WORDS = []
WORD_FREQ = {}
SORTED_GUESS_INDICES = [] 
WORD_COSTS = [] 

def load_resources():
    global MATRIX, ALLOWED_WORDS, ANSWER_WORDS, ALLOWED_MAP, ANSWER_MAP, WORD_FREQ, SORTED_GUESS_INDICES, WORD_COSTS
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    matrix_path = os.path.join(base_path, "pattern_matrix.pkl")
    json_path = os.path.join(base_path, "pattern_matrix.json")
    freq_path = os.path.join(base_path, "answers", "word_frequencies.json")
    
    print(f"Loading resources...")

    # SINGLETON CHECK: If already loaded, do nothing.
    if MATRIX.size > 0 and len(WORD_COSTS) > 0:
        return
    
    # 1. Load Matrix
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
        print("Converting Matrix to NumPy...")
        MATRIX = np.array(data["matrix"], dtype=np.uint8)
        ALLOWED_WORDS = data["allowed_words"]
        ANSWER_WORDS = data["answer_words"]
        print(f"Matrix Size: {MATRIX.nbytes / 1024 / 1024:.2f} MB")
        del data 
    else:
        print("Error: pattern_matrix not found.")
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
    
    # Pre-calculate costs
    MEAN_FREQ = 1.75
    MAX_FREQ = 6.4
    COST_RARE = 2.0
    COST_MEAN = 1.0
    COST_COMMON = 0.6
    
    WORD_COSTS = [0.0] * len(ALLOWED_WORDS)
    indices_with_freq = []
    
    for i, w in enumerate(ALLOWED_WORDS):
        f = WORD_FREQ.get(w, 0.0)
        
        if f <= MEAN_FREQ:
            ratio = f / MEAN_FREQ
            cost = COST_RARE - (ratio * (COST_RARE - COST_MEAN))
        else:
            ratio = (f - MEAN_FREQ) / (MAX_FREQ - MEAN_FREQ)
            cost = COST_MEAN - (ratio * (COST_MEAN - COST_COMMON))
            
        WORD_COSTS[i] = cost
        indices_with_freq.append((i, f))
    
    indices_with_freq.sort(key=lambda x: x[1], reverse=True)
    SORTED_GUESS_INDICES = [x[0] for x in indices_with_freq]

    print("Resources loaded and optimized.")

# --- 2. COST HELPER ---
def get_word_cost(word_idx):
    return WORD_COSTS[word_idx]

# --- 3. HELPER: FREQUENCY-AWARE SELECTION (DEFERRED BUILD) ---
def find_best_move_for_state(current_indices, depth):
    """
    Calculates the best move using a strategy that favors common words.
    OPTIMIZED: Uses Deferred Group Construction to avoid memory churn.
    """
    if not current_indices:
        return None, {}

    best_idx = -1
    min_worst = float('inf')
    # We NO LONGER build best_groups inside the loop
    
    # Convert candidates to numpy array once
    candidates_arr = np.array(current_indices)

    if len(current_indices) <= 2:
        search_indices = [ALLOWED_MAP[ANSWER_WORDS[i]] for i in current_indices]
    elif depth == 5:
        search_indices = [ALLOWED_MAP[ANSWER_WORDS[i]] for i in current_indices]
        search_indices.sort(key=lambda idx: WORD_COSTS[idx])
    else:
        search_indices = SORTED_GUESS_INDICES

    for guess_idx in search_indices:
        # 1. VECTORIZED LOOKUP
        patterns = MATRIX[guess_idx, candidates_arr]
        
        # 2. VECTORIZED COUNTING
        counts = np.bincount(patterns, minlength=243)
        
        # 3. CHECK WORST CASE
        worst = counts.max()
        
        if worst >= min_worst:
            continue

        min_worst = worst
        best_idx = guess_idx
        
        # --- OPTIMIZATION: DO NOT BUILD LISTS YET ---
        # We just remember that this index is the winner so far.
        # We avoid the expensive loop/append logic here.

        if min_worst == 1: 
            break
            
    if best_idx != -1:
        # --- NOW WE BUILD THE GROUPS ---
        # We do this exactly ONCE per node, instead of potentially 20-30 times.
        best_groups = collections.defaultdict(list)
        patterns = MATRIX[best_idx, candidates_arr]
        
        for idx, pat in zip(current_indices, patterns):
            best_groups[pat].append(idx)
            
        return ALLOWED_WORDS[best_idx], best_groups
    
    if current_indices:
        return ANSWER_WORDS[current_indices[0]], {}
        
    return None, {}

# --- 4. UCS STATE SOLVER ---
def ucs_solve_by_state(start_word: str = None, initial_candidates: list[str] = None):
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
    
    if start_word:
        start_idx = ALLOWED_MAP[start_word]
        initial_tuple = tuple(initial_indices)
        strategy_map[initial_tuple] = start_word
        visited_states.add(initial_tuple)
        
        # NumPy Split for Start Node
        c_arr = np.array(initial_indices)
        patterns = MATRIX[start_idx, c_arr]
        
        groups = collections.defaultdict(list)
        for idx, pat in zip(initial_indices, patterns):
            groups[pat].append(idx)
            
        for subset in groups.values():
            if len(subset) > 0:
                start_cost = get_word_cost(start_idx)
                heapq.heappush(pq, (start_cost, id(subset), subset, 1))
    else:
        heapq.heappush(pq, (0, id(initial_indices), initial_indices, 0))

    start_time = time.time()
    nodes_processed = 0

    print(f"Starting UCS (Exhaustive) for {len(initial_indices)} candidates...")

    while pq:
        cost, _, current_indices, depth = heapq.heappop(pq)
        state_id = tuple(current_indices)

        if state_id in visited_states and not start_word: 
            continue
        visited_states.add(state_id)

        if len(current_indices) == 1:
            strategy_map[state_id] = ANSWER_WORDS[current_indices[0]]
            continue

        best_word, best_groups = find_best_move_for_state(current_indices, depth)
        
        if best_word:
            strategy_map[state_id] = best_word
            
            best_idx = ALLOWED_MAP[best_word]
            move_cost = get_word_cost(best_idx)
            new_total_cost = cost + move_cost
            
            for pat_int, subset in best_groups.items():
                if pat_int == 242: continue 
                heapq.heappush(pq, (new_total_cost, id(subset), subset, depth + 1))
            
        nodes_processed += 1
        if nodes_processed % 100 == 0:
            print(f"Processed: {nodes_processed} | PQ Size: {len(pq)} | Cost: {cost:.2f} | Time: {time.time()-start_time:.1f}s")
    elapsed = time.time() - start_time

    print(f"UCS Complete. Total Nodes: {nodes_processed} | Time: {elapsed:.1f}s")
    return strategy_map, nodes_processed, elapsed

# --- 5. PERSISTENCE HELPERS ---
def save_strategy(strategy_map):
    STRATEGY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decision_tree", "ucs_strategy_map2.pkl")
    os.makedirs(os.path.dirname(STRATEGY_FILE), exist_ok=True)
    with open(STRATEGY_FILE, "wb") as f:
        pickle.dump(strategy_map, f)
    print(f"Strategy map saved to {STRATEGY_FILE}. Size: {len(strategy_map)} states.")

def load_strategy():
    STRATEGY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decision_tree", "ucs_strategy_map2.pkl")
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

# --- 6. RUNTIME HELPER ---
def get_next_guess(game_state, strategy_map):
    if not strategy_map:
        loaded = load_strategy()
        if loaded:
            strategy_map.update(loaded)
        else:
            print("No strategy found. Generating initial 'salet' strategy...")
            strategy_map.update(ucs_solve_by_state(start_word="salet"))
            save_strategy(strategy_map)

    game_progress = game_state["progress"]
    game_responses = game_state["response"]
    game_finished = game_state["is_game_over"]

    if len(game_responses) == 0:
        initial_key = tuple(range(len(ANSWER_WORDS))) 
        if initial_key not in strategy_map:
             print("Initial state missing. Regenerating 'salet' strategy...")
             strategy_map.update(ucs_solve_by_state(start_word="salet"))
             save_strategy(strategy_map)
        return strategy_map.get(max(strategy_map.keys(), key=len))

    if game_finished:
        return None

    current_indices = np.arange(len(ANSWER_WORDS))
    
    for guess, resp_list in zip(game_progress, game_responses):
        if not guess or guess not in ALLOWED_MAP: continue
        guess_idx = ALLOWED_MAP[guess]
        
        target_val = 0
        for j, digit in enumerate(resp_list):
            target_val += digit * (3 ** (4 - j))
            
        patterns = MATRIX[guess_idx, current_indices]
        mask = (patterns == target_val)
        current_indices = current_indices[mask]
    
    current_indices = current_indices.tolist()
    
    if not current_indices: return None

    state_id = tuple(current_indices)
    if state_id in strategy_map:
        return strategy_map[state_id]
    
    print(f"Off-script state ({len(current_indices)} candidates). Recovering with UCS...")
    new_sub_strategy = ucs_solve_by_state(initial_candidates=[ANSWER_WORDS[i] for i in current_indices])
    
    strategy_map.update(new_sub_strategy)
    save_strategy(strategy_map)
    
    return strategy_map.get(state_id)

if __name__ == "__main__":
    load_resources()
    word_set = ['finds', 'dykes', 'motes', 'salle', 'swill', 'uncus', 'alays', 'skald', 'sprad', 'mashy', 'refix', 'chibs', 'altar', 'herye', 'comas', 'gotta', 'scion', 'bisom', 'mimic', 'coxed', 'samas', 'gulag', 'savoy', 'runty', 'dryly', 'dirge', 'safes', 'smite', 'award', 'donee', 'foray', 'knows', 'adred', 'galah', 'daych', 'lawny', 'unpin', 'trank', 'rolfs', 'podia', 'godso', 'sakai', 'inula', 'yarns', 'iambi', 'tying', 'tozed', 'miaul', 'salop', 'nisus'] 
    g = game.Game()

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "answers", "answers.txt"), "r") as f:
        answer_list = f.read().splitlines()

    expermentreport = {i:{'nodes_processed':0, 'time':0.0, 'wins': 0, 'moves': [], 'avg_time_per_guess': 0.0, 'avg_time_per_game': 0.0} for i in word_set}

    for w in word_set:

        strategy, nodes_expanded, processed_time = ucs_solve_by_state(start_word=w)

        success = 0
        fail = 0
        totalmoves = 0
        moves_used = []
        totaltimes = 0.0
        totalmovetime = 0.0

        for answer in answer_list:
            print(f"--- UCS Test Game for answer '{answer}' starting with '{w}' ---")
            g.new_game(answer=answer)

            game_start_time = time.time()

            while True:
                state = g.response
                # Strategy map is mutable dict, updates happen inside use_strategy_map
                move_start = time.time()
                next_guess = get_next_guess(game_state=state, strategy_map=strategy)
                totalmovetime += time.time() - move_start
                # print(f"The bot suggests: {next_guess}.")
                res = g.add_guess(next_guess)
                print(f"Response: {res}")
                print(f"Progress: {g.response['progress']}")
                print(f"Responses: {g.response['response']}")
                if g.response["is_game_over"]:
                    moves_used.append(len(state['response']))
                    totalmoves += len(state['response'])
                    totaltimes += time.time() - game_start_time
                    if res == "Win":
                        success += 1
                        # print(f"Won in {len(state['response'])} moves.")
                    else:
                        fail += 1
                        # print(f"Lost. The answer was: {g.answer}.")
                    break
        expermentreport[w]['nodes_processed'] = nodes_expanded
        expermentreport[w]['time'] = processed_time
        expermentreport[w]['wins'] = success
        expermentreport[w]['moves'] = moves_used
        expermentreport[w]['avg_time_per_guess'] = totalmovetime / totalmoves if totalmoves > 0 else 0.0
        expermentreport[w]['avg_time_per_game'] = totaltimes / (success + fail) if (success + fail) > 0 else 0.0
        print("Experiment Report:")
        print(expermentreport[w])
    
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ucs_experiment_report.json"), "w") as f:
        json.dump(expermentreport, f, indent=4)

    # success = 0
    # fail = 0
    # totalmoves = 0

    # with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "answers", "answers.txt"), "r") as f:
    #     answer_list = f.read().splitlines()
    
    # for i in range(len(answer_list)): 
    #     print(f"--- UCS Test Game {i+1} ---")
    #     g.new_game(answer_list[i])
    #     while True:
    #         state = g.response
    #         # Strategy map is mutable dict, updates happen inside get_next_guess
    #         next_word = get_next_guess(state, strategy)
    #         if next_word is None: break
            
    #         print(f"Guess: {next_word}")
    #         res = g.add_guess(next_word)
            
    #         state = g.response
    #         print(f"Response: {res}")
    #         print(f"Progress: {state['progress']}")
    #         print(f"Responses: {state['response']}")            

    #         if state["is_game_over"]:
    #             if res == "Win":
    #                 success += 1
    #                 totalmoves += len(state['response'])
    #                 print(f"Won in {len(state['response'])} moves.")
    #             else:
    #                 fail += 1
    #                 print("Lost.")
    #             break
    
    # print(f"UCS Solver Results: {success} Wins, {fail} Losses, Average Moves: {totalmoves/success if success > 0 else 0:.2f}")