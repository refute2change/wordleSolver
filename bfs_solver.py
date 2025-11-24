import collections
import csv
import os
import wordHandle  # Uses your existing module
import game

def bfs_build_decision_tree(all_guesses: list[str], initial_candidates: list[str]):
    """
    Uses BFS to build a complete Wordle decision tree.
    """
    # 1. THE QUEUE
    # Stores tuples: (current_history_string, list_of_remaining_answers)
    queue = collections.deque()
    
    # Initialize with the start state
    queue.append(("", initial_candidates))
    
    # List to store rows for CSV writing
    csv_rows = []

    print(f"Starting BFS with {len(initial_candidates)} words...")

    while queue:
        # 2. DEQUEUE
        history_key, current_candidates = queue.popleft()

        # BASE CASE: Only one word left? We found it.
        if len(current_candidates) == 1:
            ans = current_candidates[0]
            # Record the move: On 'history_key', play the answer
            csv_rows.append([history_key, "N/A", ans])
            # Record the win state
            win_key = history_key + ans + "GGGGG"
            csv_rows.append([win_key, "GGGGG", "OKAY"])
            continue
        
        # Safety check for empty lists
        if not current_candidates:
            continue

        # 3. FIND BEST WORD (Minimax Logic)
        best_word = ""
        min_max_group_size = float('inf')
        best_groups = {} 

        # Optimization: Check current candidates first (Quick Win), then allowed words
        # If the list is small enough, just check everything.
        search_space = all_guesses 

        for guess in search_space:
            groups = collections.defaultdict(list)
            
            for target in current_candidates:
                # --- THE FIX IS HERE ---
                # 1. Get the raw list response
                raw_resp = wordHandle.get_response(guess, target)
                # 2. Convert it to a STRING (which is hashable)
                pattern_key = wordHandle.response_to_str(raw_resp)
                
                groups[pattern_key].append(target)
            
            # Find worst-case split
            current_max_group = 0
            if groups:
                current_max_group = max(len(g) for g in groups.values())

            if current_max_group < min_max_group_size:
                min_max_group_size = current_max_group
                best_word = guess
                best_groups = groups
                
                # Pruning: Perfect split found?
                if min_max_group_size == 1:
                    break

        # 4. RECORD THE DECISION
        csv_rows.append([history_key, "N/A", best_word])
        
        if len(queue) % 10 == 0:
            print(f"Queue: {len(queue)} | Solved: Candidates={len(current_candidates)} -> Guess={best_word}")

        # 5. ENQUEUE NEXT STATES
        for pattern_str, subset in best_groups.items():
            # If pattern is "GGGGG", we won, don't add to queue
            if pattern_str == "GGGGG":
                final_key = history_key + best_word + pattern_str
                csv_rows.append([final_key, "GGGGG", "OKAY"])
                continue
            
            # Create the unique key for the NEXT state
            new_history = history_key + best_word + pattern_str
            
            # Add to queue
            queue.append((new_history, subset))

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
    g = game.Game()
    g.new_game()
    tree = load_decision_tree()
    while 1:
        state = g.response
        print(f"Currently at guess {g.guess}, with words {state['progress']}.")
        next_word = get_next_guess(state, tree)
        print(f"Solver suggests: {next_word}")
        feedback = g.add_guess(next_word)
        state = g.response
        print(f"Feedback: {feedback}")
        print(f"Guesses: {state['progress']}")
        print(f"Current state: {state['response']}")
        if g.response["is_game_over"]:
            break
