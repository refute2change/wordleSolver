import collections
import json
import os
import time
import pickle
import game
import random
import heapq
import math  # Needed for Entropy and Heuristic

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
    
    if os.path.exists(matrix_path):
        with open(matrix_path, "r") as f:
            data = json.load(f)
        MATRIX = data["matrix"]
        ALLOWED_WORDS = data["allowed_words"]
        ANSWER_WORDS = data["answer_words"]
    else:
        print("Error: pattern_matrix.json not found.")
        return

    if os.path.exists(freq_path):
        with open(freq_path, "r") as f:
            WORD_FREQ = json.load(f)
        print("Frequencies loaded.")
    else:
        print("Warning: word_frequencies.json not found. Defaulting to 0.")
        WORD_FREQ = {}

    ALLOWED_MAP = {w: i for i, w in enumerate(ALLOWED_WORDS)}
    ANSWER_MAP = {w: i for i, w in enumerate(ANSWER_WORDS)}
    
    # Sort indices by frequency for optimization in move selection
    indices_with_freq = []
    for i, w in enumerate(ALLOWED_WORDS):
        f = WORD_FREQ.get(w, 0.0)
        indices_with_freq.append((i, f))
    
    indices_with_freq.sort(key=lambda x: x[1], reverse=True)
    SORTED_GUESS_INDICES = [x[0] for x in indices_with_freq]

    print("Resources loaded and optimized.")

load_resources()

# --- 2. A* HELPERS ---

def get_word_cost(word):
    """
    Calculates g(action): Cost of using a specific word based on frequency.
    Same logic as UCS: Common words are cheap, rare words are expensive.
    """
    f = WORD_FREQ.get(word, 0.0)
    
    MEAN_FREQ = 1.75
    MAX_FREQ = 6.4
    
    COST_RARE = 2.0
    COST_MEAN = 1.0
    COST_COMMON = 0.6

    if f <= MEAN_FREQ:
        ratio = f / MEAN_FREQ
        return COST_RARE - (ratio * (COST_RARE - COST_MEAN))
    else:
        ratio = (f - MEAN_FREQ) / (MAX_FREQ - MEAN_FREQ)
        return COST_MEAN - (ratio * (COST_MEAN - COST_COMMON))

def calculate_heuristic(num_candidates):
    """
    Calculates h(n): Estimated remaining cost to solution.
    Based on Information Theory: We need log2(N) bits to distinguish N items.
    We assume an average guess provides ~4 bits of information.
    We assume the average cost per guess is ~1.0.
    """
    if num_candidates <= 1: return 0
    
    bits_needed = math.log2(num_candidates)
    expected_bits_per_turn = 4.0 # Tunable parameter
    
    estimated_turns = bits_needed # / expected_bits_per_turn
    
    return estimated_turns * 1.0 # Scale by average cost

def calculate_entropy(group_counts, total_candidates):
    """
    Calculates the Information Entropy of a split.
    H = -Sum(p * log2(p))
    """
    entropy = 0
    for count in group_counts:
        if count > 0:
            p = count / total_candidates
            entropy -= p * math.log2(p)
    return entropy

# --- 3. ENTROPY-BASED MOVE SELECTION ---
def find_best_move_astar(current_indices, depth):
    """
    Selects the best word by maximizing Efficiency = Entropy / Cost.
    This replaces the Minimax logic with Information Theory logic.
    """
    if not current_indices: return None, {}

    # Optimization: If only 1 word left, pick it.
    if len(current_indices) == 1:
        return ANSWER_WORDS[current_indices[0]], {}

    best_idx = -1
    max_efficiency = -1.0 # We want to MAXIMIZE bits per cost
    best_groups = {}
    
    total_candidates = len(current_indices)

    # Search Space Logic
    # For A*, deeper search is better. We search all words unless it's the last turn.
    if depth == 5:
        # Last turn: Must pick a candidate (Greedy)
        search_indices = [ALLOWED_MAP[ANSWER_WORDS[i]] for i in current_indices]
    elif len(current_indices) <= 2:
        # Micro-optimization
        search_indices = [ALLOWED_MAP[ANSWER_WORDS[i]] for i in current_indices]
    else:
        # Search all words, prioritized by frequency
        search_indices = SORTED_GUESS_INDICES

    for guess_idx in search_indices:
        groups = collections.defaultdict(list)
        
        # 1. Build Groups (Simulate guess)
        for ans_idx in current_indices:
            pat_int = MATRIX[guess_idx][ans_idx]
            groups[pat_int].append(ans_idx)
        
        # 2. Calculate Entropy (Information Gain)
        group_counts = [len(g) for g in groups.values()]
        entropy = calculate_entropy(group_counts, total_candidates)
        
        # 3. Calculate Cost (Penalty for rare words)
        word = ALLOWED_WORDS[guess_idx]
        cost = get_word_cost(word)
        
        # 4. Calculate Efficiency (Bits gained per Unit of Cost)
        efficiency = entropy / cost
        
        # Bonus: If the word is actually a possible answer, boost it slightly.
        # This acts as a tie-breaker to prefer winning immediately.
        # (Check if guess_idx maps to an answer index present in current_indices)
        # Note: Mapping check is slightly expensive, simplified check:
        # If efficiency is very high, it likely splits well.
        
        if efficiency > max_efficiency:
            max_efficiency = efficiency
            best_idx = guess_idx
            best_groups = groups
            
            # Pruning is harder with Entropy because max entropy depends on distribution.
            # But if we find a very high entropy with low cost, we can break early.
            # Max possible entropy is log2(total_candidates).
            # If we reach near theoretical max, stop.
            if entropy > math.log2(total_candidates) - 0.1 and cost < 0.8:
                break
            
    if best_idx != -1:
        return ALLOWED_WORDS[best_idx], best_groups
    
    # Fallback
    return ANSWER_WORDS[current_indices[0]], {}

