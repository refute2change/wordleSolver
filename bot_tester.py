import time
import tracemalloc
import io
import sys
import statistics
import importlib
import game
import json
import os

# --- CONFIGURATION ---
# Which solvers to test. Format: ("module_name", "solver_func_name", "strategy_loader_func")
# Ensure these files are in the same directory.
SOLVERS_TO_TEST = [
    ("ucs_solver", "use_strategy_map", "ucs_solve_by_state"),
    ("aStar_solver", "use_strategy_map", "astar_solve_by_state")
]

# Which starting words to test for consistency check
STARTING_WORDS = ["salet", "crane", "adieu", "fuzzy"]

# How many games to play per test configuration
GAMES_PER_TEST = 20 # Keep small for quick testing, increase for accuracy

# Answer subset (Load real answers to be fair)
try:
    with open(os.path.join(os.path.dirname(__file__), "pattern_matrix.json"), "r") as f:
        ANSWERS = json.load(f)["answer_words"]
except:
    # Fallback if matrix not found
    ANSWERS = ["apple", "crane", "ghost", "pound", "brave", "stone", "model", "fails", "wight", "watch"]

class Capturing(list):
    """Context manager to capture stdout (print statements)"""
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = io.StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio
        sys.stdout = self._stdout

def run_single_game(game_instance, solver_module, strategy, target_word):
    """
    Plays one full game and records stats.
    """
    game_instance.new_game(answer=target_word)
    moves = 0
    recalculations = 0
    
    start_time = time.perf_counter()
    
    while not game_instance.response["is_game_over"]:
        # Capture print outputs to detect "Off-script" or "Regenerating" messages
        with Capturing() as output:
            try:
                # Dynamic call to the solver's 'use_strategy_map' equivalent
                # We assume the signature is (game_state, strategy_object)
                guess = solver_module.use_strategy_map(game_instance.response, strategy)
            except Exception as e:
                print(f"CRASH: {e}")
                guess = None

        # Check for recalculation triggers in logs
        for line in output:
            if "Off-script" in line or "Regenerating" in line or "Thinking" in line:
                recalculations += 1
        
        if not guess:
            break # Solver gave up
            
        game_instance.add_guess(guess)
        moves += 1
        
        if moves > 10: break # Emergency break for infinite loops

    end_time = time.perf_counter()
    
    is_win = (game_instance.response["response"] and 
              game_instance.response["response"][-1] == [2,2,2,2,2])
    
    return {
        "win": is_win,
        "moves": len(game_instance.response["response"]),
        "time": end_time - start_time,
        "recalcs": recalculations
    }

def benchmark_solver(module_name, strategy_gen_name, start_word, param_overrides=None):
    """
    Runs a benchmark suite for a specific solver configuration.
    """
    print(f"\n--- Testing {module_name} (Start: {start_word}) ---")
    
    # 1. Import/Reload Module
    try:
        mod = importlib.import_module(module_name)
        importlib.reload(mod) # Ensure fresh state
    except ImportError:
        print(f"Error: Could not import {module_name}. Skipping.")
        return None

    # 2. Apply Parameter Overrides (for A*/UCS f/g testing)
    if param_overrides:
        print(f"Applying overrides: {param_overrides}")
        for var_name, value in param_overrides.items():
            if hasattr(mod, var_name):
                setattr(mod, var_name, value)
            else:
                print(f"Warning: {module_name} has no attribute {var_name}")

    # 3. Memory Tracking: Strategy Generation
    print("Generating Strategy...", end="", flush=True)
    tracemalloc.start()
    
    gen_func = getattr(mod, strategy_gen_name)
    t0 = time.perf_counter()
    
    # Generate Strategy
    strategy = gen_func(start_word=start_word)
    
    t1 = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    gen_time = t1 - t0
    gen_memory = peak / 1024 / 1024 # MB
    print(f" Done. ({gen_time:.2f}s, {gen_memory:.2f} MB)")

    # 4. Run Games
    g = game.Game()
    results = []
    
    # Pick random subset of answers for testing
    test_set = ANSWERS[:GAMES_PER_TEST] 
    
    print(f"Running {len(test_set)} games...")
    
    for ans in test_set:
        res = run_single_game(g, mod, strategy, ans)
        results.append(res)

    # 5. Aggregate Stats
    wins = [r for r in results if r["win"]]
    win_rate = (len(wins) / len(results)) * 100
    avg_moves = statistics.mean([r["moves"] for r in wins]) if wins else 0
    avg_time = statistics.mean([r["time"] for r in results])
    avg_recalcs = statistics.mean([r["recalcs"] for r in results])
    
    return {
        "module": module_name,
        "start_word": start_word,
        "win_rate": win_rate,
        "avg_moves": avg_moves,
        "avg_time_per_game": avg_time,
        "avg_recalculations": avg_recalcs,
        "memory_peak_mb": gen_memory,
        "params": param_overrides
    }

def run_parameter_sweep():
    """
    Specifically tests A* and UCS with different cost functions as requested.
    """
    print("\n========================================")
    print("   PHASE 2: PARAMETER SWEEP (UCS/A*)    ")
    print("========================================")
    
    # Define variations of g(n) cost functions
    # Format: {"COST_RARE": x, "COST_COMMON": y} assuming your solver uses these globals
    configs = [
        {"name": "Standard", "params": {}}, # Default
        {"name": "Aggressive (High Rare Penalty)", "params": {"COST_RARE": 5.0, "COST_COMMON": 0.5}},
        {"name": "Flat (No Frequency Bias)", "params": {"COST_RARE": 1.0, "COST_COMMON": 1.0}},
    ]
    
    report = []
    
    for algo in ["aStar_solver", "ucs_solver"]:
        for config in configs:
            stats = benchmark_solver(
                module_name=algo,
                strategy_gen_name="astar_solve_by_state" if "aStar" in algo else "ucs_solve_by_state",
                start_word="salet",
                param_overrides=config["params"]
            )
            if stats:
                stats["config_name"] = config["name"]
                report.append(stats)
                
    return report

def main():
    print("========================================")
    print("      WORDLE BOT ALGORITHM TESTER       ")
    print("========================================")
    
    all_stats = []

    # --- PHASE 1: General Consistency Check ---
    for mod_name, use_func, gen_func in SOLVERS_TO_TEST:
        for start_word in STARTING_WORDS:
            stats = benchmark_solver(mod_name, gen_func, start_word)
            if stats:
                all_stats.append(stats)

    # --- Print General Report ---
    print("\n" + "="*80)
    print(f"{'ALGORITHM':<15} | {'START':<8} | {'WIN %':<6} | {'AVG MOVES':<10} | {'TIME(s)':<8} | {'MEM(MB)':<8}")
    print("-" * 80)
    for s in all_stats:
        print(f"{s['module']:<15} | {s['start_word']:<8} | {s['win_rate']:<6.1f} | {s['avg_moves']:<10.3f} | {s['avg_time_per_game']:<8.4f} | {s['memory_peak_mb']:<8.2f}")
    
    # --- PHASE 2: Run Parameter Sweep ---
    sweep_stats = run_parameter_sweep()
    
    print("\n" + "="*80)
    print(f"{'ALGORITHM':<12} | {'CONFIG':<25} | {'WIN %':<6} | {'MOVES':<6} | {'RECALCS':<8}")
    print("-" * 80)
    for s in sweep_stats:
        print(f"{s['module']:<12} | {s['config_name']:<25} | {s['win_rate']:<6.1f} | {s['avg_moves']:<6.3f} | {s['avg_recalculations']:<8.2f}")

if __name__ == "__main__":
    main()