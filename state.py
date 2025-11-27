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
            "is_game_over": False if len(self.response) == 0 else (self.response[-1] == [2, 2, 2, 2, 2] or len(self.response) == 6)
        }

    # Helper to just get the current active row index
    def current_row_index(self):
        return len(self.response)

    def unwind_guess(self):
        if len(self.progress) - len(self.response) == 1:
            self.progress[-1] = ""