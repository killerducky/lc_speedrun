#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import chess.pgn
import re
from datetime import datetime, timedelta, timezone
import configparser

CONF = configparser.ConfigParser()
PIECES = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]
SCOREBOARD = {}
TIMEUSED = 0
TIMEUSED_LOSS_PENALTY = 0
NUMGAMES = 0

# Last game of CLSmith15's run
#[Event "Hourly UltraBullet Arena"]
#[Site "https://lichess.org/RmmeqiK1"]
#[Date "2021.04.28"]
#[White "CLSmith15"]
#[Black "wongo"]
#[Result "0-1"]
#[UTCDate "2021.04.28"]
#[UTCTime "01:35:33"]

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
#SINCE = datetime.strptime("2021.04.27 18:37:42 +0000", "%Y.%m.%d %H:%M:%S %z")
#UNTIL = datetime.strptime("2021.04.28 01:35:33 +0000", "%Y.%m.%d %H:%M:%S %z")

# Use this if you want to include all games to present
#SINCE = datetime.strptime("2000.04.27 18:37:42 +0000", "%Y.%m.%d %H:%M:%S %z")
#UNTIL = datetime.today()

def init():
    for piece in PIECES:
        SCOREBOARD[piece] = chess.Board(fen=None)
    CONF.read("lc_speedrun.ini")

def print_scoreboard():
    for piece in PIECES:
        print(SCOREBOARD[piece])
        print()
    print("Total time:", timedelta(seconds=TIMEUSED))
    print("Total time with loss penalty:", timedelta(seconds=TIMEUSED_LOSS_PENALTY))

def print_stats():
    total = 0
    promotions = 0
    for piece in PIECES:
        for square in range(64):
            if SCOREBOARD[piece].piece_at(square):
                total += 1
    for square in (list(range(8)) + list(range(64-8,64))):
        if SCOREBOARD[chess.PAWN].piece_at(square):
            promotions += 1
    print("Total {:3d} out of {} promotions {:2d} out of {}".format(total, 6*64, promotions, 16))

def svg_scoreboard():
    for i in PIECES:
        piece = chess.Piece(i, chess.WHITE)
        open("{}.svg".format(str(piece)), "w").write(chess.svg.board(SCOREBOARD[i]))

def download_games():
    if 'until' not in CONF['DEFAULT']:
        # TODO: timezone?
        until = datetime.today()
    else:
        until = datetime.strptime(CONF['DEFAULT']['until'], "%Y.%m.%d %H:%M:%S %z")
    since = datetime.strptime(CONF['DEFAULT']['since'], "%Y.%m.%d %H:%M:%S %z")
    # Add 1 second to until time to make sure we get the final game
    params={
        'since':int(since.timestamp()*1000),
        'until':int(until.timestamp()*1000+1000),
        #'max':10,
        'clocks':'true'}
    url = "https://lichess.org/api/games/user/{}".format(CONF['DEFAULT']['username'])
    #print("url", url, "params", params)
    response = requests.get(url, params=params)
    content = response.content.decode('utf-8')
    #print(content)
    open("games.pgn", "w").write(content)

def parse_game(game):
    if game.headers['Variant'] != "Standard" or game.headers['TimeControl'] == "-":
        print("Skipping {} Variant {} TimeControl {}".format(game.headers['Site'], game.headers['Variant'], game.headers['TimeControl']))
        return False
    user_is_white = game.headers['White'] == CONF['DEFAULT']['username']
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
        clk_1 = int(h)*60*60 + int(m)*60 + int(s)
        piece = node.board().piece_at(node.move.to_square)
        if node.move.promotion:
            piece = chess.Piece(chess.PAWN, chess.WHITE)
        plies = node.ply()
        if (plies%2==1 if user_is_white else plies%2==0):
            #print(node.move, chess.SQUARE_NAMES[node.move.to_square], node.comment, plies, clk_1, piece)
            if not SCOREBOARD[piece.piece_type].piece_at(node.move.to_square):
                piece.color = chess.WHITE # Just store all as white (capital letter) pieces
                SCOREBOARD[piece.piece_type].set_piece_at(node.move.to_square, piece)
                #print(SCOREBOARD[piece.piece_type])
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
    print("#{:3d} {:20s} new_moves {:3d} used_time {:5d} scored_time {:5d} tottime {:7d} tottime_penalty {:7d}".format(
        NUMGAMES, game.headers["Site"], new_moves, used_time, scored_time, TIMEUSED, TIMEUSED_LOSS_PENALTY), end=" ")
    print_stats()
    return True

def parse_pgn():
    pgn = open("games.pgn")
    games = []
    while True:
        game = chess.pgn.read_game(pgn)
        if not game: break
        games.append(game)
    # lichess returns most recent games first, so reverse them
    for game in reversed(games):
        global NUMGAMES
        if parse_game(game):
            NUMGAMES += 1

init()
# Comment this if you just want to reparse the games.pgn
download_games()
parse_pgn()
print_scoreboard()
svg_scoreboard()

