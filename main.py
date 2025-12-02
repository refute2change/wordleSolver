import game
import ucs_solver, bfs_solver

g = game.Game()
g.new_game()
ucs_solver.load_resources()
bfs_solver.load_resources()
ucs = ucs_solver.load_strategy()
bfs = bfs_solver.load_strategy()

while 1:
    state = g.response
    UCSguess = ucs_solver.get_next_guess(state, ucs)
    print(f"UCS Solver suggests: {UCSguess}")
    BFSguess = bfs_solver.get_next_guess(state, bfs)
    print(f"BFS Solver suggests: {BFSguess}")
    # guess = bfs_solver.get_best_move(g.get_current_state())
    # print(f"BFS Solver suggests: {guess}")
    guess = input("Your Guess: ").strip().lower()
    response = g.add_guess(guess)
    state = g.response
    print(f"Response: {response}")
    print(f"Current State: {state['progress']}")
    print(f"Responses so far: {state['response']}")
    if state['is_game_over']:
        if response == "Win":
            print(f"You win in {len(state['progress'])} guesses!")
        elif response == "Loss":
            print(f"You lose! The word was: {g.answer}")