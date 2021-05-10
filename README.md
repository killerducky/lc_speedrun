# lc\_speedrun

Inspired by https://www.twitch.tv/clsmith15

Move all pieces to all squares using the least in-game time possible.
To prevent throwing games to save time, the code assigns the full game time for all losses.

## Running:
- Install python
- Install required python modules.
    - Windows:
        - Install python3
        - Run `cmd.exe`
        - `cd c:\path\to\lc_speedrun`
        - `python3 -m pip install -r requirements.txt`
- edit lc\_speedrun.ini
- python3 lc\_speedrun.py
- Script downloads games from lichess.org, adds to games.pgn, and finds moves played etc.
    - Also assumes everything in games.pgn is included in the run.
    - If you start a new run, delete games.pgn manually
- Use all.html, white\_P, White\_R, etc, and total.txt files as sources in e.g. OBS for streaming.

## Output:
Prints to stdout stats for each game, and final boards in ASCII.
Outputs `all.png`, `white_*.png` and `total.txt` files for total progress
Outputs \*.png files for Pawn, Knight, Bishop, Rook, Queen, and King.

