#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import chess.pgn
import re
from datetime import datetime, timedelta, timezone
import configparser
import os
import sys
import cairosvg
from PIL import Image
from pathlib import Path
import imageio

CONF = configparser.ConfigParser()
PIECES = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]
SCOREBOARD = {}
TIMEUSED = 0
TIMEUSED_LOSS_PENALTY = 0
NUMGAMES = 0
TIMEFORMAT = "%Y.%m.%d %H:%M:%S %z"

def init():
    for piece in PIECES:
        SCOREBOARD[piece] = {}
        SCOREBOARD[piece]['board'] = chess.Board(fen=None)
        SCOREBOARD[piece]['new'] = ()
    CONF.read("lc_speedrun.ini")

def print_scoreboard():
    s = [""]*8
    for piece in PIECES:
        s = ['   '.join(pair) for pair in zip(s, str(SCOREBOARD[piece]['board']).splitlines())]
    [print(line) for line in s]
    print("Total time:", timedelta(seconds=TIMEUSED))
    print("Total time with loss penalty:", timedelta(seconds=TIMEUSED_LOSS_PENALTY))

def print_stats(save):
    total = 0
    promotions = 0
    for piece in PIECES:
        for square in range(64):
            if SCOREBOARD[piece]['board'].piece_at(square):
                total += 1
    for square in (list(range(8)) + list(range(64-8,64))):
        if SCOREBOARD[chess.PAWN]['board'].piece_at(square):
            promotions += 1
    print("Promotions {:2d} out of {}".format(promotions, 16))
    if save:
        with open("total.txt", "w") as f:
            if 'timeused_loss_penalty' in CONF['DEFAULT'] and CONF['DEFAULT']['timeused_loss_penalty'] == 'yes':
                t = TIMEUSED_LOSS_PENALTY
            else:
                t = TIMEUSED
            f.write("Moves played: {} / {} {:3.1f}%  Time Used {}\n".format(
                total, 6*64, 100.0*total/6/64, timedelta(seconds=t)))
            f.write("Games: {} Promotions {:2d}/16\n".format(
                NUMGAMES, promotions))

def svg_scoreboard():
    images = []
    for i in PIECES:
        piece = chess.Piece(i, chess.WHITE)
        with open("white_{}.svg".format(str(piece)), "w") as f:
            f.write(chess.svg.board(SCOREBOARD[i]['board'], size=CONF['svg']['size'], colors=CONF['svg'], arrows=SCOREBOARD[i]['new']))
        cairosvg.svg2png(url="white_{}.svg".format(str(piece)), write_to="white_{}.png".format(str(piece)))
        black = Image.open("white_{}.png".format(str(piece)))
        black = black.rotate(180)
        black.save("black_{}.png".format(str(piece)))
        images.append(Image.open("white_{}.png".format(str(piece))))
    (width, height) = images[0].size
    pad = int(CONF['svg']['pad'])
    all_image = Image.new('RGB', (width*3 + pad*4, height*2 + pad*3))
    for i in range(6):
        x = i%3
        y = i//3
        all_image.paste(images[i], (pad+x*(width+pad), pad+y*(height+pad)))
    all_image.save("all-{:05d}.png".format(NUMGAMES))
    all_image.save("all.png")

def download_games():
    if 'until' not in CONF['DEFAULT'] or CONF['DEFAULT']['until'] == "None":
        # TODO: timezone?
        until = datetime.utcnow()
    else:
        until = datetime.strptime(CONF['DEFAULT']['until'], TIMEFORMAT)
    since = datetime.strptime(CONF['DEFAULT']['since'], TIMEFORMAT)
    pgn_data = ""
    if os.path.exists("games.pgn"):
        pgn = open("games.pgn")
        game = chess.pgn.read_game(pgn)
        if game:
            since = "{} {} +0000".format(game.headers['UTCDate'], game.headers['UTCTime'])
            # Add 1 second to make sure we skip this game that we have in the pgn already
            since = datetime.strptime(since, TIMEFORMAT) + timedelta(seconds=1)
            print("Pre-existing games.pgn found. Change since to: {}", since)
            pgn_data = open("games.pgn").read()
    # Add 1 second to until time to make sure we get the final game
    until += timedelta(seconds=1)
    params={
        'since':int(since.timestamp()*1000),
        'until':int(until.timestamp()*1000),
        #'max':10,
        'clocks':'true'}
    url = "https://lichess.org/api/games/user/{}".format(CONF['DEFAULT']['username'])
    print("since={} until={}".format(since, until))
    print("url", url, "params", params)
    response = requests.get(url, params=params)
    content = response.content.decode('utf-8')
    if not content:
        print("No new games, do not overwrite games.pgn")
    else:
        open("games.pgn", "w").write(content + pgn_data)

