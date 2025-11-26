import wordHandle
import random
import os
import tkinter
from dataclasses import dataclass

@dataclass
class State:
    progress: list[str]
    response: list[list[int]]
    answer: str
    """
    Holds ONLY the data. 
    It does not know about files, rules, or how to pick answers.
    """
    def __init__(self, progress=None, response=None, answer=""):
        # FIX 1: specific fix for Mutable Default Argument
        self.progress = progress if progress is not None else [""]
        self.response = response if response is not None else []
        self.answer = answer

    def get_data(self) -> dict:
        return {
            "progress": self.progress,
            "response": self.response,
            "answer": self.answer,
            "is_game_over": False if len(self.response) == 0 else (self.response[-1] == [2, 2, 2, 2, 2] or len(self.response) == 6)
        }

    # Helper to just get the current active row index
    def current_row_index(self):
        return len(self.response)

class Game:
    """
    The Controller. 
    Handles rules, file reading, and inputs.
    """
    def __init__(self):
        self.state = State()
        self.stop = False
        with open(os.path.dirname(os.path.abspath(__file__)) + "\\answers\\allowed_words.txt", "r") as f:
            self.answers_list = f.read().splitlines()

    def new_game(self):
        # We create a fresh State object rather than resetting variables manually
        self.state = State()
        self.set_answer()
        self.stop = False

    def set_answer(self):
        # LOGIC MOVED HERE: The Game decides the word, not the State.
        path = os.path.dirname(os.path.abspath(__file__))
        # Kept your Windows path style as requested
        with open(path + "\\answers\\answers.txt", "r") as f:
            self.state.answer = random.choice(f.read().splitlines())
        self.state.answer = self.state.answer.lower()

    @property
    def guess(self) -> int:
        return self.state.current_row_index()

    @property
    def response(self) -> dict:
        return self.state.get_data()

    def add_letter(self, letter: str):
        if self.stop: return
        
        idx = self.state.current_row_index()
        # Check if we are out of bounds (game over state)
        if idx >= 6: return

        if len(self.state.progress[-1]) < 5:
            letter = letter.lower()
            self.state.progress[-1] += letter

    def remove_letter(self):
        if self.stop: return

        idx = self.state.current_row_index()
        if idx >= 6: return
        
        if len(self.state.progress[-1]) > 0:
            self.state.progress[-1] = self.state.progress[-1][:-1]

    # for UI purposes later on, use this function
    def submit_guess(self) -> str:
        """
        Returns a status message for the UI to display (e.g., 'OK', 'Short').
        """
        if self.stop: return "Game Ended"

        idx = self.state.current_row_index()
        if idx >= 6: return "Game Over"

        guess = self.state.progress[-1]

        # 1. Validation Logic
        if len(guess) != 5:
            return "Too Short"
        if guess not in self.answers_list:
            self.state.progress[-1] = ""  # Clear the invalid guess
            return "Not in Word List"
        if guess in self.state.progress[:-1]:
            self.state.progress[-1] = ""  # Clear the invalid guess
            return "Already Guessed"
        
        # 2. Update Logic (FIX 2: Only calculating response here, once)
        response = wordHandle.get_response(guess, self.state.answer)
        self.state.response.append(response)

        # 3. Check Win/Loss
        if guess == self.state.answer:
            self.stop = True
            return "Win"
        elif len(self.state.response) == 6:
            self.stop = True
            return "Loss"
        else:
            if self.state.current_row_index() < 6:
                # Prepare the next empty row
                self.state.progress.append("")
                return "Next Turn"

    def submit(self) -> str:
        """
        Returns a status message for the UI to display (e.g., 'OK', 'Short').
        """
        if self.stop: return "Game Ended"

        idx = self.state.current_row_index()
        if idx >= 6: return "Game Over"

        guess = self.state.progress[-1]
        guess = guess.lower()

        # 1. Validation Logic
        if len(guess) != 5:
            return "Too Short"
        if guess not in self.answers_list:
            return "Not in Word List"
        if guess in self.state.progress[:-1]:
            return "Already Guessed"

        print(self.state.answer)
        
        # 2. Update Logic (FIX 2: Only calculating response here, once)
        response = wordHandle.get_response(guess, self.state.answer)
        self.state.response.append(response)

        # 3. Check Win/Loss
        if guess == self.state.answer:
            self.stop = True
            return "Win"
        elif len(self.state.response) == 6:
            self.stop = True
            return "Loss"
        else:
            if self.state.current_row_index() < 6:
                # Prepare the next empty row
                self.state.progress.append("")
                return "Next Turn"

    def add_guess(self, guess: str):
        if self.stop: return

        idx = self.state.current_row_index()
        if idx >= 6: return

        self.state.progress[-1] = guess
        self.submit_guess()

    # --- CLI Debugging / Play Tool ---
    def play(self):
        self.new_game()
        print(f"(Debug: Answer is {self.state.answer})")
        
        while not self.stop:
            print(f"\nRow {self.state.current_row_index() + 1}")
            user_input = input("Type a 5-letter word: ").lower()
            
            for char in user_input:
                self.add_letter(char)
            
            result = self.submit_guess()
            print(f"Result: {result}")
            print(f"Board: {self.state.progress}")
            print(f"Colors: {self.state.response}")

# Usage
g = Game()
g.play()