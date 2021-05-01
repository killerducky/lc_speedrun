# lc\_speedrun

Inspired by https://www.twitch.tv/clsmith15

Move all pieces to all squares using the least in-game time possible.
To prevent throwing games to save time, the code assigns the full game time for all losses.

## Running:
- Install python
- Install required python modules:
    - `pip3 install -r requirements.txt`
- edit lc\_speedrun.ini
- python3 lc\_speedrun.py

## Output:
Prints to stdout stats for each game, and final boards in ASCII.
Outputs \*.png files for Pawn, Knight, Bishop, Rook, Queen, and King.
Outputs `total.txt`
Use the \*.png and total.txt files as sources in e.g. OBS for streaming.