def parse_game(game):
    if game.headers['Variant'] != "Standard" or game.headers['TimeControl'] == "-" or 'WhiteRatingDiff' not in game.headers:
        print("Skipping {} Variant {} TimeControl {}".format(game.headers['Site'], game.headers['Variant'], game.headers['TimeControl']))
        return False
    for piece in PIECES:
        SCOREBOARD[piece]['new'] = []
    user_is_white = game.headers['White'] == CONF['DEFAULT']['username']
    user_lost = game.headers['Result'] == '0-1' if user_is_white else game.headers['Result'] == '1-0'
    node = game
    m = re.search("(\d+)\+(\d+)", game.headers['TimeControl'])
    (time_main, time_inc) = m.groups()
    time_main = int(time_main)
    time_inc = int(time_inc)
    # Handle beserk
    time_main_user = [time_main, time_main]
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
        if plies < 2:
            # In case someone does beserk, we need to use this clock time instead of the one from header
            time_main_user[plies] = clk_1
        piece = node.board().piece_at(node.move.to_square)
        if node.move.promotion:
            piece = chess.Piece(chess.PAWN, chess.WHITE)
        plies = node.ply()
        if (plies%2==1 if user_is_white else plies%2==0):
            #print(node.move, chess.SQUARE_NAMES[node.move.to_square], node.comment, plies, clk_1, piece)
            if not SCOREBOARD[piece.piece_type]['board'].piece_at(node.move.to_square):
                piece.color = chess.WHITE # Just store all as white (capital letter) pieces
                SCOREBOARD[piece.piece_type]['board'].set_piece_at(node.move.to_square, piece)
                SCOREBOARD[piece.piece_type]['new'].append((node.move.to_square, node.move.to_square))
                #print(SCOREBOARD[piece.piece_type]['board'])
                new_moves += 1
    max_time = time_main_user[0] + time_main_user[1] + time_inc*plies
    used_time = max_time - clk_0 - clk_1
    # Penalize losses by using max game time
    # Even if games are not useful for covering new squares,
    # the user will try to win or draw to scored time
    scored_time = max_time if user_lost else used_time
    global TIMEUSED
    global TIMEUSED_LOSS_PENALTY
    TIMEUSED += used_time
    TIMEUSED_LOSS_PENALTY += scored_time
    print("#{:3d} {:20s} new_moves {:3d} used_time {:5d} scored_time {:5d} tottime {:7s} tottime_penalty {:7s}".format(
        NUMGAMES, game.headers["Site"], new_moves, used_time, scored_time, str(timedelta(seconds=TIMEUSED)), str(timedelta(seconds=TIMEUSED_LOSS_PENALTY))), end=" ")
    print_stats(False)
    return True

def parse_pgn():
    if not os.path.exists("games.pgn"): return
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
            if 'animate' in CONF['DEFAULT'] and CONF['DEFAULT']['animate'] == "yes":
                svg_scoreboard()

def animate_scoreboard():
    images = list(sorted(Path('.').glob('all-*.png')))
    image_list = []
    for fn in images:
        image_list.append(imageio.imread(fn))
    imageio.mimwrite('animate.gif', image_list, fps=CONF['DEFAULT']['fps'])

init()
# Comment this if you just want to reparse the games.pgn
download_games()
parse_pgn()
print_scoreboard()
svg_scoreboard()
print_stats(True)
if 'animate' in CONF['DEFAULT'] and CONF['DEFAULT']['animate'] == "yes":
    animate_scoreboard()
