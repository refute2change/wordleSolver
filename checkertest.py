import dfs_solver
import wordHandle
import random

words = dfs_solver.read_wordle_words("allowed_words.txt")
final_words = dfs_solver.read_wordle_words("answers.txt")
flag = True
for word1 in words:
    for word2 in final_words:
        if dfs_solver.check_wordle_guess(word1, word2) != wordHandle.response_to_str(wordHandle.get_response(word1, word2)):
            print(f"Find different cases of {word1}, {word2}, with dfs_solver got the result {dfs_solver.check_wordle_guess(word1, word2)}, while wordHandle = {wordHandle.response_to_str(wordHandle.get_response(word1, word2))}")
            flag = False
            break
if flag:
    print("Okay")
else:
    print("Not okay :(")