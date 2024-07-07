from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from collections import defaultdict
from dwave.system import EmbeddingComposite, DWaveSampler

app = Flask(__name__)
CORS(app)

os.environ['DWAVE_API_TOKEN'] = 'DEV-e68c4298a3fab85f81c41ed68f40b6ac186a1989'

# Define winning combinations once
WINNING_COMBINATIONS = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Columns
    (0, 4, 8), (2, 4, 6)  # Diagonals
]

def create_qubo_for_single_move(board):
    linear = {}
    quadratic = defaultdict(int)
    penalty = 1

    # Encourage selecting an empty cell
    for i in range(9):
        if board[i] == '':
            linear[i] = -1

    # Penalize selecting multiple cells
    for i in range(9):
        if board[i] == '':
            for j in range(i + 1, 9):
                if board[j] == '':
                    quadratic[(i, j)] += penalty

    for combo in WINNING_COMBINATIONS:
        empty_cells = [i for i in combo if board[i] == '']
        if len(empty_cells) == 1:
            if board[empty_cells[0]] == 'O':
                linear[empty_cells[0]] -= 6  # Increase the penalty reduction for completing a line with 'O'

    # Penalize 'X' completing a line
    for combo in WINNING_COMBINATIONS:
        empty_cells = [i for i in combo if board[i] == '']
        if len(empty_cells) == 1:
            if all(board[i] == 'X' for i in combo if i != empty_cells[0]):
                linear[empty_cells[0]] -= 100  # Encourage penalty to block 'X'

    return {'linear': linear, 'quadratic': quadratic}

def solve_qubo(qubo):
    qubo_matrix = {(i, j): qubo['quadratic'].get((i, j), 0) for i in qubo['linear'] for j in qubo['linear']}
    for i in qubo['linear']:
        qubo_matrix[(i, i)] = qubo['linear'][i]

    sampler = EmbeddingComposite(DWaveSampler())
    response = sampler.sample_qubo(qubo_matrix, num_reads=100)
    
    solution = response.first.sample
    solution_index = [k for k, v in solution.items() if v == 1]
    return solution_index[0] if solution_index else None

def check_game_status(board):
    for condition in WINNING_COMBINATIONS:
        a, b, c = condition
        if board[a] == board[b] == board[c] and board[a] != '':
            return True  # Game has been won
    if '' not in board:
        return True  # Board is full (draw)
    return False  # Game is still ongoing

@app.route('/get_move', methods=['POST'])
def get_move():
    board = request.json['board']
    if check_game_status(board):
        return jsonify({'move': None})

    flattened_board = board
    qubo = create_qubo_for_single_move(flattened_board)
    best_move = solve_qubo(qubo)
    return jsonify({'move': best_move})

if __name__ == '__main__':
    app.run(debug=True, port=8000)
