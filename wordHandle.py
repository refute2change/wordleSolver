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

# --- Corrected classify_word function ---

def classify_word(guess_list: list[str], answer_list: list[str]):
    """
    Correctly pre-computes the partitions for all guesses.
    
    This is O(N * M) where N = len(guess_list) and M = len(answer_list).
    """
    
    # Initialize the dictionary to hold partitions for *every* guess
    classifications = {guess: [0] * 243 for guess in guess_list}
    
    total_guesses = len(guess_list)
    total_answers = len(answer_list)
    print(f"Starting pre-computation ({total_guesses} guesses, {total_answers} answers)...")

    # Loop 1: Iterate over every possible GUESS
    for i, guess in enumerate(guess_list):
        
        # Loop 2: Iterate over every possible ANSWER
        for secret in answer_list:
            
            # Get the color pattern for this (guess, secret) pair
            response = get_response(guess, secret)
            response_int = response_to_int(response)
            
            # Increment the count for *this guess's* partition
            classifications[guess][response_int] += 1
            
        if (i + 1) % 1000 == 0:
            print(f"  ... processed {i + 1} / {total_guesses} guesses")
            
    print("Pre-computation complete.")
    return classifications