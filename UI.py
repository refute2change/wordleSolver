import tkinter as tk
from tkinter import font
import game
import math

# --- Configuration & Colors ---
COLOR_BG_MAIN = "#E3C08D"  # Matches the general tan background
COLOR_BTN_NEW_BG = "#E7AB56"
COLOR_BTN_NEW_FG = "#FFFFFF"
COLOR_BOX_EMPTY_BG = "#FCE8CC"
COLOR_BOX_EMPTY_FG = "#605C56"
COLOR_BOX_ABSENT = "#605C56"
COLOR_BOX_PRESENT = "#E8E53F"
COLOR_BOX_CORRECT = "#5A9C36"
COLOR_ERROR_TEXT = "#CB2A2A"
COLOR_SUPPORT_PANEL = "#E7AB56" # Right side background

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

        # Initialize Game Backend
        self.game = game.Game()
        self.game.new_game()

        # UI State
        self.last_message = ""
        self.show_support_details = False
        
        # Support Default Values
        self.rec_word = "CRACK"
        self.selected_algo = "A*" # Default 4th option
        self.stat_runtime = "3"
        self.stat_space = "2"

        # Setup Fonts
        self.font_key = font.Font(family="Helvetica", size=12, weight="bold")
        self.font_box = font.Font(family="Helvetica", size=24, weight="bold")
        self.font_btn = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_err = font.Font(family="Helvetica", size=12, weight="normal")

        # Main Canvas for drawing everything (Custom UI requires flexibility)
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

    def draw_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Helper to draw rounded rectangles on Canvas"""
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
        """
        Main render loop. 
        Fetches data from game.state and redraws the screen.
        """
        self.canvas.delete("all")
        data = self.game.response
        
        # 1. New Game Button (Top Left)
        self.draw_button(40, 40, 140, 50, "New game", COLOR_BTN_NEW_BG, COLOR_BTN_NEW_FG, "btn_new_game")

        # 2. Draw Game Grid (Center)
        # Grid settings
        start_x = 220
        start_y = 50
        box_size = 65
        gap = 10
        
        progress = data["progress"] # List of strings, e.g. ["TRICK", "AS"]
        responses = data["response"] # List of lists of ints
        
        for row in range(6):
            # Get the word for this row if it exists
            word = progress[row] if row < len(progress) else ""
            
            # Get colors if this row has been submitted
            row_colors = []
            if row < len(responses):
                # Map backend response to colors
                # Assuming standard: 2=Green, 1=Yellow, 0=Gray (or similar mapping)
                # Based on prompt: 
                # existed & right_position (Green) -> 2
                # existed & not_right_position (Yellow) -> 1
                # not_existed (Dark Gray) -> 0
                for code in responses[row]:
                    if code == 2: row_colors.append(COLOR_BOX_CORRECT)
                    elif code == 1: row_colors.append(COLOR_BOX_PRESENT)
                    else: row_colors.append(COLOR_BOX_ABSENT)
            
            for col in range(5):
                bx = start_x + col * (box_size + gap)
                by = start_y + row * (box_size + gap)
                
                # Determine Color
                bg_color = COLOR_BOX_EMPTY_BG
                text_color = COLOR_BOX_EMPTY_FG
                
                if row < len(responses):
                    bg_color = row_colors[col]
                    text_color = "#FFFFFF" # Submitted text is white
                
                # Draw Box
                self.draw_rounded_rect(bx, by, bx+box_size, by+box_size, 25, fill=bg_color)
                
                # Draw Letter
                char = word[col] if col < len(word) else ""
                self.canvas.create_text(bx + box_size/2, by + box_size/2, text=char.upper(), fill=text_color, font=self.font_box)

        # 3. Error Message
        if self.last_message and self.last_message not in ["Next Turn", "Win", "Loss"]:
             self.canvas.create_text(400, 520 - 15, text=self.last_message, fill=COLOR_ERROR_TEXT, font=self.font_err)

        # 4. Draw Keyboard (Bottom)
        kb_start_y = 530
        key_w = 40
        key_h = 50
        key_gap = 5
        
        # Calculate keyboard key colors based on game history
        key_colors = {} # char -> color_code
        for r_idx, resp_row in enumerate(responses):
            word = progress[r_idx]
            for c_idx, code in enumerate(resp_row):
                char = word[c_idx].upper()
                current_prio = key_colors.get(char, -1)
                # Priority: Green (2) > Yellow (1) > Gray (0)
                if code > current_prio:
                    key_colors[char] = code

        for i, row_keys in enumerate(KEYBOARD_LAYOUT):
            row_w = len(row_keys) * (key_w + key_gap)
            start_x_kb = 400 - (row_w / 2) # Center align relative to grid center approx
            
            for j, char in enumerate(row_keys):
                kx = start_x_kb + j * (key_w + key_gap)
                ky = kb_start_y + i * (key_h + key_gap)
                
                # Determine Color
                k_bg = COLOR_BOX_EMPTY_BG
                k_fg = COLOR_BOX_EMPTY_FG
                
                if char in key_colors:
                    code = key_colors[char]
                    k_fg = "#FFFFFF"
                    if code == 2: k_bg = COLOR_BOX_CORRECT
                    elif code == 1: k_bg = COLOR_BOX_PRESENT
                    else: k_bg = COLOR_BOX_ABSENT
                
                # Draw Key
                tag = f"key_{char}"
                self.draw_rounded_rect(kx, ky, kx+key_w, ky+key_h, 10, fill=k_bg, tags=tag)
                self.canvas.create_text(kx+key_w/2, ky+key_h/2, text=char, fill=k_fg, font=self.font_key, tags=tag)

        # Special Keys (Backspace, Enter)
        # Simplified placement for visuals
        # Enter
        enter_x = 400 + (len(KEYBOARD_LAYOUT[2]) * (key_w + key_gap))/2 + 10
        enter_y = kb_start_y + 2 * (key_h + key_gap)
        self.draw_rounded_rect(enter_x, enter_y, enter_x+70, enter_y+key_h, 10, fill=COLOR_BOX_EMPTY_BG, tags="key_enter")
        self.canvas.create_text(enter_x+35, enter_y+key_h/2, text="Enter", fill=COLOR_BOX_EMPTY_FG, font=self.font_key, tags="key_enter")

        # Backspace
        back_x = 400 - (len(KEYBOARD_LAYOUT[2]) * (key_w + key_gap))/2 - 60
        self.draw_rounded_rect(back_x, enter_y, back_x+50, enter_y+key_h, 10, fill=COLOR_BOX_EMPTY_BG, tags="key_back")
        self.canvas.create_text(back_x+25, enter_y+key_h/2, text="⌫", fill=COLOR_BOX_EMPTY_FG, font=self.font_key, tags="key_back")


        # 5. Right Side Panel (Support)
        panel_x = 680
        panel_y = 20
        panel_w = 300
        panel_h = 560
        
        # Draw Panel Background
        self.draw_rounded_rect(panel_x, panel_y, panel_x+panel_w, panel_y+panel_h, 25, fill=COLOR_SUPPORT_PANEL)

        if not self.show_support_details:
            # Just the toggle button
            btn_y = panel_y + panel_h / 2 - 25
            self.draw_button(panel_x + 30, btn_y, 240, 50, "SUPPORT", COLOR_SUP_BTN_BG, COLOR_SUP_BTN_FG, "btn_support_toggle", radius=25)
        else:
            # Full Interface
            cx = panel_x + panel_w / 2
            
            # Recommendation
            self.canvas.create_text(cx, panel_y + 40, text="RECOMMENDATION", fill="#FFFFFF", font=self.font_btn)
            self.draw_button(panel_x + 30, panel_y + 60, 240, 60, self.rec_word, COLOR_SUP_BTN_BG, COLOR_SUP_BTN_FG, "btn_crack", radius=15)
            
            # Algorithms
            self.canvas.create_text(cx, panel_y + 160, text="ALGORITHMS", fill="#FFFFFF", font=self.font_btn)
            algos = ["DFS", "BFS", "UCS", "A*"]
            
            # 2x2 Grid for buttons
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

            # Statistics
            stats_y = panel_y + 340
            self.canvas.create_text(cx, stats_y, text="STATISTICS", fill="#FFFFFF", font=self.font_btn)
            
            # Run time
            self.canvas.create_text(panel_x+30, stats_y + 40, text="Run time (ms)", fill="#FFFFFF", font=self.font_btn, anchor="w")
            self.draw_rounded_rect(panel_x+30, stats_y+60, panel_x+270, stats_y+115, 15, fill=COLOR_SUP_INPUT_BG)
            # Placeholder text would go here
            
            # Space used
            self.canvas.create_text(panel_x+30, stats_y + 130, text="Space used (MB)", fill="#FFFFFF", font=self.font_btn, anchor="w")
            self.draw_rounded_rect(panel_x+30, stats_y+150, panel_x+270, stats_y+205, 15, fill=COLOR_SUP_INPUT_BG)

        # 6. Win/Loss Overlay
        if data["is_game_over"]:
            self.draw_game_over(data["progress"][-1] == data["answer"])

    def draw_game_over(self, is_win):
        # Semi-transparent Overlay (simulated with stipple or solid fill blocking clicks)
        # Using a solid rectangle centered to block view as per "Blur" effect request
        # Actually, Tkinter doesn't do blur. We will draw a semi-transparent box or just a solid box.
        # Based on instruction: "print out YOU WIN/LOSE and New_game button below"
        
        # Color based on result
        msg = "YOU WIN" if is_win else "YOU LOSE"
        color = COLOR_BTN_NEW_BG if is_win else COLOR_BOX_ABSENT
        
        # Overlay covering grid + keyboard
        self.canvas.create_rectangle(0, 0, 1200, 700, fill="#FFFFFF", stipple="gray50")
        
        cx, cy = 550, 350 # Center of Game Area
        
        self.canvas.create_text(cx, cy - 30, text=msg, fill=color, font=("Helvetica", 40, "bold"))
        
        # Re-draw new game button in center for this screen? 
        # The prompt says "and the New_game button below".
        self.draw_button(cx - 70, cy + 20, 140, 50, "New game", COLOR_BTN_NEW_BG, COLOR_BTN_NEW_FG, "btn_new_game_over")

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
        
        self.UI_update()

    def handle_click(self, event):
        x, y = event.x, event.y
        
        # Check Canvas Tags at click location
        items = self.canvas.find_closest(x, y)
        tags = self.canvas.gettags(items[0])
        
        if not tags: return
        
        tag = tags[0]
        
        # 1. New Game
        if "btn_new_game" in tag or "btn_new_game_over" in tag:
            self.game.new_game()
            self.last_message = ""
            self.show_support_details = False
            self.UI_update()
            return

        # 2. Support Toggle
        if "btn_support_toggle" in tag:
            self.show_support_details = True
            self.UI_update()
            return
            
        # 3. Algorithms Selection
        if tag.startswith("algo_"):
            algo_name = tag.split("_")[1]
            if algo_name == "A*": algo_name = "A*" # fix split issue if any
            self.selected_algo = algo_name
            self.UI_update()
            return

        # 4. Virtual Keyboard
        if self.game.response["is_game_over"]: return

        if tag.startswith("key_"):
            val = tag.split("_")[1]
            if val == "enter":
                self.submit_action()
            elif val == "back":
                self.game.remove_letter()
            elif len(val) == 1:
                self.game.add_letter(val)
            self.UI_update()

    def submit_action(self):
        # Call backend submit
        result = self.game.submit()
        # Map result to message
        if result == "Not in Word List":
            self.last_message = "The word does not exist!"
        elif result == "Too Short":
            self.last_message = "Not enough letters"
        elif result in ["Win", "Loss"]:
            self.last_message = result # UI handles game over flag
        else:
            self.last_message = ""

if __name__ == "__main__":
    root = tk.Tk()
    app = WordleUI(root)
    root.mainloop()