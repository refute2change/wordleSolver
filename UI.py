import tkinter as tk
from tkinter import messagebox
import random
import string
import os

# --------------------- Configuration / Colors ---------------------
BG = "#121213"
TILE_BG = "#535569"
EMPTY_TILE_BG = "#8e9091"
TEXT_COLOR = "#ffffff"
GREEN = "#6aaa64"
YELLOW = "#c9b458"
GREY = "#c7c8c9"
DARK_GREY = "#3d4054"
KEY_BG = "#818384"
KEY_ACTIVE = "#565758"

ROWS = 6
COLS = 5
WORDLIST_FILE = "word-list.txt"

# --------------------- Word List Loading ---------------------
def load_word_list(path):
    if not os.path.exists(path):
        # Provide a short fallback list if file not found to prevent crash
        return ["apple","brave","cigar","deltae","eagle","flame","grace","house","inner","joker"]
    with open(path, "r", encoding="utf-8") as f:
        words = [line.strip().lower() for line in f if line.strip()]
    # Keep only 5-letter alphabetic words
    words = [w for w in words if len(w) == 5 and all(ch in string.ascii_lowercase for ch in w)]
    
    return words

# --------------------- Main Application ---------------------
class WordleApp:
    def __init__(self, root):
        self.root = root
        root.title("Wordle Tkinter")
        root.configure(bg=BG)
        self.word_list = load_word_list(WORDLIST_FILE)
        if not self.word_list:
            messagebox.showerror("Error", f"No valid words found in {WORDLIST_FILE}.")
            root.destroy()
            return

        self.target_word = random.choice(self.word_list)
        self.attempt = 0
        self.col = 0
        self.grid_letters = [["" for _ in range(COLS)] for _ in range(ROWS)]
        self.labels = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.key_buttons = {}
        self.warn_after_id = None
        self.game_over = False

        self.create_ui()
        root.bind("<Key>", self.on_key)  # physical keyboard
        # debug: print("Target:", self.target_word)

    def create_ui(self):
        top_frame = tk.Frame(self.root, bg=BG)
        top_frame.pack(pady=12)

        board = tk.Frame(top_frame, bg=BG)
        board.pack()

        # create 6x5 tiles
        for r in range(ROWS):
            row_frame = tk.Frame(board, bg=BG)
            row_frame.pack(padx=2, pady=2)
            for c in range(COLS):
                lbl = tk.Label(row_frame, text="", width=4, height=2,
                               font=("Helvetica", 24, "bold"),
                               bg=EMPTY_TILE_BG, fg=TEXT_COLOR, bd=2, relief="solid")
                lbl.grid(row=r, column=c, padx=6, pady=6)
                self.labels[r][c] = lbl

        # message/warning label
        self.msg = tk.Label(self.root, text="", fg="white", bg=BG, font=("Helvetica", 12, "bold"))
        self.msg.pack(pady=6)

        # keyboard frame
        kb_frame = tk.Frame(self.root, bg=BG)
        kb_frame.pack(pady=6)

        rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
        for i, row in enumerate(rows):
            rowf = tk.Frame(kb_frame, bg=BG)
            rowf.pack(pady=4)
            if i == 2:
                # add backspace button
                back = tk.Button(rowf, text="⌫", width=5, height=2, command=self.backspace,
                                 bg=KEY_BG, fg=TEXT_COLOR, bd=0)
                back.pack(side="left", padx=3)
            for ch in row:
                btn = tk.Button(rowf, text=ch.upper(), width=4, height=2,
                                command=lambda ch=ch: self.add_letter(ch),
                                bg=KEY_BG, fg=TEXT_COLOR, bd=0)
                btn.pack(side="left", padx=3)
                self.key_buttons[ch] = btn
            if i == 0:
                # add Enter on right of first row
                enter = tk.Button(rowf, text="Enter", width=6, height=2, command=self.submit_word,
                                  bg=KEY_BG, fg=TEXT_COLOR, bd=0)
                enter.pack(side="left", padx=6)

        # Reset button
        ctrl_frame = tk.Frame(self.root, bg=BG)
        ctrl_frame.pack(pady=8)
        reset_btn = tk.Button(ctrl_frame, text="Reset", command=self.reset_game, bg="#2b2b2b", fg=TEXT_COLOR)
        reset_btn.pack()

    # --------------------- Input Handling ---------------------
    def on_key(self, event):
        if self.game_over:
            return
        key = event.keysym.lower()
        # cancel any existing warning timer if user types anything
        if self.warn_after_id:
            self.root.after_cancel(self.warn_after_id)
            self.warn_after_id = None
            self.clear_message()
        if key == "backspace":
            self.backspace()
        elif key == "return":
            self.submit_word()
        elif len(key) == 1 and key in string.ascii_letters:
            self.add_letter(key)

    def add_letter(self, ch):
        if self.game_over:
            return
        ch = ch.lower()
        if self.col >= COLS:
            # do not accept more than 5 letters for the row
            return
        # place letter
        self.grid_letters[self.attempt][self.col] = ch
        lbl = self.labels[self.attempt][self.col]
        lbl.config(text=ch.upper())
        self.col += 1

    def backspace(self):
        if self.game_over:
            return
        if self.col <= 0:
            return
        self.col -= 1
        self.grid_letters[self.attempt][self.col] = ""
        lbl = self.labels[self.attempt][self.col]
        lbl.config(text="")
        # Restore tile bg in case it was colored earlier by mistake
        lbl.config(bg=EMPTY_TILE_BG)

    # --------------------- Message Helpers ---------------------
    def show_message(self, text, duration_ms=None):
        self.msg.config(text=text)
        if duration_ms:
            if self.warn_after_id:
                self.root.after_cancel(self.warn_after_id)
            self.warn_after_id = self.root.after(duration_ms, self.clear_message)

    def clear_message(self):
        self.msg.config(text="")
        self.warn_after_id = None

    # --------------------- Word Checking / Coloring ---------------------
    def submit_word(self):
        if self.game_over:
            return
        current = "".join(self.grid_letters[self.attempt]).lower()
        if len(current) < COLS:
            self.show_message("Too short")
            # auto-clear "Too short" after 1s as well for good UX
            if self.warn_after_id:
                self.root.after_cancel(self.warn_after_id)
            self.warn_after_id = self.root.after(1000, self.clear_message)
            return

        if current not in self.word_list:
            # Word not in list
            self.show_message("Word not found", duration_ms=1000)
            return

        # Check letters with Wordle frequency rules
        target = self.target_word
        result_colors = [GREY] * COLS
        t_counts = {}
        # count letters in target
        for ch in target:
            t_counts[ch] = t_counts.get(ch, 0) + 1
        # first pass: greens
        for i, ch in enumerate(current):
            if target[i] == ch:
                result_colors[i] = GREEN
                t_counts[ch] -= 1
        # second pass: yellows where counts remain
        for i, ch in enumerate(current):
            if result_colors[i] == GREEN:
                continue
            if ch in t_counts and t_counts[ch] > 0:
                result_colors[i] = YELLOW
                t_counts[ch] -= 1
            else:
                result_colors[i] = DARK_GREY

        # apply colors to tiles and update keyboard colors (never downgrade green/yellow)
        for i, color in enumerate(result_colors):
            lbl = self.labels[self.attempt][i]
            lbl.config(bg=color, fg=TEXT_COLOR)
            letter = current[i]
            # update on-screen key
            if letter in self.key_buttons:
                btn = self.key_buttons[letter]
                # Promote key color: green > yellow > grey > default
                cur = btn.cget("bg")
                priority = {GREEN:3, YELLOW:2, DARK_GREY:1, KEY_BG:0, KEY_ACTIVE:0}
                if priority.get(color,0) > priority.get(cur,0):
                    btn.config(bg=color)

        # check win
        if current == target:
            self.show_message("You won! 🏆")
            self.game_over = True
            return

        # next attempt
        self.attempt += 1
        self.col = 0
        if self.attempt >= ROWS:
            self.game_over = True
            self.show_message(f"The word is: {self.target_word.upper()}")

    # --------------------- Reset ---------------------
    def reset_game(self):
        self.target_word = random.choice(self.word_list)
        self.attempt = 0
        self.col = 0
        self.grid_letters = [["" for _ in range(COLS)] for _ in range(ROWS)]
        self.game_over = False
        self.clear_message()
        # reset tiles
        for r in range(ROWS):
            for c in range(COLS):
                lbl = self.labels[r][c]
                lbl.config(text="", bg=EMPTY_TILE_BG, fg=TEXT_COLOR)
        # reset keys
        for k, btn in self.key_buttons.items():
            btn.config(bg=KEY_BG)
        # debug: print("New target:", self.target_word)

# --------------------- Run ---------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = WordleApp(root)
    root.mainloop()
