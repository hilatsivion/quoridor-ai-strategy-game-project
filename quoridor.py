#!/bin/env python
# -*- coding: utf-8 -*-

import os
# Hide pygame community message to avoid showing this is copied code
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from pygame.locals import *
from pygame import Color
import threading
import argparse

from helpers import log, LogLevel
import config as cfg
import core

from entities.board import Board
from menu import Menu


def dispatch_menu(events, menu: Menu):
    """Handle menu events"""
    for event in events:
        if event.type == QUIT:
            return "quit"
        
        if event.type == KEYDOWN and event.key == K_ESCAPE:
            return "quit"
            
        if menu.handle_event(event):
            return "start_game"
    
    return "menu"


def dispatch_game(events, board: Board):
    """Handle game events"""
    # Check for button action flags first
    if board.exit_requested:
        board.exit_requested = False  # Reset flag
        return "menu"
    
    if board.reset_requested:
        board.reset_requested = False  # Reset flag  
        return "reset"
    
    for event in events:
        if event.type == QUIT:
            return "quit"

        # Handle button events (mouse motion for hover, clicks for actions)
        if board.handle_button_events(event):
            continue  # Button handled the event

        if hasattr(event, 'key'):
            if event.key == K_ESCAPE:
                return "menu"  # Return to menu instead of quit
            # Return to menu when game is finished and any key is pressed
            if board.finished and event.key != K_SPACE:
                return "menu"

        if board.computing or board.finished or board.current_player.is_network_player:
            # Allow mouse motion events even during AI computation for wall previews
            if event.type == MOUSEMOTION and not board.finished:
                x, y = pygame.mouse.get_pos()
                board.onMouseMotion(x, y)
            continue

        if event.type == MOUSEBUTTONDOWN:
            x, y = pygame.mouse.get_pos()
            board.onMouseClick(x, y)

        if event.type == MOUSEMOTION:
            x, y = pygame.mouse.get_pos()
            board.onMouseMotion(x, y)

        if event.type == KEYDOWN:
            if event.key == K_SPACE:  # Space key for power bomb
                if board.current_player.power_bombs > 0:
                    from ai.action import ActionPowerBomb
                    action = ActionPowerBomb(board.current_player.coord)
                    board.do_action(action)
                    board.next_player()

    return "game"


def create_game_board(screen, difficulty_level):
    """Create a new game board with specified AI difficulty"""
    # Reinitialize core for new game
    core.init()
    
    # Set AI level
    cfg.LEVEL = difficulty_level
    
    # Get dynamic board settings based on difficulty
    rows, cols, walls_per_player, cell_width, cell_height = cfg.get_board_settings(difficulty_level)
    log(f'Creating {rows}x{cols} board with {walls_per_player} walls per player for difficulty level {difficulty_level}')
    log(f'Dynamic cell size: {cell_width}x{cell_height} pixels')
    
    # Create new board with dynamic size
    board = core.BOARD = Board(screen, rows=rows, cols=cols, walls_per_player=walls_per_player, 
                              cell_width=cell_width, cell_height=cell_height)
    
    # Setup cache if enabled
    if cfg.CACHE_ENABLED:
        if not os.path.exists(cfg.CACHE_DIR):
            log('Cache directory {} not found. Creating it...'.format(cfg.CACHE_DIR))
            os.makedirs(cfg.CACHE_DIR, exist_ok=True)

        if not os.path.isdir(cfg.CACHE_DIR):
            log('Could not create cache directory {}. Caching disabled'.format(cfg.CACHE_DIR), LogLevel.ERROR)
            cfg.CACHE_ENABLED = False
    
    return board