# --- 4. A* SOLVER ---
def astar_solve_by_state(start_word: str = None, initial_candidates: list[str] = None):
    """
    Generates a strategy tree using A* Search.
    Priority Queue sorts by f(n) = g(n) + h(n).
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
    
    # --- START NODE ---
    if start_word:
        start_idx = ALLOWED_MAP[start_word]
        initial_tuple = tuple(initial_indices)
        strategy_map[initial_tuple] = start_word
        visited_states.add(initial_tuple)
        
        groups = collections.defaultdict(list)
        for ans_idx in initial_indices:
            pat_int = MATRIX[start_idx][ans_idx]
            groups[pat_int].append(ans_idx)
            
        # Initial Cost g
        g_start = get_word_cost(start_word)
        
        for subset in groups.values():
            if len(subset) > 0:
                # A* Calculation
                # g = cost so far
                # h = estimated remaining cost
                h = calculate_heuristic(len(subset))
                f = g_start + h
                
                # Heap: (f, g, depth, tie_breaker_id, subset)
                heapq.heappush(pq, (f, g_start, 1, id(subset), subset))
    else:
        # If no start word, push the root state
        h = calculate_heuristic(len(initial_indices))
        heapq.heappush(pq, (h, 0, 0, id(initial_indices), initial_indices))

    start_time = time.time()
    nodes_processed = 0

    print(f"Starting A* for {len(initial_indices)} candidates...")

    while pq:
        # Pop lowest f(n)
        f, g, depth, _, current_indices = heapq.heappop(pq)
        state_id = tuple(current_indices)

        if state_id in visited_states and not start_word: 
            continue
        visited_states.add(state_id)

        # Base Case: Solved
        if len(current_indices) == 1:
            strategy_map[state_id] = ANSWER_WORDS[current_indices[0]]
            continue
        
        if depth >= 6: continue

        # Local Search (Greedy Entropy)
        best_word, best_groups = find_best_move_astar(current_indices, depth)
        
        if best_word:
            strategy_map[state_id] = best_word
            
            # Update Path Cost g(n)
            move_cost = get_word_cost(best_word)
            new_g = g + move_cost
            
            for pat_int, subset in best_groups.items():
                if pat_int == 242: continue 
                
                # Calculate h(n) for child
                new_h = calculate_heuristic(len(subset))
                new_f = new_g + new_h
                
                heapq.heappush(pq, (new_f, new_g, depth + 1, id(subset), subset))
            
        nodes_processed += 1
        if nodes_processed % 50 == 0:
            # Debug Stats
            # Note: h is not stored in pq item, so we calculate it for display: h = f - g
            print(f"Processed: {nodes_processed} | PQ: {len(pq)} | f: {f:.2f} (g={g:.2f}, h={f-g:.2f}) | Time: {time.time()-start_time:.1f}s")

    return strategy_map

# --- 5. RUNTIME HELPER ---
def use_strategy_map(game_state, strategy_map):
    game_progress = game_state["progress"]
    game_responses = game_state["response"]
    game_finished = game_state["is_game_over"]

    if len(game_responses) == 0:
        if not strategy_map:
            print("Generating initial strategy (A*)...")
            strategy_map.update(astar_solve_by_state(start_word="salet")) 
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
        current_indices = [i for i in current_indices if MATRIX[guess_idx][i] == target_val]
    
    if not current_indices: return None

    state_id = tuple(current_indices)
    if state_id in strategy_map:
        return strategy_map[state_id]
    
    print(f"Off-script state ({len(current_indices)} candidates). Recovering with A*...")
    strategy_map.update(astar_solve_by_state(initial_candidates=[ANSWER_WORDS[i] for i in current_indices]))
    
    return strategy_map.get(state_id)

if __name__ == "__main__":
    strategy = {}
    g = game.Game()

    # Quick validation on 5 words
    for word in ALLOWED_WORDS[:5]:
        success = 0
        fail = 0
        totalmoves = 0
        
        # A* works best with a good starter, but can solve from any.
        # We test solving *from* the word as the opener.
        print(f"--- A* Test Opener: {word} ---")
        strategy = astar_solve_by_state(start_word=word)

        # Test on a small subset of answers to verify
        test_answers = ANSWER_WORDS 
        for ans in test_answers: 
            g.new_game(ans)
            while True:
                state = g.response
                next_word = use_strategy_map(state, strategy)
                if next_word is None: break
                
                res = g.add_guess(next_word)
                state = g.response

                if state["is_game_over"]:
                    if res == "Win":
                        success += 1
                        totalmoves += len(state['response'])
                    else:
                        fail += 1
                    break
        
        print(f"Results for {word}: {success} Wins, {fail} Losses, Avg: {totalmoves/success if success else 0:.2f}")