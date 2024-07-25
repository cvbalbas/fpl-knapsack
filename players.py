import requests
import csv

class Player:
    def __init__(self, name: str, price: int, points: float, position: str):
        self.name = name
        self.price = price
        self.points = points
        self.position = position

    def __str__(self):
        return f"({self.name}, {self.price}, {self.points}, {self.position})"

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        if pos not in ["GK", "DEF", "MID", "ATT"]:
            raise ValueError("Sorry, that's not a valid position")
        self._position = pos

    def get_group(self):
        if self.position == "GK":
            group = 0
        elif self.position == "DEF":
            group = 1
        elif self.position == "MID":
            group = 2
        else:
            group = 3
        return group
    

# URL for the Fantasy Premier League API
FPL_API_URL = 'https://fantasy.premierleague.com/api/bootstrap-static/'

# Function to get player data from the API
def get_fpl_data():
    response = requests.get(FPL_API_URL)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception("Failed to fetch data from FPL API")

# Function to process the data and extract relevant fields
def process_fpl_data(data):
    teams = {team['id']: team['name'] for team in data['teams']}
    positions = ["GK", "DEF", "MID", "ATT"]
    players = data['elements']
    
    processed_data = []
    for player in players:
        player_data = {
            'name': player['web_name'],
            'team': teams[player['team']],
            'score': player['total_points'],
            'position': positions[player['element_type'] - 1],
            'price': player['now_cost'],  # Price is given in tenths of millions
            'status': player['status'], # 'a': Available 'd': Doubtful 'i': Injured 's': Suspended 'u': Unavailable
        }
        processed_data.append(player_data)
    
    return processed_data

# Function to write data to a CSV file
def write_to_csv(players_data, filename='fpl_players.csv'):
    fieldnames = ['name', 'team', 'score', 'position', 'price', 'status']
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for player in players_data:
            writer.writerow(player)
# Main function to get data, process it, and write to CSV
def main():
    try:
        fpl_data = get_fpl_data()
        processed_data = process_fpl_data(fpl_data)
        write_to_csv(processed_data)
        print("Data successfully written to fpl_players.csv")
        create_players_from_csv()
    except Exception as e:
        print(f"An error occurred: {e}")
    

# Function to create players from CSV data
def create_players_from_csv(filename='fpl_players.csv'):
    players = []
    with open(filename, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if int(row['score']) > 0 and row['status'] == 'a':
                name = row['name']
                price = float(row['price'])
                points = float(row['score'])
                position = row['position']
                # Create a Player instance and append to the list
                player = Player(name=name, price=price, points=points, position=position)
                players.append(player)
                # print(player)
    print(len(players))
    return players


if __name__ == '__main__':
    main()