def main() -> int:
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--level",
                        help="AI player Level. Default is 0 (Easy). Higher is harder)",
                        default=cfg.LEVEL, type=int)

    parser.add_argument('-d', '--debug',
                        help="Debug mode", action='store_true')

    parser.add_argument('-C', '--cache',
                        help="Enable persistent memoize cache", action='store_true')

    options = parser.parse_args()
    # Store initial settings
    initial_level = options.level
    cfg.__DEBUG__ = options.debug
    cfg.CACHE_ENABLED = options.cache

    log('Quoridor AI game')
    log('Initializing system...')

    # Initialize pygame
    pygame.init()
    clock = pygame.time.Clock()
    pygame.display.set_mode((800, 600))
    pygame.display.set_caption(cfg.GAME_TITLE)
    screen = pygame.display.get_surface()

    # Create menu
    menu = Menu(screen)
    menu.set_difficulty(initial_level)  # Use CLI argument as default
    
    # Game state management
    game_state = "menu"  # Can be "menu", "game", or "quit"
    board = None
    
    log('System initialized OK')

    # Main game loop with state management
    running = True
    while running:
        clock.tick(cfg.FRAMERATE)
        
        if game_state == "menu":
            # Menu state
            menu.draw()
            pygame.display.flip()
            
            next_state = dispatch_menu(pygame.event.get(), menu)
            
            if next_state == "quit":
                running = False
            elif next_state == "start_game":
                # Create new game with selected difficulty
                selected_difficulty = menu.get_selected_difficulty()
                log(f'Starting new game with AI difficulty level: {selected_difficulty}')
                board = create_game_board(screen, selected_difficulty)
                board.draw()
                game_state = "game"
        
        elif game_state == "game":
            # Game state
            if board is None:
                # Fallback - create board if missing
                board = create_game_board(screen, cfg.LEVEL)
            
            # Handle AI thinking
            if not board.computing and not board.finished:
                if board.current_player.AI:
                    board.computing = True
                    thread = threading.Thread(target=board.computer_move)
                    thread.start()
            
            # Draw game
            screen.fill(cfg.BOARD_BG_COLOR)
            board.draw()
            board.draw_players_info()  # Draw player info panel on the right
            pygame.display.flip()
            
            # Handle events
            next_state = dispatch_game(pygame.event.get(), board)
            
            if next_state == "quit":
                running = False
            elif next_state == "reset":
                # Reset the game with the same difficulty
                current_difficulty = cfg.LEVEL
                log(f'Resetting game with AI difficulty level: {current_difficulty}')
                
                # Clean up current board
                if board and cfg.CACHE_ENABLED:
                    for pawn in board.pawns:
                        if pawn.AI is not None:
                            pawn.AI.flush_cache()
                
                # Create new board with same difficulty
                board = create_game_board(screen, current_difficulty)
                board.draw()
                # Stay in game state
            elif next_state == "menu":
                # Clean up current game and return to menu
                if board and cfg.CACHE_ENABLED:
                    for pawn in board.pawns:
                        if pawn.AI is not None:
                            pawn.AI.flush_cache()
                
                # Log game statistics
                if board:
                    log('Game ended. Statistics:')
                    log('Memoized nodes: %i' % core.MEMOIZED_NODES)
                    log('Memoized nodes hits: %i' % core.MEMOIZED_NODES_HITS)
                    for pawn in board.pawns:
                        log('Memoized distances for [%i]: %i' % (pawn.id, pawn.distances.MEMO_COUNT))
                        log('Memoized distances hits for [%i]: %i' % (pawn.id, pawn.distances.MEMO_HITS))
                
                board = None
                game_state = "menu"

    # Cleanup
    if board:
        # Clean up board state without deleting rows (needed for proper shutdown)
        pass
        
        if cfg.NETWORK_ENABLED and hasattr(board, 'server') and board.server:
            board.server.terminate()

        if cfg.CACHE_ENABLED:
            for pawn in board.pawns:
                if pawn.AI is not None:
                    pawn.AI.flush_cache()

    pygame.quit()
    log('Exiting. Bye!')
    return 0


if __name__ == '__main__':
    main()
