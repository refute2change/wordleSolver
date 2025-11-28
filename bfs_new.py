import collections
import csv
import json
import os
import time
import pickle
import game
import random

# --- 1. GLOBAL RESOURCES ---
ALLOWED_MAP = {}
ANSWER_MAP = {}
MATRIX = []
ALLOWED_WORDS = []
ANSWER_WORDS = []

def load_resources():
    global MATRIX, ALLOWED_WORDS, ANSWER_WORDS, ALLOWED_MAP, ANSWER_MAP
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    matrix_path = os.path.join(base_path, "pattern_matrix.json")
    
    if not os.path.exists(matrix_path):
        pass

    print(f"Loading resources from {matrix_path}...")
    with open(matrix_path, "r") as f:
        data = json.load(f)

    MATRIX = data["matrix"]
    ALLOWED_WORDS = data["allowed_words"]
    ANSWER_WORDS = data["answer_words"]

    ALLOWED_MAP = {w: i for i, w in enumerate(ALLOWED_WORDS)}
    ANSWER_MAP = {w: i for i, w in enumerate(ANSWER_WORDS)}
    print("Resources loaded.")

load_resources()

# --- 2. HELPER: MINIMAX LOGIC ---
def find_best_move_for_state(current_indices, depth):
    """
    Calculates the single best move for a specific set of candidates.
    """
    # Safety Check: If no candidates, we can't do anything
    if not current_indices:
        return None, {}

    best_idx = -1
    min_worst = float('inf')
    best_groups = {}

    # Logic: If last guess (Depth 5), must pick candidate.
    if depth == 5:
        search_indices = [ALLOWED_MAP[ANSWER_WORDS[i]] for i in current_indices]
    else:
        search_indices = range(len(ALLOWED_WORDS))

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
            if min_worst == 1: break
            
    if best_idx != -1:
        return ALLOWED_WORDS[best_idx], best_groups
    
    # Fallback: If for some reason we found nothing (shouldn't happen with full search),
    # return the first candidate as a Hail Mary.
    if current_indices:
        fallback_word = ANSWER_WORDS[current_indices[0]]
        return fallback_word, {}
        
    return None, {}

# --- 3. BFS STATE SOLVER (Tree Generator) ---
def bfs_solve_by_state(start_word: str = None, initial_candidates: list[str] = None):
    """
    Generates a strategy tree.
    Args:
        start_word (str): Optional forced first move.
        initial_candidates (list[str]): Optional subset of words to solve for. 
                                        If None, solves for ALL answers.
    """
    queue = collections.deque()
    strategy_map = {}
    visited_states = set()
    
    # --- FLEXIBLE INITIALIZATION ---
    if initial_candidates:
        # Convert user's list of strings into indices using the Global Map
        initial_indices = []
        for w in initial_candidates:
            if w in ANSWER_MAP:
                initial_indices.append(ANSWER_MAP[w])
            else:
                print(f"Warning: Candidate '{w}' not in known answer list. Ignoring.")
    else:
        # Default: Solve for everything
        initial_indices = list(range(len(ANSWER_WORDS)))
    
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
                queue.append((subset, 1))
    else:
        queue.append((initial_indices, 0))

    start_time = time.time()
    nodes_processed = 0

    print(f"Starting BFS for {len(initial_indices)} candidates...")

    while queue:
        current_indices, depth = queue.popleft()
        state_id = tuple(current_indices)

        # Skip if already processed
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
            print(f"Processed: {nodes_processed} | Queue: {len(queue)} | Time: {time.time()-start_time:.1f}s")

    return strategy_map

# --- 4. RUNTIME HELPER ---
def load_strategy(filename="bfs_state_strategy.pkl"):
    base_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_path, "decision_tree", filename)
    if not os.path.exists(path): return {}
    with open(path, "rb") as f: return pickle.load(f)

def get_starting_word(strategy_map):
    # This logic assumes the map was built for the FULL game.
    # If the map was built for a subset, we need to find the key with the largest tuple.
    if not strategy_map: return None
    
    # Heuristic: The starting state is the largest key in the map
    initial_state_id = max(strategy_map.keys(), key=len)
    return strategy_map.get(initial_state_id)

