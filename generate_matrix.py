import wordHandle
import json
import os

def generate_pattern_matrix():
    print("Loading words...")
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Adjust paths to match your folder structure
    with open(os.path.join(base_path, "answers", "allowed_words.txt"), "r") as f:
        allowed = f.read().splitlines()
    with open(os.path.join(base_path, "answers", "answers.txt"), "r") as f:
        answers = allowed

    print(f"Generating Matrix for {len(allowed)} guesses vs {len(answers)} answers...")
    print("This will take about 1-2 minutes.")

    # We map every word to an ID (Index)
    # The matrix will be: matrix[guess_id][answer_id] = pattern_int
    
    # 1. Create Word -> ID Maps
    allowed_map = {word: i for i, word in enumerate(allowed)}
    answers_map = {word: i for i, word in enumerate(answers)}
    
    # 2. Build the Matrix
    # Using a flat list for JSON compatibility (List of Lists)
    matrix = []
    
    # Progress bar logic
    total = len(allowed)
    for i, guess in enumerate(allowed):
        row = []
        for target in answers:
            # Get response as list [0,2,0,1,0]
            resp_list = wordHandle.get_response(guess, target)
            # Convert to a single integer (Base 3) for storage efficiency
            # 0=Grey, 1=Yellow, 2=Green. 
            # e.g., [2,0,0,0,0] -> 2*81 = 162
            val = 0
            for j, digit in enumerate(resp_list):
                val += digit * (3 ** (4 - j))
            row.append(val)
        
        matrix.append(row)
        
        if i % 500 == 0:
            print(f"Processed {i}/{total} words...")

    # 3. Save Data
    output_data = {
        "allowed_words": allowed,
        "answer_words": answers,
        "matrix": matrix
    }
    
    out_path = os.path.join(base_path, "pattern_matrix.json")
    print(f"Saving to {out_path}...")
    with open(out_path, "w") as f:
        json.dump(output_data, f)
    
    print("Done! Matrix generated.")

if __name__ == "__main__":
    generate_pattern_matrix()