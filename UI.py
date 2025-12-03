import tkinter as tk
from tkinter import font
import game
import ucs_solver, bfs_solver
import dfs_solver
import heuristic_minimax
import math
import threading  # <--- Added to handle background tasks


# --- Configuration & Colors ---
COLOR_BG_MAIN = "#E3C08D"
COLOR_BTN_NEW_BG = "#E7AB56"
COLOR_BTN_NEW_FG = "#FFFFFF"
COLOR_BOX_EMPTY_BG = "#FCE8CC"
COLOR_BOX_EMPTY_FG = "#605C56"
COLOR_BOX_ABSENT = "#605C56"
COLOR_BOX_PRESENT = "#E8E53F"
COLOR_BOX_CORRECT = "#5A9C36"
COLOR_ERROR_TEXT = "#CB2A2A"
COLOR_SUPPORT_PANEL = "#E7AB56"

# Support Panel Specifics
COLOR_SUP_BTN_BG = "#FCE8CC"
COLOR_SUP_BTN_FG = "#605C56"
COLOR_SUP_BTN_ACTIVE_BG = "#5A9C36"
COLOR_SUP_BTN_ACTIVE_FG = "#FFFFFF"
COLOR_SUP_INPUT_BG = "#FCE8CC"

KEYBOARD_LAYOUT = [
    "QWERTYUIOP",
    "ASDFGHJKL",
    "ZXCVBNM"
]

class WordleUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Wordle")
        self.root.geometry("1100x700")
        self.root.configure(bg=COLOR_BG_MAIN)
        self.root.resizable(False, False)
        self.strategy = {}

        # Initialize Game Backend
        self.game = game.Game()
        self.game.new_game()

        ucs_solver.load_resources()
        bfs_solver.load_resources()
        self.ucs = ucs_solver.load_strategy()
        self.bfs = bfs_solver.load_strategy()

        # UI State
        self.last_message = ""
        self.show_support_details = False
        
        # Support Default Values
        self.rec_word = "CRACK"
        self.selected_algo = "DFS" 
        self.stat_runtime = "3"
        self.stat_space = "2"

        # Setup Fonts
        self.font_key = font.Font(family="Helvetica", size=12, weight="bold")
        self.font_box = font.Font(family="Helvetica", size=24, weight="bold")
        self.font_btn = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_err = font.Font(family="Helvetica", size=12, weight="normal")

        # Main Canvas
        self.canvas = tk.Canvas(
            root, width=1000, height=600, 
            bg=COLOR_BG_MAIN, highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Bind Inputs
        self.root.bind("<Key>", self.handle_keypress)
        self.canvas.bind("<Button-1>", self.handle_click)

        # Initial Draw
        self.UI_update()

    # --- Threading Helper ---
    def run_bot_calculation(self):
        """
        Runs the heavy BFS strategy lookup/regeneration in a separate thread
        to keep the UI responsive.
        """
        def task():
            # This is the slow part (regenerating the tree if off-script)
            # self.rec_word = bfs_new.use_strategy_map(self.game.response, self.strategy)
            if (self.selected_algo == "BFS"):
                self.rec_word = bfs_solver.get_next_guess(self.game.response, self.bfs) # Handling BFS
            elif (self.selected_algo == "UCS"):
                self.rec_word = ucs_solver.get_next_guess(self.game.response, self.ucs) # Handling UCS
            elif (self.selected_algo == "DFS"):
                self.rec_word = dfs_solver.get_next_guess(self.game.response) # Handling DFS
            else:
                self.rec_word = heuristic_minimax.get_next_guess(self.game.response) # Handling A*

            if self.rec_word is None:
                self.rec_word = ""
            else:
                self.rec_word = self.rec_word.upper()
            
            # Since we are in a thread, we use print() for now.
            # If you want to update the UI (e.g. self.rec_word), you must use 
            # self.root.after() to schedule it on the main thread.
            print(f"Bot Suggestion: {self.rec_word}")
            self.UI_update()
            
            # Example of how to update UI safely from thread:
            # self.root.after(0, lambda: self.update_recommendation(suggestion))

        # Create and start the thread
        # daemon=True ensures the thread dies if the main app is closed
        thread = threading.Thread(target=task, daemon=True)
        thread.start()

    def draw_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]
        return self.canvas.create_polygon(points, **kwargs, smooth=True)

    def draw_button(self, x, y, w, h, text, bg, fg, tag, radius=25):
        self.draw_rounded_rect(x, y, x + w, y + h, radius, fill=bg, tags=tag)
        self.canvas.create_text(x + w/2, y + h/2, text=text, fill=fg, font=self.font_btn, tags=tag)

    def UI_update(self):
        self.canvas.delete("all")
        data = self.game.response
        
        # 1. New Game Button
        self.draw_button(40, 40, 140, 50, "New game", COLOR_BTN_NEW_BG, COLOR_BTN_NEW_FG, "btn_new_game")

        # 2. Draw Game Grid
        start_x = 220
        start_y = 50
        box_size = 65
        gap = 10
        
        progress = data["progress"]
        responses = data["response"]
        
        for row in range(6):
            word = progress[row] if row < len(progress) else ""
            row_colors = []
            if row < len(responses):
                for code in responses[row]:
                    if code == 2: row_colors.append(COLOR_BOX_CORRECT)
                    elif code == 1: row_colors.append(COLOR_BOX_PRESENT)
                    else: row_colors.append(COLOR_BOX_ABSENT)
            
            for col in range(5):
                bx = start_x + col * (box_size + gap)
                by = start_y + row * (box_size + gap)
                
                bg_color = COLOR_BOX_EMPTY_BG
                text_color = COLOR_BOX_EMPTY_FG
                
                if row < len(responses):
                    bg_color = row_colors[col]
                    text_color = "#FFFFFF"
                
                self.draw_rounded_rect(bx, by, bx+box_size, by+box_size, 25, fill=bg_color)
                
                char = word[col] if col < len(word) else ""
                self.canvas.create_text(bx + box_size/2, by + box_size/2, text=char.upper(), fill=text_color, font=self.font_box)

        # 3. Error Message
        if self.last_message and self.last_message not in ["Next Turn", "Win", "Loss"]:
             self.canvas.create_text(400, 520 - 15, text=self.last_message, fill=COLOR_ERROR_TEXT, font=self.font_err)

        # 4. Draw Keyboard
        kb_start_y = 530
        key_w = 40
        key_h = 50
        key_gap = 5
        
        key_colors = {}
        for r_idx, resp_row in enumerate(responses):
            word = progress[r_idx]
            for c_idx, code in enumerate(resp_row):
                char = word[c_idx].upper()
                current_prio = key_colors.get(char, -1)
                if code > current_prio:
                    key_colors[char] = code

        for i, row_keys in enumerate(KEYBOARD_LAYOUT):
            row_w = len(row_keys) * (key_w + key_gap)
            start_x_kb = 400 - (row_w / 2)
            
            for j, char in enumerate(row_keys):
                kx = start_x_kb + j * (key_w + key_gap)
                ky = kb_start_y + i * (key_h + key_gap)
                
                k_bg = COLOR_BOX_EMPTY_BG
                k_fg = COLOR_BOX_EMPTY_FG
                
                if char in key_colors:
                    code = key_colors[char]
                    k_fg = "#FFFFFF"
                    if code == 2: k_bg = COLOR_BOX_CORRECT
                    elif code == 1: k_bg = COLOR_BOX_PRESENT
                    else: k_bg = COLOR_BOX_ABSENT
                
                tag = f"key_{char}"
                self.draw_rounded_rect(kx, ky, kx+key_w, ky+key_h, 10, fill=k_bg, tags=tag)
                self.canvas.create_text(kx+key_w/2, ky+key_h/2, text=char, fill=k_fg, font=self.font_key, tags=tag)

        # Special Keys
        enter_x = 400 + (len(KEYBOARD_LAYOUT[2]) * (key_w + key_gap))/2 + 10
        enter_y = kb_start_y + 2 * (key_h + key_gap)
        self.draw_rounded_rect(enter_x, enter_y, enter_x+70, enter_y+key_h, 10, fill=COLOR_BOX_EMPTY_BG, tags="key_enter")
        self.canvas.create_text(enter_x+35, enter_y+key_h/2, text="Enter", fill=COLOR_BOX_EMPTY_FG, font=self.font_key, tags="key_enter")

        back_x = 400 - (len(KEYBOARD_LAYOUT[2]) * (key_w + key_gap))/2 - 60
        self.draw_rounded_rect(back_x, enter_y, back_x+50, enter_y+key_h, 10, fill=COLOR_BOX_EMPTY_BG, tags="key_back")
        self.canvas.create_text(back_x+25, enter_y+key_h/2, text="⌫", fill=COLOR_BOX_EMPTY_FG, font=self.font_key, tags="key_back")


        # 5. Right Side Panel
        panel_x = 680
        panel_y = 20
        panel_w = 300
        panel_h = 560
        
        self.draw_rounded_rect(panel_x, panel_y, panel_x+panel_w, panel_y+panel_h, 25, fill=COLOR_SUPPORT_PANEL)

        if not self.show_support_details:
            btn_y = panel_y + panel_h / 2 - 25
            self.draw_button(panel_x + 30, btn_y, 240, 50, "SUPPORT", COLOR_SUP_BTN_BG, COLOR_SUP_BTN_FG, "btn_support_toggle", radius=25)
        else:
            cx = panel_x + panel_w / 2

            if (data["is_game_over"] == False):
                if (self.selected_algo == "BFS"):
                    self.rec_word = bfs_solver.get_next_guess(self.game.response, self.bfs).upper() # Handling BFS
                elif (self.selected_algo == "UCS"):
                    self.rec_word = ucs_solver.get_next_guess(self.game.response, self.ucs).upper() # Handling UCS
                elif (self.selected_algo == "DFS"):
                    self.rec_word = dfs_solver.get_next_guess(self.game.response).upper() # Handling DFS
                else:
                    self.rec_word = heuristic_minimax.get_next_guess(self.game.response).upper() # Handling A*
            
            self.canvas.create_text(cx, panel_y + 40, text="RECOMMENDATION", fill="#FFFFFF", font=self.font_btn)
            self.draw_button(panel_x + 30, panel_y + 60, 240, 60, self.rec_word, COLOR_SUP_BTN_BG, COLOR_SUP_BTN_FG, "btn_crack", radius=15)
            
            self.canvas.create_text(cx, panel_y + 160, text="ALGORITHMS", fill="#FFFFFF", font=self.font_btn)
            algos = ["DFS", "BFS", "UCS", "A*"]
            
            ax_start = panel_x + 30
            ay_start = panel_y + 190
            aw, ah = 110, 55
            gap_a = 20
            
            for i, algo in enumerate(algos):
                r = i // 2
                c = i % 2
                ax = ax_start + c*(aw+gap_a)
                ay = ay_start + r*(ah+gap_a)
                
                bg = COLOR_SUP_BTN_ACTIVE_BG if algo == self.selected_algo else COLOR_SUP_BTN_BG
                fg = COLOR_SUP_BTN_ACTIVE_FG if algo == self.selected_algo else COLOR_SUP_BTN_FG
                
                self.draw_button(ax, ay, aw, ah, algo, bg, fg, f"algo_{algo}", radius=15)

            stats_y = panel_y + 340
            self.canvas.create_text(cx, stats_y, text="STATISTICS", fill="#FFFFFF", font=self.font_btn)
            
            self.canvas.create_text(panel_x+30, stats_y + 40, text="Run time (ms)", fill="#FFFFFF", font=self.font_btn, anchor="w")
            self.draw_rounded_rect(panel_x+30, stats_y+60, panel_x+270, stats_y+115, 15, fill=COLOR_SUP_INPUT_BG)
            
            self.canvas.create_text(panel_x+30, stats_y + 130, text="Space used (MB)", fill="#FFFFFF", font=self.font_btn, anchor="w")
            self.draw_rounded_rect(panel_x+30, stats_y+150, panel_x+270, stats_y+205, 15, fill=COLOR_SUP_INPUT_BG)

        # 6. Win/Loss Overlay
        if data["is_game_over"]:
            self.draw_game_over(False if len(data["response"]) == 0 else (data["response"][-1] == [2,2,2,2,2]))

    def draw_game_over(self, is_win):
        msg = "YOU WIN" if is_win else "YOU LOSE"
        word_msg = "The correct word was " + self.game.state.answer.upper()
        color = COLOR_BTN_NEW_BG if is_win else COLOR_BOX_ABSENT
        
        self.canvas.create_rectangle(0, 0, 1200, 700, fill="#FFFFFF", stipple="gray50")
        
        cx, cy = 550, 350
        self.canvas.create_text(cx, cy - 30, text=msg, fill=color, font=("Helvetica", 40, "bold"))
        if (is_win == False):
            self.canvas.create_text(cx, cy + 15, text=word_msg, fill = color, font = ("Helvetica", 20, "bold"))
        self.draw_button(cx - 70, cy + 30, 140, 50, "New game", COLOR_BTN_NEW_BG, COLOR_BTN_NEW_FG, "btn_new_game_over")

    # --- Interaction Handlers ---

    def handle_keypress(self, event):
        if self.game.response["is_game_over"]:
            return

        key = event.keysym.upper()
        if len(key) == 1 and key.isalpha():
            self.game.add_letter(key)
        elif key == "BACKSPACE":
            self.game.remove_letter()
        elif key == "RETURN":
            self.submit_action()
            # Changed to threaded call
            if self.show_support_details:
                self.run_bot_calculation()
        
        self.UI_update()

    def handle_click(self, event):
        x, y = event.x, event.y
        items = self.canvas.find_closest(x, y)
        tags = self.canvas.gettags(items[0])
        
        if not tags: return
        tag = tags[0]
        
        if "btn_new_game" in tag or "btn_new_game_over" in tag:
            self.game.new_game()
            self.last_message = ""
            self.show_support_details = False
            self.UI_update()
            return

        if "btn_support_toggle" in tag:
            self.show_support_details = True
            self.run_bot_calculation()
            self.UI_update()
            return
            
        if tag.startswith("algo_"):
            algo_name = tag.split("_")[1]
            self.selected_algo = algo_name
            self.UI_update()
            return

        if self.game.response["is_game_over"]: return

        if tag.startswith("key_"):
            val = tag.split("_")[1]
            if val == "enter":
                self.submit_action()
                # Changed to threaded call
                if self.show_support_details:
                    self.run_bot_calculation()
            elif val == "back":
                self.game.remove_letter()
            elif len(val) == 1:
                self.game.add_letter(val)
            self.UI_update()

    def submit_action(self):
        result = self.game.submit()
        if result == "Not in Word List":
            self.last_message = "The word does not exist!"
        elif result == "Too Short":
            self.last_message = "Not enough letters"
        elif result == "Already Guessed":
            self.last_message = "Word already guessed"
        elif result in ["Win", "Loss"]:
            self.last_message = result
        else:
            self.last_message = ""

def start():
    root = tk.Tk()
    app = WordleUI(root)
    root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = WordleUI(root)
    root.mainloop()