def use_strategy_map(game_state, strategy_map):
    """
    Runtime Lookup with Smart Recovery.
    Handles ANY off-script deviation by calculating the move live.
    """
    game_progress = game_state["progress"]
    game_responses = game_state["response"]
    game_finished = game_state["is_game_over"]

    # --- 1. HANDLE START OF GAME ---
    # If game just started (no responses yet), return the tree's opener.
    if len(game_responses) == 0:
        best_word = ALLOWED_WORDS[random.randint(0, len(ALLOWED_WORDS)-1)]
        strategy_map.update(bfs_solve_by_state(start_word=best_word))
        return best_word
        if not strategy_map:
            # Emergency: No map loaded? Just guess 'salet' or calculate.
            base_path = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_path, "decision_tree", "starting_word_stats.json")
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                    # best_word = max(data.items(), key=lambda x: (x[1]["wins"]/x[1]["plays"] if x[1]["plays"] > 0 else 0))[0]
                    # strategy_map.update(bfs_solve_by_state(start_word=best_word))
                    # return best_word
            best_word = ALLOWED_WORDS[random.randint(0, len(ALLOWED_WORDS)-1)]
            strategy_map.update(bfs_solve_by_state(start_word=best_word))
            return best_word

    if game_finished:
        update_strategy_map(game_responses[-1] == [2, 2, 2, 2, 2], game_progress)
        return None

    # --- 2. FILTER CANDIDATES BASED ON HISTORY ---
    current_indices = list(range(len(ANSWER_WORDS)))
    
    for guess, resp_list in zip(game_progress, game_responses):
        if not guess: continue
        if guess not in ALLOWED_MAP: continue
        guess_idx = ALLOWED_MAP[guess]
        
        target_val = 0
        for j, digit in enumerate(resp_list):
            target_val += digit * (3 ** (4 - j))
            
        current_indices = [
            idx for idx in current_indices 
            if MATRIX[guess_idx][idx] == target_val
        ]
    
    if not current_indices:
        return None # Impossible state

    # --- 3. LOOKUP IN STRATEGY MAP ---
    state_id = tuple(current_indices)
    
    if state_id in strategy_map:
        return strategy_map[state_id]
    
    # --- 4. OFF-SCRIPT DETECTED (THE FIX) ---
    # If we are here, it means the user played a move that put us in a state
    # the pre-calculated tree doesn't know about.
    # We regenerate the search tree for just this state forward.
    
    print(f"Off-script state detected ({len(current_indices)} candidates). Regenerating partial tree...")
    
    strategy_map.update(bfs_solve_by_state(initial_candidates=[ANSWER_WORDS[i] for i in current_indices]))
                
    # After regeneration, try lookup again
    if state_id in strategy_map:
        return strategy_map[state_id]
    
    return None

def update_strategy_map(won: bool, progress: list[str]):
    base_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_path, "decision_tree", "starting_word_stats.json")
    if not os.path.exists(path):
        target = {}
        for word in ALLOWED_WORDS:
            target[word] = {"wins": 0, "plays": 0, "average_moves": 0}
        with open(path, "w", newline="") as f:
            json.dump(target, f, indent=4)
    
    with open(path, "r") as f:
        data = json.load(f)
        if won:
            data[progress[0]]["wins"] += 1
        data[progress[0]]["plays"] += 1
        data[progress[0]]["average_moves"] = (
            (data[progress[0]]["average_moves"] * (data[progress[0]]["plays"] - 1) + len(progress))
            / data[progress[0]]["plays"]
        )
    with open(path, "w", newline="") as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    strategy = None
    
    # print(f"Strategy generated with {len(strategy)} unique states.")
    
    # out_path = os.path.dirname(os.path.abspath(__file__)) + "\\decision_tree\\bfs_state_strategy.pkl"
    # with open(out_path, "wb") as f:
    #     pickle.dump(strategy, f)
    # print(f"Saved binary strategy to {out_path}")
    strategy = {}
    g = game.Game()
    g.new_game()
    success = 0
    fail = 0
    dead_list = []

    with open("E:\\Coding Things\\wordleSolver\\answers\\answers.txt", "r") as f:
        possible_answers = f.read().splitlines()
    
    for i in range(500):
        print(f"--- Test Game {i+1} ---")
        g.new_game()
        while 1:
            state = g.response
            next_word = use_strategy_map(state, strategy)
            if next_word is None:
                # print("No strategy found for current state.")
                break
            print(f"Next guess should be: {next_word}")
            res = g.add_guess(next_word)
            state = g.response
            print(f"Progress: {state['progress']}")
            print(f"Response: {state['response']}")
            if state["is_game_over"]:
                if res == "Win":
                    success += 1
                    # print(f"The solver won in {len(state['response'])} moves!")
                else:
                    fail += 1
                    # print("The solver lost.")
                break
        use_strategy_map(state, strategy)