# -*- coding: utf-8 -*-

import re
import random
from typing import List, Union, Tuple, Set
import collections  # NEW: for a tiny loop-detection deque

from helpers import log, LogLevel
import core
import config as cfg
from config import INF
from cache import PersistentDict

from entities.wall import Wall
from entities.coord import Coord
from .action import Action, ActionPlaceWall, ActionMovePawn, ActionPowerBomb

# ---------------------------------------------------------------------------
# Heuristic weights (pure numeric, no if/else branches).
# Tune at will – these play nicely at all levels.
#   • URGENCY_W   – how much to punish letting the opponent get close.
#   • PROGRESS_W  – how much to reward getting close to our own goal.
#   • LOOP_PENALTY – tiny cost for repeating a board state (breaks oscillation).
# ---------------------------------------------------------------------------
URGENCY_W    = 12.0
PROGRESS_W   = 5.0
LOOP_PENALTY = 0.2

class AI:
    """ This class implements the game AI.
    It could be use to implement an Strategy pattern
    """
    def __init__(self, pawn, level=1):
        self.level = level  # Level of difficulty
        self.board = pawn.board
        if cfg.CACHE_ENABLED:
            self._memoize_think = PersistentDict(cfg.CACHE_AI_FNAME, flag='c')
        else:
            self._memoize_think = {}

        pawn.AI = self
        log('Player %i is moved by computers A.I. with level %i' % (pawn.id, level), LogLevel.INFO)

        # Remember the last two board hashes – helps detect repetitions
        self._last_states = collections.deque(maxlen=4)

    @property
    def available_actions(self) -> List[Union[ActionPlaceWall, ActionMovePawn, ActionPowerBomb]]:
        player = self.pawn
        moves = [ActionMovePawn(player.coord, x) for x in player.valid_moves]
        
        # Sort moves to prefer forward movement (avoid loops)
        if hasattr(player, '_move_history') and player._move_history:
            # Score moves based on how recently they were visited
            def move_score(move):
                if move.dest in player._move_history:
                    # The more recent, the worse the score (higher number = worse)
                    return len(player._move_history) - player._move_history.index(move.dest)
                return 0  # Never visited = best score
            
            # Sort by score (ascending = better moves first)
            result = sorted(moves, key=move_score)
        else:
            result = moves

        # Add power bomb action if available
        if player.power_bombs > 0:
            result.append(ActionPowerBomb(player.coord))

        if not player.walls:  # Out of walls?
            return self._order_actions(result)

        k = self.board.state[1 + 4 * len(self.board.pawns):]
        try:
            wall_actions = core.MEMOIZED_WALLS[k]
        except KeyError:
            # Generate strategic wall actions instead of all possible walls
            wall_actions = self._generate_strategic_walls()
            core.MEMOIZED_WALLS[k] = wall_actions

        return self._order_actions(result + wall_actions)

    def _generate_strategic_walls(self) -> List[ActionPlaceWall]:
        """Generate only strategically relevant wall positions"""
        strategic_positions = self._get_strategic_positions()
        color = self.board[0][0].wall_color
        wall_actions = []
        
        # Quick collision check cache
        existing_wall_coords = {(w.coord.row, w.coord.col, w.horiz) for w in self.board.walls}
        
        for coord in strategic_positions:
            for horiz in (False, True):
                # Quick collision check before expensive validation
                if (coord.row, coord.col, horiz) in existing_wall_coords:
                    continue
                    
                # Check for wall collisions with existing walls
                if self._has_wall_collision(coord, horiz):
                    continue
                    
                wall = Wall(self.board.screen, self.board, color, coord, horiz)
                if self.board.can_put_wall(wall):
                    wall_actions.append(ActionPlaceWall(wall))
        
        return wall_actions
    
    def _get_strategic_positions(self) -> Set[Coord]:
        """Identify strategic positions for wall placement"""
        strategic_positions = set()
        
        for pawn in self.board.pawns:
            # Add positions near pawns (within 2 moves)
            strategic_positions.update(self._get_positions_near_pawn(pawn, radius=2))
            
            # Add positions that block shortest paths
            strategic_positions.update(self._get_path_blocking_positions(pawn))
            
            # Add positions that create shortcuts for current player
            if pawn == self.pawn:
                strategic_positions.update(self._get_shortcut_positions(pawn))
        
        # Filter out invalid positions
        return {pos for pos in strategic_positions 
                if self.board.in_range(pos) and 
                pos.row < self.board.rows - 1 and 
                pos.col < self.board.cols - 1}
    
    def _get_positions_near_pawn(self, pawn, radius=2) -> Set[Coord]:
        """Get wall positions near a pawn"""
        positions = set()
        pawn_pos = pawn.coord
        
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if abs(dr) + abs(dc) <= radius:  # Manhattan distance
                    pos = Coord(pawn_pos.row + dr, pawn_pos.col + dc)
                    if (self.board.in_range(pos) and 
                        pos.row < self.board.rows - 1 and 
                        pos.col < self.board.cols - 1):
                        positions.add(pos)
        
        return positions
    
    def _get_path_blocking_positions(self, pawn) -> Set[Coord]:
        """Get positions that would block pawn's shortest path"""
        positions = set()
        
        # Get pawn's current shortest path
        try:
            path = pawn.distances.shortest_path
            if path and len(path) > 1:
                # Add wall positions that would block this path
                for i in range(len(path) - 1):
                    current = path[i]
                    next_pos = path[i + 1]
                    
                    # Add wall positions that would block movement between current and next
                    blocking_walls = self._get_blocking_wall_positions(current, next_pos)
                    positions.update(blocking_walls)
        except:
            # Fallback: use positions in front of pawn
            pawn_pos = pawn.coord
            if pawn in self.board.pawns[1:]:  # AI pawns
                # Block forward movement toward goal
                if pawn_pos.row > 0:
                    positions.add(Coord(pawn_pos.row - 1, max(0, pawn_pos.col - 1)))
                    positions.add(Coord(pawn_pos.row - 1, pawn_pos.col))
            else:  # Human pawn
                # Block backward movement toward goal
                if pawn_pos.row < self.board.rows - 2:
                    positions.add(Coord(pawn_pos.row + 1, max(0, pawn_pos.col - 1)))
                    positions.add(Coord(pawn_pos.row + 1, pawn_pos.col))
        
        return positions
    
    def _get_shortcut_positions(self, pawn) -> Set[Coord]:
        """Get positions that create shortcuts for the pawn"""
        positions = set()
        pawn_pos = pawn.coord
        
        # Add positions that could redirect opponent's path
        for other_pawn in self.board.pawns:
            if other_pawn != pawn:
                # Add positions between current pawn and opponent
                mid_row = (pawn_pos.row + other_pawn.coord.row) // 2
                mid_col = (pawn_pos.col + other_pawn.coord.col) // 2
                
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        pos = Coord(mid_row + dr, mid_col + dc)
                        if (self.board.in_range(pos) and 
                            pos.row < self.board.rows - 1 and 
                            pos.col < self.board.cols - 1):
                            positions.add(pos)
        
        return positions
    
    def _get_blocking_wall_positions(self, pos1: Coord, pos2: Coord) -> Set[Coord]:
        """Get wall positions that would block movement between two adjacent positions"""
        positions = set()
        
        if pos1.row == pos2.row:  # Horizontal movement
            # Vertical wall blocks horizontal movement
            wall_row = min(pos1.row, self.board.rows - 2)
            wall_col = min(pos1.col, pos2.col)
            if wall_col < self.board.cols - 1:
                positions.add(Coord(wall_row, wall_col))
        elif pos1.col == pos2.col:  # Vertical movement
            # Horizontal wall blocks vertical movement
            wall_row = min(pos1.row, pos2.row)
            wall_col = min(pos1.col, self.board.cols - 2)
            if wall_row < self.board.rows - 1:
                positions.add(Coord(wall_row, wall_col))
        
        return positions
    
    def _has_wall_collision(self, coord: Coord, horiz: bool) -> bool:
        """Quick check for wall collisions without creating Wall object"""
        for wall in self.board.walls:
            if wall.coord == coord:
                return True  # Same position
            if wall.horiz == horiz:
                # Same orientation - check for overlap
                if horiz:  # Both horizontal
                    if (wall.coord.row == coord.row and 
                        abs(wall.coord.col - coord.col) == 1):
                        return True
                else:  # Both vertical
                    if (wall.coord.col == coord.col and 
                        abs(wall.coord.row - coord.row) == 1):
                        return True
            else:
                # Different orientations - check for intersection
                if (wall.coord.row == coord.row and 
                    wall.coord.col == coord.col):
                    return True
        return False
    
    def _order_actions(self, actions: List[Union[ActionPlaceWall, ActionMovePawn, ActionPowerBomb]]) -> List[Union[ActionPlaceWall, ActionMovePawn, ActionPowerBomb]]:
        """Order actions for better alpha-beta pruning"""
        def action_priority(action):
            if isinstance(action, ActionMovePawn):
                # Prioritize forward moves toward goal
                move_score = self._evaluate_move_priority(action)
                return (0, -move_score)  # Lower number = higher priority
            elif isinstance(action, ActionPowerBomb):
                return (1, 0)  # Power bombs have medium priority
            else:  # ActionPlaceWall
                # Prioritize defensive walls
                wall_score = self._evaluate_wall_priority(action)
                return (2, -wall_score)  # Lower number = higher priority
        
        return sorted(actions, key=action_priority)
    
    def _evaluate_move_priority(self, action: ActionMovePawn) -> float:
        """Evaluate move priority for action ordering"""
        dest = action.dest
        current_pos = self.pawn.coord
        
        # Prioritize moves toward goal
        if self.pawn.color == cfg.PAWN_A_COL:  # Human (red) - goal is top
            goal_distance = dest.row  # Lower row = closer to goal
        else:  # AI (blue) - goal is bottom
            goal_distance = self.board.rows - 1 - dest.row  # Higher row = closer to goal
        
        # Prioritize moves that get closer to goal
        if self.pawn.color == cfg.PAWN_A_COL:
            progress = current_pos.row - dest.row  # Positive = moving toward goal
        else:
            progress = dest.row - current_pos.row  # Positive = moving toward goal
        
        return progress * 10 - goal_distance  # Higher score = better move
    
    def _evaluate_wall_priority(self, action: ActionPlaceWall) -> float:
        """Evaluate wall priority for action ordering"""
        wall_coord = action.coord
        
        # Prioritize walls closer to opponent
        min_distance_to_opponent = float('inf')
        for pawn in self.board.pawns:
            if pawn != self.pawn:
                distance = abs(wall_coord.row - pawn.coord.row) + abs(wall_coord.col - pawn.coord.col)
                min_distance_to_opponent = min(min_distance_to_opponent, distance)
        
        # Prioritize walls that block opponent's forward movement
        blocking_score = 0
        for pawn in self.board.pawns:
            if pawn != self.pawn:
                # Check if wall blocks opponent's path toward goal
                if pawn.color == cfg.PAWN_A_COL:  # Opponent wants to go up
                    if action.horiz and wall_coord.row <= pawn.coord.row:
                        blocking_score += 5
                else:  # Opponent wants to go down
                    if action.horiz and wall_coord.row >= pawn.coord.row:
                        blocking_score += 5
        
        return blocking_score - min_distance_to_opponent

    def clean_memo(self):
        """ Removes useless state from the memoized cache.
        """
        if cfg.CACHE_ENABLED:
            return  # Do not delete anything if cache enabled

        L = 1 + len(self.board.pawns) * 4
        k = self.board.state[L:]
        k = '.' * L + k.replace('1', '.') + '$'
        r = re.compile(k)

        for q in list(self._memoize_think.keys()):
            if not r.match(q):
                del self._memoize_think[q]

    def move(self) -> Tuple[Action, int]:
        """ Return best move according to the deep level using isolated board state calculation
        """
        # Check if I can win immediately
        for coord in self.pawn.valid_moves:
            if coord in self.pawn.goals:
                return ActionMovePawn(self.pawn.coord, coord), -INF

        # Create isolated copy of board for calculation
        original_board = self.board
        original_pawn_id = self.pawn.id
        original_pawn = self.pawn  # Keep reference to original pawn for progress updates
        calculation_board = self.board.create_ai_copy()
        
        # Temporarily switch AI to work with calculation board
        self.board = calculation_board
        # Set the AI board's current player to match the AI's pawn
        # Find the index of the pawn in the calculation board
        for i, pawn in enumerate(calculation_board.pawns):
            if pawn.id == original_pawn_id:
                calculation_board.player = i
                break
        
        # Link progress updates: calculation board pawn updates original pawn's progress
        # Find the corresponding pawn in the calculation board
        calculation_pawn = None
        for pawn in calculation_board.pawns:
            if pawn.id == original_pawn_id:
                calculation_pawn = pawn
                break
        
        if calculation_pawn:
            calculation_pawn._original_pawn = original_pawn
            calculation_pawn.percent = None  # Initialize progress tracking
        
        try:
            # PURE HEURISTIC APPROACH: Let minimax find the best move based on evaluation scores
            # No emergency blocking - everything is handled by heuristic weights
            
            original_pawn.percent = 0  # Initialize progress on original pawn
            move, h, alpha, beta = self.think(True)  # AI is always MAX player
            self.clean_memo()
            self.distances.clean_memo()
            
        finally:
            # Always restore original board reference
            self.board = original_board
            
        return move, h

    def do_action(self, action: Union[ActionPlaceWall, ActionMovePawn, ActionPowerBomb]):
        """ Simulates the action en background
        """
        if isinstance(action, ActionPlaceWall):
            # FIXED: Store the actual wall object for proper undo
            action._wall_object = self.board.new_wall(action.coord, action.horiz)
            self.board.putWall(action._wall_object)
            self.pawn.walls -= 1
        elif isinstance(action, ActionPowerBomb):
            # Store walls before power bomb for undo
            action._destroyed_walls = []
            action._wall_returns = {}
            
            # SAFETY: Validate power bomb is available
            if self.pawn.power_bombs <= 0:
                return  # Cannot use power bomb
            
            # Find walls to destroy (create a copy of walls list to avoid modification during iteration)
            walls_copy = list(self.board.walls)
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    affected_coord = Coord(action.center.row + dr, action.center.col + dc)
                    if not self.board.in_range(affected_coord):
                        continue
                    
                    walls_to_remove = []
                    for wall in walls_copy:
                        if self.board.wall_affects_coord(wall, affected_coord):
                            walls_to_remove.append(wall)
                    
                    for wall in walls_to_remove:
                        if wall not in action._destroyed_walls:
                            action._destroyed_walls.append(wall)
                            # SAFETY: Check wall still exists before removing
                            if wall in self.board.walls:
                                self.board.removeWall(wall)
                                
                                # Track wall returns with safety check
                                owner_id = getattr(wall, 'owner_id', None)
                                if owner_id is not None and 0 <= owner_id < len(self.board.pawns):
                                    action._wall_returns[owner_id] = action._wall_returns.get(owner_id, 0) + 1
            
            # Return walls to owners
            for owner_id, count in action._wall_returns.items():
                if 0 <= owner_id < len(self.board.pawns):  # Safety check
                    self.board.pawns[owner_id].walls += count
            
            self.pawn.power_bombs -= 1
        else:  # ActionMovePawn
            self.pawn.move_to(action.dest)

        # Record board state after applying the action (for loop penalty)
        self._last_states.append(self.board.state)

        # Note: Heuristic evaluation is done inside think(); do_action returns None.

    def undo_action(self, action: Union[ActionPlaceWall, ActionMovePawn, ActionPowerBomb]):
        """ Reverts a given action
        """
        if isinstance(action, ActionPlaceWall):
            # FIXED: Use the same wall object that was placed
            if hasattr(action, '_wall_object'):
                self.board.removeWall(action._wall_object)
            else:
                # Fallback for old actions (shouldn't happen in normal use)
                self.board.removeWall(self.board.new_wall(action.coord, action.horiz))
            self.pawn.walls += 1
        elif isinstance(action, ActionPowerBomb):
            # Restore destroyed walls
            for wall in action._destroyed_walls:
                # SAFETY: Only restore wall if it's not already on the board
                if wall not in self.board.walls:
                    self.board.putWall(wall)
            
            # Remove walls that were returned to owners
            for owner_id, count in action._wall_returns.items():
                if 0 <= owner_id < len(self.board.pawns):  # Safety check
                    self.board.pawns[owner_id].walls -= count
            
            self.pawn.power_bombs += 1
        else:  # ActionMovePawn
            self.pawn.move_to(action.orig)

    def think(self, is_max: bool, ilevel=0, alpha=INF, beta=-INF):
        """ Returns best movement with the given level of
        analysis, and returns it as a Wall (if a wall
        must be put) or as a coordinate pair.

        MAX is a boolean with tells if this function is
        looking for a MAX (True) value or a MIN (False) value.
        """
        k = str(ilevel) + self.board.state[1:]
        try:
            r = self._memoize_think[k]
            core.MEMOIZED_NODES_HITS += 1
            return r
        except KeyError:
            core.MEMOIZED_NODES += 1
            pass

        result = None
        # __DEBUG__
        # print(alpha, beta)
        stop = False

        if ilevel >= self.level:  # OK we must return the movement
            HH = -INF if is_max else INF  # FIXED: Initialize correctly for MAX/MIN
            h0 = self.distances.shortest_path_len
            hh0 = self.board.pawns[(self.board.player + 1) % 2].distances.shortest_path_len
            # next_player = (self.board.player + 1) % len(self.board.pawns)

            for action in self.available_actions:
                self.do_action(action)

                p = self.pawn
                self.board.update_pawns_distances()
                
                # SAFETY: Validate board state after action
                if cfg.__DEBUG__:
                    for pawn in self.board.pawns:
                        if not pawn.valid_moves and pawn.coord not in pawn.goals:
                            log(f'WARNING: Pawn {pawn.id} has no valid moves at {pawn.coord} - possible board corruption')
                
                h1 = self.distances.shortest_path_len
                hh1 = min([pawn.distances.shortest_path_len
                           for pawn in self.board.pawns if pawn is not p])
                # (simple difference computed in base variable below)
                base      = h1 - hh1
                urgency   = URGENCY_W  / (hh1 + 0.5) ** 2
                progress  = -PROGRESS_W / (h1 + 0.5) ** 2
                loop_pen  = LOOP_PENALTY if self.board.state in self._last_states else 0.0
                h         = base + urgency + progress + loop_pen

                # Tiny random jitter to break exact ties when state not repeated
                if abs(h - HH) < 1e-9 and self.board.state not in self._last_states:
                    h += (random.random() - 0.5) * 0.01
                
                # Simplified debug output - only for serious debugging
                # (Removed verbose move evaluation to clean up console output)
                
                # That's it! Let minimax do its job.
                # The algorithm should naturally:
                # - Block immediate threats (they result in terrible h values)
                # - Avoid bad power bomb usage (it worsens our position)
                # - Choose good moves (they improve our relative position)
                
                # (old manhattan tie-break removed; handled by progress term)

                if is_max:
                    h = -h
                    if h > HH:
                        HH = h
                        result = action

                        if HH >= alpha:
                            alpha = HH  # FIXED: Update alpha, don't overwrite HH
                            stop = True
                elif h < HH:  # MIN
                    HH = h
                    result = action

                    if HH <= beta:
                        beta = HH   # FIXED: Update beta, don't overwrite HH
                        stop = True

                elif h == HH:  # Tie-breaking logic for all levels
                    # Random tie-breaking - academically sound and simple
                    if random.random() < 0.5:
                        result = action

                self.undo_action(action)
                if stop:
                    break

            self._memoize_think[k] = result, HH, alpha, beta
            return result, HH, alpha, beta

        # Not a leaf in the search tree. Alpha-Beta minimax
        HH = -INF if is_max else INF
        player = self.board.current_player
        player.distances.push_state()
        r = self.available_actions
        count_r = 0
        L = float(len(r))

        for action in r:
            if not ilevel:
                count_r += 1
                # Update progress on original pawn if linked, otherwise on current player
                if hasattr(player, '_original_pawn') and player._original_pawn is not None:
                    player._original_pawn.percent = count_r / L  # [0..1]
                elif player.percent is not None:
                    player.percent = count_r / L  # [0..1]
                # Progress updates handled by main thread only - no GUI calls from background thread

            self.do_action(action)
            self.board.next_player()
            dummy, h, alpha1, beta1 = self.think(not is_max, ilevel + 1, alpha, beta)
            # __DEBUG__
            # print action, '|', dummy, h, '<<<'
            self.previous_player()

            if is_max:
                # __DEBUG__
                # print h, HH
                if h > HH:  # MAX
                    result, HH = action, h
                    if HH >= alpha:
                        alpha = HH  # FIXED: Update alpha, don't overwrite HH
                        stop = True
                    else:
                        beta = HH
            else:
                if h < HH:  # MIN
                    result, HH = action, h
                    if HH <= beta:
                        beta = HH   # FIXED: Update beta, don't overwrite HH
                        stop = True
                    else:
                        alpha = HH

            self.undo_action(action)
            if stop:
                break

        player.distances.pop_state()
        self._memoize_think[k] = result, HH, alpha, beta
        # DEBUG__
        # print(result)
        return result, HH, alpha, beta

    @property
    def pawn(self):
        return self.board.current_player

    @property
    def distances(self):
        return self.pawn.distances

    def previous_player(self):
        """ Switches to previous player.
        """
        self.board.player = (self.board.player + self.board.num_players - 1) % self.board.num_players

    def flush_cache(self):
        if isinstance(self._memoize_think, PersistentDict):
            self._memoize_think.close()
