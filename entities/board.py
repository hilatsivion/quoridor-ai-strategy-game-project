# -*- coding: utf-8 -*-

from typing import Set, List, Union
import pygame

from helpers import log
from network.server import EnhancedServer, Functions
import config as cfg

from ai.action import ActionMovePawn, ActionPlaceWall, ActionPowerBomb
from ai.ai import AI

from .drawable import Drawable
from .pawn import Pawn
from .cell import Cell
from .wall import Wall
from .coord import Coord

from config import DIR
from menu import Button


class Board(Drawable):
    """ Quoridor board.
    This object contains te state of the game.
    """

    def __init__(self,
                 screen: pygame.Surface,
                 rows=cfg.DEF_ROWS,
                 cols=cfg.DEF_COLS,
                 walls_per_player=cfg.NUM_WALLS,
                 cell_padding=cfg.CELL_PAD,
                 color=cfg.BOARD_BG_COLOR,
                 border_color=cfg.BOARD_BRD_COLOR,
                 border_size=cfg.BOARD_BRD_SIZE,
                 cell_width=cfg.CELL_WIDTH,
                 cell_height=cfg.CELL_HEIGHT):

        Drawable.__init__(self, screen=screen, color=color, border_color=border_color, border_size=border_size)
        self.rows: int = rows
        self.cols: int = cols
        self.cell_pad = cell_padding
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.mouse_wall = None  # Wall painted on mouse move
        self.player: int = 0  # Current player 0 or 1
        self.board: List[List[Cell]] = []
        self.computing = False  # True if a non-human player is moving
        self._state = None
        
        # Visual state preservation no longer needed - AI uses isolated calculation

        # Create NETWORK server
        try:
            if cfg.NETWORK_ENABLED:
                self.server = EnhancedServer(("localhost", cfg.PORT))
                log('Network server active at TCP PORT ' + str(cfg.PORT))
                self.server.register_introspection_functions()
                self.server.register_instance(Functions())
                self.server.start()
        except BaseException:
            log('Could not start network server')
            self.server = None

        for i in range(rows):
            self.board.append([])
            for j in range(cols):
                self.board[-1].append(Cell(screen, self, coord=Coord(i, j)))

        self.pawns: List[Pawn] = []
        self.pawns += [Pawn(screen=screen,
                            board=self,
                            color=cfg.PAWN_A_COL,
                            border_color=cfg.PAWN_BORDER_COL,
                            coord=Coord(rows - 1, cols >> 1),  # Centered
                            walls=walls_per_player
                            # URL = SERVER_URL + ':%i' % (BASE_PORT + PAWNS)
                            )]
        self.pawns += [Pawn(screen=screen,
                            board=self,
                            color=cfg.PAWN_B_COL,
                            border_color=cfg.PAWN_BORDER_COL,
                            coord=Coord(0, col=cols >> 1),  # Centered
                            walls=walls_per_player
                            )]

        self.regenerate_board(cfg.CELL_COLOR, cfg.CELL_BORDER_COLOR, self.cell_width, self.cell_height)
        self.num_players = cfg.DEFAULT_NUM_PLAYERS
        self.walls: Set[Wall] = set()  # Walls placed on board
        self.draw_players_info()
        self._AI = []
        # self._AI += [AI(self.pawns[0])]
        self._AI += [AI(self.pawns[1], level=cfg.LEVEL)]
        
        # Initialize game control buttons
        self._init_game_buttons()

    def _init_game_buttons(self):
        """Initialize Reset and Exit buttons for the game UI"""
        button_width = 80
        button_height = 35
        button_spacing = 15
        
        # Position buttons in the right side area (where player info is shown)
        # Use the same x position as the player info panel
        buttons_x = self.rect.x + self.rect.width + cfg.PAWN_PADDING
        
        # Position buttons at the top of the right side area
        buttons_start_y = 20  # Start closer to the top to provide more space below
        
        # Reset button - positioned at the top of the right side area
        self.reset_button = Button(
            buttons_x, buttons_start_y, button_width, button_height,
            "Reset", (150, 180, 220), (255, 255, 255),
            lambda: self._reset_game()
        )
        
        # Exit button - positioned below the reset button
        self.exit_button = Button(
            buttons_x, buttons_start_y + button_height + button_spacing,
            button_width, button_height,
            "Exit", (220, 150, 150), (255, 255, 255),
            lambda: self._exit_game()
        )
        
        self.game_buttons = [self.reset_button, self.exit_button]
        
        # Button action flags for communication with main game loop
        self.reset_requested = False
        self.exit_requested = False

    def _reset_game(self):
        """Set flag to request game reset"""
        self.reset_requested = True

    def _exit_game(self):
        """Set flag to request exit to menu"""
        self.exit_requested = True

    def handle_button_events(self, event):
        """Handle button events and return True if a button was interacted with"""
        for button in self.game_buttons:
            if button.handle_event(event):
                return True
        return False

    def regenerate_board(self, c_color, cb_color, c_width=None, c_height=None):
        """ Regenerate board colors and get_cell positions.
        Must be called on initialization or whenever a screen attribute
        changes (eg. color, board size, etc)
        """
        # Use instance's dynamic cell sizes if not provided
        if c_width is None:
            c_width = self.cell_width
        if c_height is None:
            c_height = self.cell_height
            
        y = self.cell_pad
        for i in range(self.rows):
            x = self.cell_pad
            for j in range(self.cols):
                cell = self.board[i][j]
                cell.x, cell.y = x, y
                cell.color = c_color
                cell.border_color = cb_color
                cell.height = c_height
                cell.width = c_width
                cell.pawn = None
                x += c_width + self.cell_pad
            y += c_height + self.cell_pad

        for pawn in self.pawns:
            pawn.cell = self.get_cell(pawn.coord)

    def draw(self):
        """ Draws a squared n x n board, defaults
        to the standard 9 x 9
        """
        super().draw()

        for row in self:
            for cell in row:
                cell.draw()

        # Draw walls
        for wall in self.walls:
            wall.draw()
        
        # Draw wall preview if mouse is hovering over a valid wall position
        if self.mouse_wall is not None:
            self.mouse_wall.draw_preview()
            
        # Draw game control buttons
        for button in self.game_buttons:
            button.draw(self.screen)

    def get_cell(self, coord: Coord) -> Cell:
        """ Returns board get_cell at the given the coord
        """
        return self.board[coord.row][coord.col]

    def set_cell(self, coord: Coord, value: Cell):
        """ Updates a cell in the board with the new Cell
        instance at the given coord
        """
        self.board[coord.row][coord.col] = value

    def __getitem__(self, i: int) -> List[Cell]:
        return self.board[i]

    def in_range(self, coord: Coord) -> bool:
        """ Returns whether te given coordinate are within the board or not
        """
        return 0 <= coord.col < self.cols and 0 <= coord.row < self.rows

    def putWall(self, wall: Wall) -> None:
        """ Puts the given wall on the board.
        The cells are updated accordingly
        """
        if wall in self.walls:
            return  # If already put, nothing to do

        self.walls.add(wall)
        i, j = wall.coord

        if wall.horiz:
            # Horizontal wall - blocks north-south movement
            if self.in_range(Coord(i, j)):
                self.board[i][j].set_path(DIR.S, False)
            if self.in_range(Coord(i, j + 1)):
                self.board[i][j + 1].set_path(DIR.S, False)
        else:
            # Vertical wall - blocks east-west movement  
            if self.in_range(Coord(i, j)):
                self.board[i][j].set_path(DIR.W, False)
            if self.in_range(Coord(i + 1, j)):
                self.board[i + 1][j].set_path(DIR.W, False)

        self._state = None

    def removeWall(self, wall: Wall) -> None:
        """ Removes a wall from the board.
        The cells are updated accordingly
        """
        if wall not in self.walls:
            return  # Already removed, nothing to do

        self.walls.remove(wall)
        i, j = wall.coord

        if wall.horiz:
            # Horizontal wall - restore north-south movement
            if self.in_range(Coord(i, j)):
                self.board[i][j].set_path(DIR.S, True)
            if self.in_range(Coord(i, j + 1)):
                self.board[i][j + 1].set_path(DIR.S, True)
        else:
            # Vertical wall - restore east-west movement
            if self.in_range(Coord(i, j)):
                self.board[i][j].set_path(DIR.W, True)
            if self.in_range(Coord(i + 1, j)):
                self.board[i + 1][j].set_path(DIR.W, True)

        self._state = None

    def onMouseClick(self, x, y):
        """ Dispatch mouse click Event
        """
        # Check for button clicks first (they take priority)
        for button in self.game_buttons:
            if button.rect.collidepoint(x, y):
                # Button click will be handled via its action callback
                return

        cell = self.which_cell(x, y)
        if cell is not None:
            pawn = self.current_player
            if not pawn.can_move(cell.coord):
                return

            self.do_action(ActionMovePawn(pawn.coord, cell.coord))
            cell.set_focus(False)
            self.draw()

            if self.finished:
                self.draw_player_info(self.player)
                return

            self.next_player()
            self.draw_players_info()
            return

        wall = self.wall(x, y)
        if not wall:
            return

        if self.can_put_wall(wall):
            self.do_action(ActionPlaceWall(wall))
            self.next_player()
            self.draw_players_info()

    def onMouseMotion(self, x, y):
        """ Get mouse motion event and acts accordingly
        """
        if not self.rect.collidepoint(x, y):
            return

        for row in self.board:
            for cell in row:
                cell.onMouseMotion(x, y)

        if self.which_cell(x, y):
            # Clear wall preview when mouse is over a cell
            self.mouse_wall = None
            return  # The focus was on a get_cell, we're done

        # Check walls availability
        if not self.current_player.walls:
            return  # The current player has run out of walls. We're done

        wall = self.wall(x, y)
        if not wall:
            # Clear any existing wall preview
            self.mouse_wall = None
            return

        if self.can_put_wall(wall):
            # Update mouse wall for preview (will be drawn in main draw cycle)
            self.mouse_wall = wall
        else:
            # Can't place wall here, clear any existing preview
            self.mouse_wall = None

    def can_put_wall(self, wall) -> bool:
        """ Returns whether the given wall can be put
        on the board.
        """
        if not self.current_player.walls:
            return False

        # Quick collision check - cheaper than full collision detection
        for w in self.walls:
            if wall.collides(w):
                return False

        # Optimized pathfinding check - only test if wall placement would block any pawn
        result = True
        self.putWall(wall)

        # Check reachability for all pawns - but stop at first failure for speed
        for pawn in self.pawns:
            if not pawn.can_reach_goal():
                result = False
                break

        self.removeWall(wall)
        return result

    def wall(self, x, y) -> Union[Wall, None]:
        """ Factory which returns which wall is below mouse cursor at x, y coords.
        Returns None if no wall matches x, y coords
        """
        if not self.rect.collidepoint(x, y):
            return None

        # Wall: Guess which top-left get_cell is it
        j = (x - self.x) // (self.board[0][0].width + self.cell_pad)
        i = (y - self.y) // (self.board[0][0].height + self.cell_pad)
        
        # Check bounds for cell indices
        if i < 0 or i >= self.rows or j < 0 or j >= self.cols:
            return None
            
        cell = self.board[i][j]

        # Wall: Guess if it is horizontal or vertical
        horiz = x < (cell.x + cell.width)
        
        # Dynamic wall bounds based on actual board size
        max_wall_index = self.rows - 2  # For walls, valid indices are 0 to (size-2)
        if horiz:
            if j > max_wall_index:
                j = max_wall_index
        else:
            if i > max_wall_index:
                i = max_wall_index

        # Check if wall coordinates are valid
        if i > max_wall_index or j > max_wall_index or i < 0 or j < 0:
            return None

        return self.new_wall(Coord(i, j), horiz, cell.wall_color)

    def new_wall(self, coord: Coord, horiz: bool, color: pygame.Color = None) -> Wall:
        """ Wall factory. Creates a new wall
        """
        if color is None:
            color = self.board[0][0].wall_color
        # Pass current player's ID as owner - with safety check
        owner_id = None
        if hasattr(self, 'current_player') and self.current_player is not None:
            owner_id = self.current_player.id
        return Wall(self.screen, self, color, coord, horiz, owner_id)

    @property
    def x(self):
        """ Absolute left coordinate
        """
        return self.board[0][0].x

    @property
    def y(self):
        """ Absolute left coordinate
        """
        return self.board[0][0].y

    @property
    def width(self):
        return (self.cell_pad + self.board[0][0].width) * self.cols

    @property
    def height(self):
        return (self.cell_pad + self.board[0][0].height) * self.rows

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def next_player(self):
        """ Switches to next player
        """
        self.player = (self.player + 1) % self.num_players
        self.update_pawns_distances()

    def update_pawns_distances(self):
        for pawn in self.pawns:
            pawn.distances.update()

    def which_cell(self, x, y):
        """ Returns an instance of the get_cell for which (x, y) screen coord
        matches. Otherwise, returns None if no get_cell is at (x, y) screen
        coords.
        """
        for row in self.board:
            for cell in row:
                if cell.rect.collidepoint(x, y):
                    return cell

        return None

    @property
    def current_player(self):
        """ Returns current player's pawn
        """
        return self.pawns[self.player]

    def draw_player_info(self, player_num):
        """ Draws player pawn at board + padding_offset with enhanced display
        """
        pawn = self.pawns[player_num]
        r = pawn.rect
        r.x = self.rect.x + self.rect.width + cfg.PAWN_PADDING
        
        # Position player info below the buttons with sufficient spacing
        # Calculate height needed for button area: start_y + 2 buttons + spacing
        button_area_height = 20 + 35 + 15 + 35  # buttons_start_y + button_height + spacing + button_height
        player_info_start_y = button_area_height + 40  # More margin below buttons to prevent overlap
        r.y = player_info_start_y + (player_num * (r.height + cfg.PAWN_PADDING + 40))  # Start below buttons
        
        # Player name above the pawn
        player_name = "Player" if player_num == 0 else "AI"
        name_color = pawn.color if not pawn.AI else (80, 120, 220)
        font = pygame.font.SysFont(None, 28, bold=True)
        name_surface = font.render(player_name, True, name_color)
        name_rect = name_surface.get_rect(center=(r.x + r.width // 2, r.y - 20))
        
        # Clear area around name
        clear_rect = pygame.Rect(name_rect.x - 5, name_rect.y - 2, 
                                name_rect.width + 10, name_rect.height + 4)
        pygame.draw.rect(self.screen, cfg.BOARD_BG_COLOR, clear_rect, 0)
        self.screen.blit(name_surface, name_rect)
        
        # Highlight current player
        is_current_player = (self.current_player is pawn)
            
        if is_current_player:
            pygame.draw.rect(self.screen, cfg.CELL_VALID_COLOR, r, 0)
            pygame.draw.rect(self.screen, pawn.border_color, r, 3)
        else:
            pygame.draw.rect(self.screen, self.color, r, 0)

        pawn.draw(r)
        
        # AI Progress bar - positioned under AI pawn circle
        if pawn.AI and pawn.percent is not None:
            progress_rect = pygame.Rect(r.x - 10, r.y + r.height + 8, cfg.GAUGE_WIDTH + 20, 8)
            # Clear background
            pygame.draw.rect(self.screen, cfg.BOARD_BG_COLOR, 
                           pygame.Rect(progress_rect.x - 2, progress_rect.y - 2, 
                                     progress_rect.width + 4, progress_rect.height + 4), 0)
            # Progress background
            pygame.draw.rect(self.screen, (200, 200, 200), progress_rect, 0)
            pygame.draw.rect(self.screen, (120, 120, 120), progress_rect, 1)
            
            # Progress fill
            fill_width = int(progress_rect.width * pawn.percent)
            if fill_width > 0:
                fill_rect = pygame.Rect(progress_rect.x, progress_rect.y, fill_width, progress_rect.height)
                pygame.draw.rect(self.screen, (100, 150, 250), fill_rect, 0)
            
            # Progress text
            progress_text = f"Thinking... {int(pawn.percent * 100)}%"
            progress_font = pygame.font.SysFont(None, 18)
            progress_surface = progress_font.render(progress_text, True, (60, 80, 120))
            progress_text_rect = progress_surface.get_rect(center=(r.x + r.width // 2, progress_rect.y + progress_rect.height + 15))
            
            # Clear text area
            text_clear_rect = pygame.Rect(progress_text_rect.x - 2, progress_text_rect.y - 1,
                                        progress_text_rect.width + 4, progress_text_rect.height + 2)
            pygame.draw.rect(self.screen, cfg.BOARD_BG_COLOR, text_clear_rect, 0)
            self.screen.blit(progress_surface, progress_text_rect)

        # Wall count display
        wall_x = r.x + r.width + 20
        wall_y = r.y + r.height // 2 - 5
        
        # Wall icon
        wall_rect = pygame.Rect(wall_x, wall_y, 6, cfg.FONT_SIZE)
        pygame.draw.rect(self.screen, cfg.WALL_COLOR, wall_rect, 0)
        
        # Wall count
        wall_count_x = wall_x + 20
        wall_count_rect = pygame.Rect(wall_count_x, wall_y, 30, cfg.FONT_SIZE)
        pygame.draw.rect(self.screen, cfg.FONT_BG_COLOR, wall_count_rect, 0)  # Clear area
        
        self.msg(wall_count_x, wall_y, str(pawn.walls))

        # Power bomb display
        bomb_x = wall_count_x + 40
        center_x = bomb_x + 6
        center_y = wall_y + cfg.FONT_SIZE // 2
        
        # Clear bomb area
        pygame.draw.circle(self.screen, cfg.FONT_BG_COLOR, (center_x, center_y), 8, 0)
        
        # Draw bomb icon based on current count
        if pawn.power_bombs > 0:
            pygame.draw.circle(self.screen, (255, 120, 0), (center_x, center_y), 6, 0)  # Orange bomb
        else:
            pygame.draw.circle(self.screen, (150, 150, 150), (center_x, center_y), 6, 0)  # Gray (used)
        
        # Power bomb count
        bomb_count_x = bomb_x + 20
        bomb_count_rect = pygame.Rect(bomb_count_x, wall_y, 20, cfg.FONT_SIZE)
        pygame.draw.rect(self.screen, cfg.FONT_BG_COLOR, bomb_count_rect, 0)  # Clear area
        self.msg(bomb_count_x, wall_y, str(pawn.power_bombs))

        # Win message - positioned below status area
        if self.finished and (self.current_player == pawn):
            win_message = f"{player_name.upper()} WINS!"
            win_font = pygame.font.SysFont(None, 36, bold=True)
            win_surface = win_font.render(win_message, True, (220, 50, 50))
            
            # Position below the board, in center
            board_bottom = self.rect.y + self.rect.height + 45  # Below power bomb instruction
            win_rect = win_surface.get_rect(center=(self.rect.x + self.rect.width // 2, board_bottom))
            
            # Clear background for win message
            win_clear_rect = pygame.Rect(win_rect.x - 10, win_rect.y - 5,
                                       win_rect.width + 20, win_rect.height + 10)
            pygame.draw.rect(self.screen, cfg.BOARD_BG_COLOR, win_clear_rect, 0)
            pygame.draw.rect(self.screen, (255, 255, 255), win_clear_rect, 2)
            self.screen.blit(win_surface, win_rect)
            
            # Exit instruction below win message
            exit_y = win_rect.y + win_rect.height + 10
            exit_rect_width = 250
            exit_x = self.rect.x + (self.rect.width - exit_rect_width) // 2
            self.msg(exit_x, exit_y, "Press any key to return to menu", (100, 100, 100), cfg.FONT_SIZE + 4)

    def msg(self, x, y, str_, color=cfg.FONT_COLOR, fsize=cfg.FONT_SIZE):
        font = pygame.font.SysFont(None, fsize)
        fnt = font.render(str_, True, color)
        self.screen.blit(fnt, (x, y))

    def draw_players_info(self):
        """ Calls the above function for every player.
        """
        for i in range(len(self.pawns)):
            self.draw_player_info(i)
        
        # Show power bomb instruction below the board
        if not self.finished and self.current_player.power_bombs > 0:
            instruction_x = self.rect.x
            instruction_y = self.rect.y + self.rect.height + 10
            self.msg(instruction_x, instruction_y, "Press SPACE to detonate power bomb", cfg.FONT_COLOR, cfg.FONT_SIZE + 8)

    def do_action(self, action: Union[ActionPlaceWall, ActionMovePawn, ActionPowerBomb]):
        """ Performs a playing action: move a pawn, place a barrier, or use power bomb.
        Transmit the action to the network, to inform other players.
        """
        player_id = self.current_player.id

        if isinstance(action, ActionPlaceWall):
            wdir = 'horizontal' if action.horiz else 'vertical'
            log('Player %i places %s wall at (%i, %i)' % (player_id, wdir, action.coord.col, action.coord.row))
            self.putWall(self.new_wall(action.coord, action.horiz))
            self.current_player.walls -= 1
        elif isinstance(action, ActionPowerBomb):
            log('Player %i uses power bomb at (%i, %i)' % (player_id, action.center.row, action.center.col))
            self.execute_power_bomb(action.center)
            self.current_player.power_bombs -= 1
        else:  # ActionMovePawn
            log('Player %i moves to (%i, %i)' % (player_id, action.dest.row, action.dest.col))
            # Track move history for tie-breaking (prevent loops)
            if not hasattr(self.current_player, '_move_history'):
                self.current_player._move_history = []
            
            self.current_player._last_coord = self.current_player.coord
            self.current_player._move_history.append(self.current_player.coord)
            
            # Keep only last 4 moves to prevent long loops
            if len(self.current_player._move_history) > 4:
                self.current_player._move_history.pop(0)
            
            self.current_player.move_to(action.dest)
            self._state = None

        for pawn in self.pawns:
            if pawn.is_network_player:
                pawn.NETWORK.do_action(action)

        # ---- Loop-penalty support: record final board state in moving player's AI
        if self.current_player.AI is not None:
            try:
                self.current_player.AI._last_states.append(self.state)
            except AttributeError:
                pass

    def execute_power_bomb(self, center: Coord):
        """ Execute power bomb: destroy all walls in 3x3 area and return them to owners
        """
        destroyed_walls = []
        
        # Define 3x3 area around center
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                affected_coord = Coord(center.row + dr, center.col + dc)
                if not self.in_range(affected_coord):
                    continue
                
                # Find walls that touch this coordinate
                walls_to_remove = []
                for wall in self.walls:
                    if self.wall_affects_coord(wall, affected_coord):
                        walls_to_remove.append(wall)
                
                # Remove walls and track them
                for wall in walls_to_remove:
                    if wall not in destroyed_walls:  # Avoid duplicates
                        destroyed_walls.append(wall)
                        self.removeWall(wall)
        
        # Return walls to their owners
        wall_counts = {}  # Track how many walls each player gets back
        for wall in destroyed_walls:
            owner_id = getattr(wall, 'owner_id', None)
            if owner_id is not None and owner_id < len(self.pawns):
                wall_counts[owner_id] = wall_counts.get(owner_id, 0) + 1
        
        # Add walls back to players
        for owner_id, count in wall_counts.items():
            self.pawns[owner_id].walls += count
            log(f'Player {owner_id} gets {count} walls back from power bomb')

    def wall_affects_coord(self, wall: Wall, coord: Coord) -> bool:
        """ Check if a wall affects movement from/to a specific coordinate
        """
        wall_coord = wall.coord
        
        if wall.horiz:  # Horizontal wall
            # Horizontal wall blocks north-south movement
            # Wall at (r,c) blocks movement between (r,c)↔(r+1,c) and (r,c+1)↔(r+1,c+1)
            if ((coord.row == wall_coord.row and coord.col == wall_coord.col) or
                (coord.row == wall_coord.row and coord.col == wall_coord.col + 1) or
                (coord.row == wall_coord.row + 1 and coord.col == wall_coord.col) or
                (coord.row == wall_coord.row + 1 and coord.col == wall_coord.col + 1)):
                return True
        else:  # Vertical wall
            # Vertical wall blocks east-west movement
            # Wall at (r,c) blocks movement between (r,c)↔(r,c+1) and (r+1,c)↔(r+1,c+1)
            if ((coord.row == wall_coord.row and coord.col == wall_coord.col) or
                (coord.row == wall_coord.row and coord.col == wall_coord.col + 1) or
                (coord.row == wall_coord.row + 1 and coord.col == wall_coord.col) or
                (coord.row == wall_coord.row + 1 and coord.col == wall_coord.col + 1)):
                return True
        
        return False

    def computer_move(self):
        """ Performs computer moves for every non-human player using isolated state calculation
        """
        if not self.current_player.AI or self.finished:
            self.computing = False
            return

        # AI calculates on an isolated copy of the game state
        # This prevents any visual flickering or game state corruption
        action, x = self.current_player.AI.move()
        
        try:
            pygame.mixer.music.load('./media/chime.ogg')
            pygame.mixer.music.play()
        except pygame.error:
            pass  # Ignore mixer errors
            
        # Apply the calculated action to the real game state
        self.do_action(action)

        if not self.finished:
            self.next_player()

        self.draw()
        self.draw_players_info()
        self.computing = False

    @property
    def finished(self):
        """ Returns whether the match has finished or not.
        """
        return any(pawn.coord in pawn.goals for pawn in self.pawns)

    @property
    def state(self):
        """ Status serialization in a t-uple
        """
        if self._state is not None:
            return self._state

        result = str(self.player)  # current player
        result += ''.join(p.state for p in self.pawns)
        result += ''.join(self.board[i][j].state for j in range(self.cols - 1) for i in range(self.rows - 1))
        self._state = result

        return result



    def create_ai_copy(self):
        """Create a deep copy of the board state for AI calculation"""
        import copy
        
        # Create a new board with same dimensions
        ai_board = Board(
            screen=self.screen,
            rows=self.rows,
            cols=self.cols,
            walls_per_player=max(pawn.walls for pawn in self.pawns),  # Use max available walls
            cell_padding=self.cell_pad,
            color=self.color,
            border_color=self.border_color,
            border_size=self.border_size,
            cell_width=self.cell_width,
            cell_height=self.cell_height
        )
        
        # Copy game state
        ai_board.player = self.player
        ai_board.computing = False  # AI copy should not be in computing state
        
        # Copy pawn positions and stats (but not AI references)
        for i, pawn in enumerate(self.pawns):
            ai_board.pawns[i].coord = pawn.coord
            ai_board.pawns[i].walls = pawn.walls
            ai_board.pawns[i].power_bombs = pawn.power_bombs
            ai_board.pawns[i].id = pawn.id
            # Don't copy AI reference to avoid circular dependencies
            ai_board.pawns[i].AI = None
            
        # Copy walls and apply them to cell paths
        ai_board.walls = set()
        for wall in self.walls:
            # Create new wall object with same properties
            new_wall = ai_board.new_wall(wall.coord, wall.horiz, wall.color)
            new_wall.owner_id = getattr(wall, 'owner_id', None)
            # Use putWall to properly add the wall and update cell paths
            ai_board.putWall(new_wall)
        
        # Update distances
        ai_board.update_pawns_distances()
        
        return ai_board


