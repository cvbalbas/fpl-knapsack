from players import create_players_from_csv, Player
import itertools
import copy
from tqdm import tqdm
from collections import OrderedDict
import numpy as np
import csv
import os
import pandas as pd

# from celery_config import run_knapsack_algorithm

# my_flask_app/app.py
from flask import Flask, request, jsonify, render_template


app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/printTable', methods=['POST'])
def printTable():
    # if 'file' not in request.files:
    #     return jsonify({'message': 'No file part'}), 400
    
    # file = request.files['file']
    
    # if file.filename == '':
    #     return jsonify({'message': 'No selected file'}), 400
    
    # if file:
    # filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    # file.save(filepath)
    
    # Read the CSV file into a DataFrame
    # df = pd.read_csv(filepath)
    filepath = "uploads/fpl_player.csv"
    players = []
    with open(filepath, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        # print(*reader)
        for row in reader:
            # print(*row)
            name = row['name']
            price = float(row['price'])
            points = float(row['score'])
            position = row['position']
            id = int(row['id'])
            team = row['team']
            # Create a Player instance and append to the list
            player = Player(name=name, price=price, points=points, position=position, id=id, team=team)
            players.append(player)
            # print(player)
    
    # Convert the DataFrame to a JSON object
    # csv_data = df.to_dict(orient='records')
    # print(csv_data)
    # Get top 50 players from each position   
    # top_players_by_position = get_top_players_by_position(players, top_n=50)
    # merged_top_players = []
    # for top_players in top_players_by_position.values():
    #     merged_top_players.extend(top_players)

    # Sort the merged list by points in descending order
    sorted_merged_top_players = sorted(players, key=lambda player: player.name, reverse=False)
    # sorted_playersDB = sorted(players, key=lambda player: player.points, reverse=True)
    players_dict = [player.to_dict() for player in sorted_merged_top_players]

    print(*players_dict)
    return jsonify({'message': 'File successfully uploaded', 'players': players_dict}), 200

@app.route('/run_knapsack', methods=['POST'])
def run_knapsack():
    data = request.get_json()
    formation = int(data['formation']) 
    budget = int(data['budget'])
    # filename = data['filename'] #Save as a unique filename and that's what we pass
    players_data = data['selectedPlayers']
    # print(players_data)
    playersDB = [Player(**player) for player in players_data]
    # for player in playersDB:
    #     print(player)

    formations = [
    # possible_formations = [
            [3, 4, 3],
            [3, 5, 2],
            [4, 3, 3],
            [4, 4, 2],
            [4, 5, 1],
            [5, 3, 2],
            [5, 4, 1],
        ]
    possible_formations = [formations[formation]]
    
    # playersDB = create_players_from_csv(filename)
    # print(*playersDB[:150])
    
    # Get top 50 players from each position   
    # top_players_by_position = get_top_players_by_position(playersDB, top_n=10)
    # merged_top_players = []
    # for top_players in top_players_by_position.values():
    #     merged_top_players.extend(top_players)

    # Sort the merged list by points in descending order
    # sorted_merged_top_players = sorted(merged_top_players, key=lambda player: player.points, reverse=True)
    # sorted_playersDB = sorted(playersDB, key=lambda player: player.points, reverse=True)
    # print(*sorted_playersDB[:100])

    # print("Data successfully opened fpl_players.csv and loaded into playersDB")
    formation =  best_full_teams(playersDB, possible_formations, budget)
    # print(formation)
    # best_players = formation[0][2]
    # best_players_str = ",".join(str(element) for element in best_players)
    # # print(best_players_str)

    formation_str = ",".join(str(element) for element in formation[0][0])
    data = []
    for best_team in formation:
        best_players = best_team[2]
        best_players_str = ",".join(str(element) for element in best_players)
        formation_str = ",".join(str(element) for element in best_team[0])
        best_team_data = {
            "bestPlayers": best_players_str,
            "formation": formation_str,
            "score": best_team[1]
        }
        data.append(best_team_data)

    return data

def best_full_teams(players_list, formations, budget):
    formation_score_players = []

    for formation in formations:
        players_points, players_prices, players_comb_indexes = players_preproc(
            players_list, formation)

        score, comb_result_indexes = knapsack_multichoice_onepick(
            players_prices, players_points, budget)

        result_indexes = []
        for comb_index in comb_result_indexes:
            for winning_i in players_comb_indexes[comb_index[0]][comb_index[1]]:
                result_indexes.append(winning_i)

        result_players = []
        for res_index in result_indexes:
            result_players.append(players_list[res_index])

        formation_score_players.append((formation, score, result_players))

        print("With formation " + str(formation) + ": " + str(score))
        for best_player in result_players:
            print(best_player)
        print()
        print()

    formation_score_players_by_score = sorted(formation_score_players,
                                            key=lambda tup: tup[1],
                                            reverse=True)
    for final_formation_score in formation_score_players_by_score:
        print((final_formation_score[0], final_formation_score[1]))

    return formation_score_players


def players_preproc(players_list, formation):
    max_gk = 1
    max_def = formation[0]
    max_mid = formation[1]
    max_att = formation[2]

    gk_values, gk_weights, gk_indexes = generate_group(players_list, "GK")
    gk_comb_values, gk_comb_weights, gk_comb_indexes = group_preproc(gk_values, gk_weights, gk_indexes, max_gk)

    def_values, def_weights, def_indexes = generate_group(players_list, "DEF")
    def_comb_values, def_comb_weights, def_comb_indexes = group_preproc(
        def_values, def_weights, def_indexes, max_def)

    mid_values, mid_weights, mid_indexes = generate_group(players_list, "MID")
    mid_comb_values, mid_comb_weights, mid_comb_indexes = group_preproc(
        mid_values, mid_weights, mid_indexes, max_mid)

    att_values, att_weights, att_indexes = generate_group(players_list, "ATT")
    att_comb_values, att_comb_weights, att_comb_indexes = group_preproc(
        att_values, att_weights, att_indexes, max_att)

    result_comb_values = [gk_comb_values, def_comb_values, mid_comb_values,
                        att_comb_values]
    result_comb_weights = [gk_comb_weights, def_comb_weights, mid_comb_weights,
                            att_comb_weights]
    result_comb_indexes = [gk_comb_indexes, def_comb_indexes, mid_comb_indexes,
                            att_comb_indexes]

    return result_comb_values, result_comb_weights, result_comb_indexes


def generate_group(full_list, group):
    group_values = []
    group_weights = []
    group_indexes = []
    for i, item in enumerate(full_list):
        if item.position == group:
            group_values.append(float(item.points))
            group_weights.append(int(item.price))
            group_indexes.append(i)
    return group_values, group_weights, group_indexes


def group_preproc(group_values, group_weights, initial_indexes, r):
    comb_values = list(itertools.combinations(group_values, r))
    comb_weights = list(itertools.combinations(group_weights, r))
    comb_indexes = list(itertools.combinations(initial_indexes, r))

    group_comb_values = []
    for value_combinations in comb_values:
        values_added = sum(list(value_combinations))
        group_comb_values.append(values_added)

    group_comb_weights = []
    for weight_combinations in comb_weights:
        weights_added = sum(list(weight_combinations))
        group_comb_weights.append(weights_added)

    return group_comb_values, group_comb_weights, comb_indexes

def knapsack_multichoice_onepick(weights, values, max_weight, verbose=False):
    if len(weights) == 0:
        return 0

    last_array = [-1 for _ in range(max_weight + 1)]
    last_path = [[] for _ in range(max_weight + 1)]
    for i in range(len(weights[0])):
        if weights[0][i] < max_weight:
            if last_array[weights[0][i]] < values[0][i]:
                last_array[weights[0][i]] = values[0][i]
                last_path[weights[0][i]] = [(0, i)]
            # last_array[weight[0][i]] = max(last_array[weight[0][i]], value[0][i])

    # Calculate the total number of operations based on each item j in each category i
    total_operations = sum(len(weights[i]) for i in range(1, len(weights)))
    # Progress bar setup
    pbar = tqdm(total=total_operations, disable=not verbose, desc='Knapsack Progress')

    for i in range(1, len(weights)):
        current_array = [-1 for _ in range(max_weight + 1)]
        current_path = [[] for _ in range(max_weight + 1)]
        for j in range(len(weights[i])):
            for k in range(weights[i][j], max_weight + 1):
                if last_array[k - weights[i][j]] > 0:
                    if current_array[k] < last_array[k - weights[i][j]] + values[i][j]:
                        current_array[k] = last_array[k - weights[i][j]] + values[i][j]
                        current_path[k] = copy.deepcopy(last_path[k - weights[i][j]])
                        current_path[k].append((i, j))
                    # current_array[k] = max(current_array[k], last_array[k - weight[i][j]] + value[i][j])
            pbar.update(1) # Update progress after processing each weight
        last_array = current_array
        last_path = current_path
    solution, index_path = get_onepick_solution(last_array, last_path)

    return solution, index_path


def get_onepick_solution(scores, paths):
    scores_paths = list(zip(scores, paths))
    scores_paths_by_score = sorted(scores_paths, key=lambda tup: tup[0],
                                    reverse=True)

    return scores_paths_by_score[0][0], scores_paths_by_score[0][1]

def get_top_players_by_position(players, top_n=40):
    # Group players by position
    grouped_players = {
        "GK": [],
        "DEF": [],
        "MID": [],
        "ATT": []
    }
    
    for player in players:
        grouped_players[player.position].append(player)
    
    # Sort each group by points in descending order and slice the top_n players
    top_players = {}
    for position, players_list in grouped_players.items():
        sorted_players = sorted(players_list, key=lambda p: p.points, reverse=True)
        top_players[position] = sorted_players[:top_n]
    print(len(grouped_players["GK"]))
    print(len(grouped_players["DEF"]))
    print(len(grouped_players["MID"]))
    print(len(grouped_players["ATT"]))
    return top_players
    
    
if __name__ == '__main__':
    app.run(debug=True)
    # port = int(os.environ.get("PORT", 5000))
    # app.run(host='0.0.0.0', port=port)
