import socket
import threading
import random
import string
import time
import select
import platform

def clear():
   if platform.system() =="Linux" or platform.system() =="Darwin":
      os.system("clear")
   elif platform.system() =="Windows":
      os.system("cls")

# Constants
GAME_DURATIONS = {1: 60, 2: 600, 3: 1200, 4: 1800}  # in seconds
TIMEOUT_PER_ROUND = 30  # in seconds
MAX_PLAYERS_PER_ROOM = 10
LEADERBOARD_SIZE = 5

# Global variables
PLAYERS = {}
ROOM_PLAYERS = []
CORRECT_ANSWER = random.randint(0, 10)
ROUND_ACTIVE = False
START_TIME = 0
ROOM_PASSWORD = None

def generate_leaderboard(players):
    sorted_players = sorted(players.items(), key=lambda x: x[1], reverse=True)
    leaderboard = ["\nLeaderboard:"]
    for i, (name, score) in enumerate(sorted_players[:LEADERBOARD_SIZE], start=1):
        leaderboard.append(f"{i}. {name}: {score} points")
    return '\n'.join(leaderboard)


def handle_client(conn, addr, game_duration):
    global PLAYERS
    global ROOM_PLAYERS
    global CORRECT_ANSWER
    global ROUND_ACTIVE
    global START_TIME
    name = ''
    try:
        conn.send("Welcome to the Guess a Number game!\n".encode())
        
        if ROOM_PASSWORD:
            conn.send("Enter the room password: ".encode())
            password_attempt = conn.recv(1024).decode().strip()
            if password_attempt != ROOM_PASSWORD:
                conn.send("Incorrect password. Connection closed.\n".encode())
                return

        conn.send("Enter your name: ".encode())
        name = conn.recv(1024).decode().strip()
        while name in PLAYERS:
            conn.send("Name already taken. Enter another name: ".encode())
            name = conn.recv(1024).decode().strip()
        PLAYERS[name] = 0  # Initialize player's score
        ROOM_PLAYERS.append(name)
        conn.send(f"Welcome, {name}!\n".encode())

        if len(ROOM_PLAYERS) < 2:
            conn.send("Waiting for more players to join...\n".encode())
            while len(ROOM_PLAYERS) < 2:
                time.sleep(1)

        while True:
            ROUND_ACTIVE = False
            time.sleep(1)
            if not ROUND_ACTIVE:
                ROUND_ACTIVE = True
                conn.send("Guess a number between 0 and 10: ".encode())
                START_TIME = time.time()  # Reset start time for each round

                # Wait for player guess or timeout
                while time.time() - START_TIME < TIMEOUT_PER_ROUND:
                    ready, _, _ = select.select([conn], [], [], 0)
                    if ready:
                        guess = conn.recv(1024).decode().strip()
                        try:
                            guess = int(guess)
                        except ValueError:
                            conn.send("Invalid input! Please enter a number: ".encode())
                            continue
                        if guess == CORRECT_ANSWER:
                            conn.send("Congratulations! You guessed correctly!\n".encode())
                            PLAYERS[name] += 1
                        else:
                            conn.send("Wrong guess. Try again!\n".encode())
                        break
                else:
                    conn.send(f"Time's up! The correct answer was {CORRECT_ANSWER}.\n".encode())
                ROUND_ACTIVE = False

            # Check if game duration has passed
            if time.time() - START_TIME > game_duration:
                conn.send("Game over! Thank you for playing.\n".encode())
                break

    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        if name in ROOM_PLAYERS:
            ROOM_PLAYERS.remove(name)
        if name in PLAYERS:
            del PLAYERS[name]


def send_leaderboard(conn):
    global PLAYERS
    try:
        leaderboard = generate_leaderboard(PLAYERS)
        conn.send(leaderboard.encode())
    except Exception as e:
        print(f"Error sending leaderboard: {e}")

def start_server():
    global GAME_DURATIONS
    global ROOM_PASSWORD
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind(('', 0))  # Automatically selects an available port
            port = server.getsockname()[1]  # Get the port assigned by the OS
            print(f"Server is listening on port {port}...")
            server.listen()

            # Select game duration
            duration_choice = int(input("Select game duration:\n1. 1 minute\n2. 10 minutes\n3. 20 minutes\n4. 30 minutes\nEnter your choice: "))
            duration_choice = min(max(duration_choice, 1), 4)  # Ensure choice is within range
            game_duration = GAME_DURATIONS[duration_choice]

            # Set room password if desired
            while True:
               password_choice = input("Do you want to set a password for the room? (y/n): ").lower()
               if password_choice == 'y' or password_choice == 'n':
                  break
               else:
                  print("Error, please enter a correct option!")   

            if password_choice == 'y':
                ROOM_PASSWORD = input("Enter the room password: ")

            while True:
                conn, addr = server.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr, game_duration))
                thread.start()
    except Exception as e:
        print(f"Error starting server: {e}")

def start_client():
    global PLAYERS
    global ROOM_PLAYERS
    host = input("Enter server IP address: ")
    port = int(input("Enter server port: "))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((host, port))
            while True:
                data = client.recv(1024).decode()
                if not data:
                    break
                    
                if "Enter the room password" in data:
                   pass
                else: 
                   print(data, end='')
                   
                if "Enter your name" in data:
                    name = input()  # Get the name from user
                    client.send(name.encode())
                elif "Enter the room password" in data:
                    password = input("Enter the room password: ")
                    client.send(password.encode())
                elif "Guess a number" in data:
                    guess = input("Enter your guess: ")  # Get the guess from user
                    client.send(guess.encode())
                    # Wait for server response
                    response = client.recv(1024).decode()
                    print(response)
                elif "Leaderboard" in data:
                    send_leaderboard(client)
            time.sleep(1)
    except Exception as e:
        print(f"Error connecting to server: {e}")


def main():
    print("Welcome to Guess a Number!")

    while True:
        choice = input("Do you want to host a game (h) or connect to a game (c)? ").lower()
        if choice == 'h':
            start_server()
            break
        elif choice == 'c':
            start_client()
            break
        else:
            print("Invalid choice. Please enter 'h' to host or 'c' to connect.")

if __name__ == "__main__":
    main()
