import collections
import csv
import json
import os
import time
import pickle
import game

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
        # Fallback for testing environment
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

# --- 2. BFS STATE SOLVER ---
def bfs_solve_by_state(start_word: str = None):
    """
    Solves Wordle by treating the 'Set of Remaining Words' as the state.
    This merges duplicate branches (Transpositions), making it much faster.
    """
    # Queue stores: (list_of_candidate_INDICES, depth)
    # We DO NOT store history strings anymore, because multiple histories 
    # can point to this same state.
    queue = collections.deque()
    
    # The Result Map: { tuple(candidate_indices) : best_word_index }
    # This is our "Strategy Book"
    strategy_map = {}
    
    # Visited Set to detect Transpositions
    # Stores: tuple(candidate_indices)
    visited_states = set()

    # Initial State: All answers
    initial_indices = list(range(len(ANSWER_WORDS)))
    
    # Handle Forced Start
    if start_word:
        # We manually process the start to force the first move
        start_idx = ALLOWED_MAP[start_word]
        
        # We assume the "All Candidates" state maps to the start_word
        initial_tuple = tuple(initial_indices)
        strategy_map[initial_tuple] = start_word
        visited_states.add(initial_tuple)
        
        # Calculate splits for Turn 1
        groups = collections.defaultdict(list)
        for ans_idx in initial_indices:
            pat_int = MATRIX[start_idx][ans_idx]
            groups[pat_int].append(ans_idx)
            
        for subset in groups.values():
            if len(subset) > 0:
                queue.append((subset, 1))
    else:
        # Standard: Start from scratch
        queue.append((initial_indices, 0))

    start_time = time.time()
    nodes_processed = 0
    skipped_nodes = 0

    print(f"Starting Graph-Based BFS...")

    while queue:
        current_indices, depth = queue.popleft()
        
        # 1. CREATE STATE ID
        # Converting list to tuple makes it hashable for sets/dicts
        state_id = tuple(current_indices)

        # 2. CHECK VISITED (Transposition Table)
        if state_id in visited_states:
            skipped_nodes += 1
            continue
        visited_states.add(state_id)

        # 3. BASE CASE: Solved
        if len(current_indices) == 1:
            # The strategy for a single word is just to guess that word
            strategy_map[state_id] = ANSWER_WORDS[current_indices[0]]
            continue
        
        if depth >= 6: continue

        # 4. MINIMAX LOGIC (Same as before)
        best_idx = -1
        min_worst = float('inf')
        best_groups = {}

        if len(current_indices) < 20:
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
        
        if best_idx == -1: continue
        
        # 5. RECORD STRATEGY
        best_word = ALLOWED_WORDS[best_idx]
        strategy_map[state_id] = best_word

        # 6. ENQUEUE CHILDREN
        for pat_int, subset in best_groups.items():
            if pat_int == 242: continue # Win state doesn't need solving
            queue.append((subset, depth + 1))
            
        nodes_processed += 1
        if nodes_processed % 100 == 0:
            print(f"Processed: {nodes_processed} | Skipped: {skipped_nodes} | Queue: {len(queue)} | Time: {time.time()-start_time:.1f}s")

    return strategy_map

def load_strategy(filename="bfs_state_strategy.pkl"):
    """
    Loads the pre-calculated strategy map from a pickle file.
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_path, "decision_tree", filename)
    
    if not os.path.exists(path):
        print(f"Warning: Strategy file not found at {path}")
        return {}

    print(f"Loading strategy from {path}...")
    with open(path, "rb") as f:
        strategy = pickle.load(f)
    print(f"Loaded strategy with {len(strategy)} states.")
    return strategy

def get_starting_word(strategy_map):
    """
    Retrieves the opening move from the strategy map.
    The opening move is keyed by the tuple of ALL answer indices.
    """
    # The initial state is represented by a tuple of indices 0 to N-1
    # because that represents the set of "All Possible Answers"
    initial_state_id = tuple(range(len(ANSWER_WORDS)))
    
    return strategy_map.get(initial_state_id)

# --- 4. RUNTIME HELPER ---
def use_strategy_map(game_state, strategy_map):
    """
    To use the strategy map, we must reconstruct the STATE (candidate set)
    from the game history at runtime.
    """
    # 1. Extract Data
    game_progress = game_state["progress"]
    game_responses = game_state["response"]
    if strategy_map is None:
        strategy_map.update(bfs_solve_by_state(start_word=game_progress[0]))
    if len(game_responses) >= 1 and game_progress[0] != get_starting_word(strategy_map):
        strategy_map.update(bfs_solve_by_state(start_word=game_progress[0]))
    # 1. Filter candidates based on history
    current_indices = list(range(len(ANSWER_WORDS)))
    
    # Re-apply all past clues to narrow down the list
    for guess, resp_list in zip(game_progress, game_responses):
        if not guess: continue
        guess_idx = ALLOWED_MAP[guess]
        
        # Convert response list [0,2,0..] to int mask
        # (Assuming you have a helper for this, or standard calculation)
        target_val = 0
        for j, digit in enumerate(resp_list):
            target_val += digit * (3 ** (4 - j))
            
        # Filter
        current_indices = [
            idx for idx in current_indices 
            if MATRIX[guess_idx][idx] == target_val
        ]
        
    # 2. Look up the resulting set in our map
    state_id = tuple(current_indices)
    
    if state_id in strategy_map:
        return strategy_map[state_id]
    else:
        return None # State not found (or Off-Script)
    


if __name__ == "__main__":
    # Generate the strategy
    strategy = load_strategy()
    g = game.Game()
    g.new_game()
    
    # with open("E:\Coding Things\wordleSolver\answers\answers.txt", "r") as f:
    #     possible_answers = f.read().splitlines()
    

    while 1:
        state = g.response
        next_word = use_strategy_map(state, strategy)
        if next_word is None:
            print("No strategy found for current state.")
            break
        print(f"Next guess should be: {next_word}")
        res = g.add_guess(next_word)
        state = g.response
        print(f"Progress: {state['progress']}")
        print(f"Response: {state['response']}")
        if state["is_game_over"]:
            if res == "Win":
                print(f"The solver won in {len(state['response'])} moves!")
            else:
                print("The solver lost.")
            break