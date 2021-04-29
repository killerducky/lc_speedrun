#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import chess.pgn
import re
from datetime import datetime, timedelta

USERNAME = "CLSmith15"
PIECES = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]
SCOREBOARD = {}
TIMEUSED = 0
TIMEUSED_LOSS_PENALTY = 0

# Last game of CLSmith15's run
#[Event "Rated Blitz game"]
#[Site "https://lichess.org/nlWFiG6Z"]
#[Date "2021.04.28"]
#[White "prof81"]
#[Black "CLSmith15"]
#[Result "0-1"]
#[UTCDate "2021.04.28"]
#[UTCTime "16:33:57"]

# First game of CLSmith15's run
#[Event "Rated Bullet game"]
#[Site "https://lichess.org/vvktNmSG"]
#[Date "2021.04.27"]
#[White "gabbba10"]
#[Black "CLSmith15"]
#[Result "1-0"]
#[UTCDate "2021.04.27"]
#[UTCTime "18:37:42"]

# Go to the game you want to include, look at the pgn, find these:
#[UTCDate "2021.04.28"]
#[UTCTime "16:33:57"]
#SINCE = datetime.strptime("2022.04.28 17:34:59", "%Y.%m.%d %H:%M:%S")
#SINCE = datetime.strptime("2021.04.28 16:33:58", "%Y.%m.%d %H:%M:%S")
#SINCE = datetime.strptime("2021.04.28 16:33:57", "%Y.%m.%d %H:%M:%S")   # orig  vs prof81
#SINCE = datetime.strptime("2021.04.28 16:33:56", "%Y.%m.%d %H:%M:%S")    # one second before vs prof81
#SINCE = datetime.strptime("2021.04.28 16:27:49", "%Y.%m.%d %H:%M:%S")    # one second before vs chingis-han

#SINCE = datetime.strptime("2021.04.28 16:27:49", "%Y.%m.%d %H:%M:%S")  # 1 games
#SINCE = datetime.strptime("2021.04.28 12:27:49", "%Y.%m.%d %H:%M:%S")  # 1 games
#SINCE = datetime.strptime("2021.04.28 11:27:49", "%Y.%m.%d %H:%M:%S")  # 3 games -- oldest game is [UTCDate "2021.04.28"] [UTCTime "16:27:50"]
#SINCE = datetime.strptime("2021.04.28 10:27:49", "%Y.%m.%d %H:%M:%S")  # 4 games -- oldest game is [UTCDate "2021.04.28"] [UTCTime "16:21:44"] 4th game?
# Seems to be a 5 hour difference, and I'm GMT-5...
# But I don't see why timezones matter?
#SINCE = datetime.strptime("2021.04.28 6:27:49", "%Y.%m.%d %H:%M:%S")  # 4 games
#SINCE = datetime.strptime("2021.04.28 01:27:49", "%Y.%m.%d %H:%M:%S")  # 4 games
#SINCE = datetime.strptime("2021.04.28 1:27:49", "%Y.%m.%d %H:%M:%S")  # 4 games
#SINCE = datetime.strptime("2021.04.27 16:27:49", "%Y.%m.%d %H:%M:%S")  # 10 games
SINCE = datetime.strptime("2021.04.26 16:27:49", "%Y.%m.%d %H:%M:%S")  # 10 games
UNTIL = datetime.strptime("2021.04.28 20:17:26", "%Y.%m.%d %H:%M:%S")

# Use this if you want to include all games to present
#UNTIL = datetime.today()

def init():
    for piece in PIECES:
        SCOREBOARD[piece] = chess.Board(fen=None)

def print_scoreboard():
    for piece in PIECES:
        print(SCOREBOARD[piece])
        print()
    print("Total time:", timedelta(seconds=TIMEUSED))
    print("Total time with loss penalty:", timedelta(seconds=TIMEUSED_LOSS_PENALTY))

def download_games():
    print("since", SINCE.timestamp()*1000, SINCE)
    print("until", UNTIL.timestamp()*1000, UNTIL)
    params={
        'since':int(SINCE.timestamp()*1000),
        'until':int(UNTIL.timestamp()*1000),
        #'max':10,
        'clocks':'true'}
    url = "https://lichess.org/api/games/user/{}".format(USERNAME)
    print("url", url, "params", params)
    response = requests.get(url, params=params)
    content = response.content.decode('utf-8')
    print(content)
    open("games.pgn", "w").write(content)

def parse_game(game):
    print(game.headers['TimeControl'])
    print(game.headers['Result'])
    print(game.headers['White'] == USERNAME)
    user_is_white = game.headers['White'] == USERNAME
    user_lost = game.headers['Result'] == '0-1' if user_is_white else game.headers['Result'] == '1-0'
    node = game
    m = re.search("(\d+)\+(\d+)", game.headers['TimeControl'])
    (time_main, time_inc) = m.groups()
    time_main = int(time_main)
    time_inc = int(time_inc)
    clk_0 = time_main
    clk_1 = time_main
    plies = 0
    new_moves = 0
    while len(node.variations) > 0:
        node = node.variations[0]
        clk_0 = clk_1
        m = re.search("\[\%clk (\d+):(\d+):(\d+)", node.comment)
        (h, m, s) = m.groups()
        clk_1 = int(h)*60 + int(m)*60 + int(s)
        piece = node.board().piece_at(node.move.to_square)
        if node.move.promotion:
            piece = chess.Piece(chess.PAWN, chess.WHITE)
        plies = node.ply()
        if (plies%2==1 if user_is_white else plies%2==0):
            print(node.move, chess.SQUARE_NAMES[node.move.to_square], node.comment, plies, clk_1, piece)
            if not SCOREBOARD[piece.piece_type].piece_at(node.move.to_square):
                piece.color = chess.WHITE # Just store all as white (capital letter) pieces
                SCOREBOARD[piece.piece_type].set_piece_at(node.move.to_square, piece)
                print(SCOREBOARD[piece.piece_type])
                new_moves += 1
    max_time = time_main*2 + time_inc*plies
    used_time = max_time - clk_0 - clk_1
    # Penalize losses by using max game time
    # Even if games are not useful for covering new squares,
    # the user will try to win or draw to scored time
    scored_time = max_time if user_lost else used_time
    global TIMEUSED
    global TIMEUSED_LOSS_PENALTY
    TIMEUSED += used_time
    TIMEUSED_LOSS_PENALTY += scored_time
    #print(plies, max_time, used_time, max_time, clk_0, clk_1)
    print("new_moves", new_moves, "used_time", used_time, "scored_time", scored_time, "TIMEUSED", TIMEUSED, "TIMEUSED_LOSS_PENALTY", TIMEUSED_LOSS_PENALTY)

def parse_pgn():
    pgn = open("games.pgn")
    while True:
        game = chess.pgn.read_game(pgn)
        if not game: break
        parse_game(game)

init()
print_scoreboard()
# Comment this if you just want to reparse the games.pgn
#download_games()
parse_pgn()
print_scoreboard()

