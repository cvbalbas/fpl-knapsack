from players import create_players_from_csv, Player
import itertools
import copy
from tqdm import tqdm
from collections import OrderedDict
import numpy as np
import csv
import os
import pandas as pd
import uuid
from redis import Redis
from rq import Queue
from rq.job import Job
from tasks import best_full_teams

# from celery_config import run_knapsack_algorithm

# my_flask_app/app.py
from flask import Flask, request, jsonify, render_template, session
from flask_executor import Executor


app = Flask(__name__)
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = Redis.from_url(redis_url)
queue = Queue(connection=conn)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/printTable', methods=['POST'])
def printTable():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        
        # Read the CSV file into a DataFrame
        # df = pd.read_csv(filepath)
        players = []
        with open(filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            # print(*reader)
            for row in reader:
                # print(*row)
                if int(row['score']) > 0 and row['status'] == 'a':
                    name = row['name']
                    price = float(row['price'])
                    points = float(row['score'])
                    position = row['position']
                    # Create a Player instance and append to the list
                    player = Player(name=name, price=price, points=points, position=position)
                    players.append(player)
                    # print(player)
        
        # Convert the DataFrame to a JSON object
        # csv_data = df.to_dict(orient='records')
        # print(csv_data)
        # Get top 50 players from each position   
        top_players_by_position = get_top_players_by_position(players, top_n=50)
        merged_top_players = []
        for top_players in top_players_by_position.values():
            merged_top_players.extend(top_players)

        # Sort the merged list by points in descending order
        sorted_merged_top_players = sorted(merged_top_players, key=lambda player: player.points, reverse=True)
        # sorted_playersDB = sorted(players, key=lambda player: player.points, reverse=True)
        players_dict = [player.to_dict() for player in sorted_merged_top_players]

        print(*players_dict)
        return jsonify({'message': 'File successfully uploaded', 'players': players_dict}), 200

@app.route('/run_knapsack', methods=['POST'])
def run_knapsack():
    data = request.get_json()
    formation = int(data['formation']) 
    budget = int(data['budget'])
    filename = data['filename'] #Save as a unique filename and that's what we pass
    formations = [
            [3, 4, 3],
            [3, 5, 2],
            [4, 3, 3],
            [4, 4, 2],
            [4, 5, 1],
            [5, 3, 2],
            [5, 4, 1],
        ]
    possible_formations = [formations[formation]]
    
    playersDB = create_players_from_csv(filename)
    # print(*playersDB[:150])
    
    # Get top 50 players from each position   
    top_players_by_position = get_top_players_by_position(playersDB, top_n=50)
    merged_top_players = []
    for top_players in top_players_by_position.values():
        merged_top_players.extend(top_players)


    # Sort the merged list by points in descending order
    sorted_merged_top_players = sorted(merged_top_players, key=lambda player: player.points, reverse=True)
    # sorted_playersDB = sorted(playersDB, key=lambda player: player.points, reverse=True)
    # print(*sorted_playersDB[:100])

    # print("Data successfully opened fpl_players.csv and loaded into playersDB")
    
    user_id = str(uuid.uuid4())
    job =  queue.enqueue(best_full_teams, sorted_merged_top_players, possible_formations, budget)
    session['task_id'] = job.get_id()
    session['user_id'] = user_id

    # best_players = formation[0][2]
    # best_players_str = ",".join(str(element) for element in best_players)
    # # print(best_players_str)

    # formation_str = ",".join(str(element) for element in formation[0][0])

    # data = {
    #     "bestPlayers": best_players_str,
    #     "formation": formation_str,
    #     "score": formation[0][1]
    # }

    return jsonify({'status': 'submitted', 'task_id': job.get_id()})

@app.route('/task_status/<task_id>')
def task_status(task_id):
    job = Job.fetch(task_id, connection=conn)
    if job.is_finished:
        return jsonify(job.result)
    elif job.is_failed:
        return jsonify({'status': 'FAILED'})
    else:
        return jsonify({'status': 'IN_PROGRESS'})
    


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
    # app.run(debug=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
