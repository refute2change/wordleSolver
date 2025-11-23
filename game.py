import wordHandle
import random
import os

class state:
    progress: list[str]
    response: list[str]
    answer: str

    def __init__(self, progress: list[str] = [""], response: list[str] = [], answer: str = ""):
        self.progress = progress
        self.response = response
        self.answer = answer

    def set_answer(self):
        path = os.path.dirname(os.path.abspath(__file__))
        with open(path + "\\answers\\answers.txt", "r") as f:
            self.answer = random.choice(f.read().splitlines())

    def get_answer(self) -> str:
        return self.answer

    def get_state(self) -> dict:
        return {
            "progress": self.progress,
            "response": self.response,
            "answer": self.answer
        }

    def intiate(self):
        self.progress = [""]
        self.response = []
        self.set_answer()

    def update(self):
        self.response = []
        for guess in self.progress:
            if len(guess) == 5:
                resp = wordHandle.get_response(guess, self.answer)
                self.response.append(resp)

    def add_guess(self, guess: str):
        if len(self.progress) == 6:
            return
        self.progress[-1] = guess
        self.update()
    
    def add_letter(self, letter: str):
        if len(self.progress) == 6:
            return
        if len(self.progress[-1]) == 5:
            return
        self.progress[-1] += letter
    
    def remove_letter(self):
        if len(self.progress) == 0:
            return
        if len(self.progress[-1]) == 0:
            return
        else:
            self.progress[-1] = self.progress[-1][:-1]

    def enter_guess(self):
        if len(self.progress) == 6:
            return
        if len(self.progress[-1]) != 5:
            return
        self.response.append(wordHandle.get_response(self.progress[-1], self.answer))


class game:
    def __init__(self):
        self.state = state()
        self.guess = 0
        self.stop = False

    def new_game(self):
        self.state.intiate()  # note: uses state's intiate()
        self.guess = 0
        self.stop = False

    def set_answer(self):
        self.state.set_answer()

    def get_answer(self) -> str:
        return self.state.answer

    def get_state(self) -> dict:
        return self.state.get_state()

    def add_letter(self, letter: str):
        if self.stop:
            return
        self.state.add_letter(letter)

    def remove_letter(self):
        if self.stop:
            return
        self.state.remove_letter()

    def add_guess(self, guess: str):
        if self.stop or self.guess >= 6:
            return
        if len(guess) != 5 or not guess.isalpha():
            raise ValueError("Guess must be a 5-letter word.")
        self.state.add_guess(guess.lower())

    def submit_guess(self):
        if self.stop or self.guess >= 6:
            return
        if len(self.state.progress[-1]) != 5:
            return

        current = self.state.progress[-1]
        self.state.enter_guess()
        # increment guess count if a response was recorded
        if len(self.state.response) > self.guess:
            self.guess += 1

        if current == self.state.answer:
            self.stop = True
        else:
            # prepare next empty row if still allowed
            if self.guess < 6:
                # ensure there's an empty slot to type into
                if len(self.state.progress) < 6:
                    self.state.progress.append("")

    def input_guess(self):
        user_input = input("Enter your 5-letter guess: ")
        if len(user_input) == 5 and user_input.isalpha():
            try:
                self.add_guess(user_input.lower())
                self.submit_guess()
            except ValueError as e:
                print(e)
        else:
            print("Invalid input. Please enter a 5-letter word.")

    def play(self):
        self.new_game()
        while not self.stop and self.guess < 6:
            while True:
                print(f"Guess {self.guess + 1}: ", end="")
                user_input = input()
                if len(user_input) == 5 and user_input.isalpha():
                    try:
                        self.add_guess(user_input.lower())
                        break
                    except ValueError:
                        print("Invalid guess. Please enter a 5-letter word.")
                else:
                    print("Invalid guess. Please enter a 5-letter word.")
            self.submit_guess()
            print(f"Current Progress: {self.state.progress}")
            if self.guess > 0:
                print(f"Last Response: {self.state.response[self.guess - 1]}")

        if self.stop:
            print(f"Congratulations! You've guessed the word: {self.state.answer}")
        else:
            print(f"Game over! The correct word was: {self.state.answer}")

# g = game()
# g.play()