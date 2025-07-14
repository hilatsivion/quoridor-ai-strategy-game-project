# -*- coding: utf-8 -*-

import os
from pygame import Color

from entities.coord import Coord

__doc__ = """ Centralizes all global configuration flags """

# Debug FLAG
__DEBUG__ = True

# Frame rate
FRAMERATE = 25

# Config Options
GAME_TITLE = 'Quoridor'
DEFAULT_NUM_PLAYERS = 2

# Cell size
CELL_WIDTH = 50
CELL_HEIGHT = 50
CELL_PAD = 7
CELL_BORDER_SIZE = 2

# Default Number of rows and cols
DEF_ROWS = 9
DEF_COLS = 9

# Number of Walls per player
NUM_WALLS = 10

def get_board_settings(difficulty_level):
    """
    Return board dimensions, wall count, and dynamic cell sizes based on AI difficulty level.
    All boards are scaled to appear the same visual size as a 9x9 board.
    
    Args:
        difficulty_level (int): AI difficulty level
        
    Returns:
        tuple: (rows, cols, walls_per_player, cell_width, cell_height)
    """
    # Base dimensions for scaling (9x9 board)
    base_size = 9
    base_cell_width = CELL_WIDTH
    base_cell_height = CELL_HEIGHT
    
    # Calculate target board size (without padding)
    target_board_width = base_size * base_cell_width + (base_size - 1) * CELL_PAD
    target_board_height = base_size * base_cell_height + (base_size - 1) * CELL_PAD
    
    if difficulty_level <= 2:
        # Depth 1-2: 9x9 board, 10 walls
        board_size = 9
        walls = 10
    elif difficulty_level <= 4:
        # Depth 3-4: 7x7 board, 7 walls
        board_size = 7
        walls = 7
    else:
        # Depth 5+: 5x5 board, 5 walls
        board_size = 5
        walls = 5
    
    # Calculate dynamic cell sizes to fit target board dimensions
    # Available space for cells = target_size - (padding_between_cells)
    available_width = target_board_width - (board_size - 1) * CELL_PAD
    available_height = target_board_height - (board_size - 1) * CELL_PAD
    
    # Calculate cell sizes
    cell_width = available_width // board_size
    cell_height = available_height // board_size
    
    # Ensure minimum cell size for visibility
    cell_width = max(cell_width, 30)
    cell_height = max(cell_height, 30)
    
    return (board_size, board_size, walls, cell_width, cell_height)

### COLORS ###
# Font Color & SIZE
FONT_COLOR = Color(0, 10, 50)
FONT_BG_COLOR = Color(255, 255, 255)
FONT_SIZE = 16

# Board Background and Border color and look
BOARD_BG_COLOR = Color(250, 248, 245)  # Light cream
BOARD_BRD_COLOR = Color(80, 90, 100)  # Soft dark gray
BOARD_BRD_SIZE = 2

# Cell colors - More visible and pleasant
CELL_BORDER_COLOR = Color(120, 130, 140)  # Medium gray
CELL_COLOR = Color(220, 200, 180)  # Light wood tone
CELL_VALID_COLOR = Color(120, 200, 180)  # Soft cyan

# Wall Color
WALL_COLOR = Color(60, 70, 80)  # Dark but not black

# Wall Preview Colors and Effects
WALL_PREVIEW_COLOR = Color(100, 130, 160)  # Lighter blue-gray for preview
WALL_PREVIEW_OPACITY = 128  # 50% transparency (0-255 scale)

# Pawns color - More vibrant and visible
PAWN_A_COL = Color(220, 80, 80)  # Bright red for player
PAWN_B_COL = Color(80, 120, 220)  # Bright blue for AI
PAWN_BORDER_COL = Color(255, 255, 255)  # White border for contrast

# Gauge bars
GAUGE_WIDTH = CELL_WIDTH
GAUGE_HEIGHT = 5
GAUGE_COLOR = Color(128, 40, 40)
GAUGE_BORDER_COLOR = Color(0, 0, 0)

# Other constants
PAWN_PADDING = 25  # Pixels right to the board


class DIR:
    """ Directions
    """
    N = 0
    S = 1
    E = 2
    W = 3


DIRS = {DIR.N, DIR.S, DIR.E, DIR.W}  # Available directions
OPPOSITE_DIRS = [DIR.S, DIR.N, DIR.W, DIR.E]  # Reverse direction

# Delta to add to position to move into that direction
DIRS_DELTA = [Coord(-1, 0), Coord(+1, 0), Coord(0, -1), Coord(0, +1)]

# Network port
NETWORK_ENABLED = False  # Set to true to enable network playing
PORT = 8001  # This client port
BASE_PORT = 8000
SERVER_ADDR = 'localhost'
SERVER_URL = 'http://{}:{}'.format(SERVER_ADDR, PORT)

# Default AI playing level
LEVEL = 2

# Infinite
INF = 99

# Cache
CACHE_ENABLED = False
CACHE_DIR = './__cache'
CACHE_AI_FNAME = os.path.join(CACHE_DIR, 'ai.memo')
CACHE_DIST_FNAME = os.path.join(CACHE_DIR, 'dist.memo')
