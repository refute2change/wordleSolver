import math
from collections import defaultdict

# --- Your Helper Functions (Fixed get_response) ---

def get_response(word: str, target: str) -> list[int]:
    """
    Calculates the Wordle color pattern.
    0 = Grey, 1 = Yellow, 2 = Green
    """
    response = [0] * 5  # Start with all Grey
    target_counts = defaultdict(int)
    
    # 1. First pass: Find Greens (2)
    for i in range(5):
        if word[i] == target[i]:
            response[i] = 2
        else:
            target_counts[target[i]] += 1
            
    # 2. Second pass: Find Yellows (1)
    for i in range(5):
        if response[i] == 0:  # Only check Grey letters
            if word[i] in target_counts and target_counts[word[i]] > 0:
                response[i] = 1
                target_counts[word[i]] -= 1
                
    return response

def response_to_str(response: list[int]) -> str:
    ret = ""
    for i in response:
        if i == 2:
            ret += "G"
        elif i == 1:
            ret += "Y"
        elif i == 0:
            ret += "B"
    return ret

def response_to_int(response: list[int]) -> int:
    result = 0
    for i in range(5):
        result += response[i] * (3 ** (4 - i))
    return result