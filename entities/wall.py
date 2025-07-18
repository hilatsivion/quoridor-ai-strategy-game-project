# -*- coding: utf-8 -*-

import pygame

from .drawable import Drawable
from .coord import Coord
from config import DIR, DIRS_DELTA


class Wall(Drawable):
    """ Class for painting a Wall
    """
    def __init__(self,
                 screen: pygame.Surface,
                 board,  # parent object
                 color: pygame.Color,
                 coord: Coord = None,  # Wall coordinates
                 horiz: bool = None,  # whether this wall lays horizontal o vertically
                 owner_id: int = None,  # ID of player who placed this wall
                 ):
        super().__init__(screen, color)
        self.board = board
        self.horiz: bool = horiz
        self.coord = coord
        self.owner_id = owner_id  # Track who placed this wall
        self._hash = hash((self.horiz, self.coord))

    def __eq__(self, other) -> bool:
        assert isinstance(other, Wall)
        return self.horiz == other.horiz and self.coord == other.coord

    def __repr__(self):
        return "<Wall: %i, %i, %i>" % (self.coord.row, self.coord.col, int(self.horiz))

    def __hash__(self):
        return self._hash

    @property
    def coords(self):
        """ Returns a list with 2 t-uples containing coord of
        wall cells. Cells are top / left to the wall.
        """
        if self.horiz is None or self.coord is None:
            return None

        if self.horiz:
            return [self.coord, self.coord + DIRS_DELTA[DIR.W]]

        return [self.coord, self.coord + DIRS_DELTA[DIR.N]]

    @property
    def rect(self):
        c = self.coords
        if not c:
            return None

        cell = self.board.get_cell(self.coord)
        if self.horiz:
            x = cell.x
            y = cell.y + cell.height
            w = self.board.cell_pad + 2 * cell.width
            h = self.board.cell_pad
        else:
            x = cell.x + cell.width
            y = cell.y
            w = self.board.cell_pad
            h = self.board.cell_pad + 2 * cell.width

        return pygame.Rect(x, y, w, h)

    def draw(self):
        if self.color is None:
            return

        pygame.draw.rect(self.screen, self.color, self.rect, 0)

    def draw_preview(self):
        """Draw wall with preview styling (lower opacity and different color)"""
        if self.rect is None:
            return
            
        import config as cfg
        
        # Create a surface with per-pixel alpha for transparency
        preview_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        
        # Set preview color with opacity
        preview_color = (*cfg.WALL_PREVIEW_COLOR[:3], cfg.WALL_PREVIEW_OPACITY)
        
        # Draw the wall on the surface with alpha
        pygame.draw.rect(preview_surface, preview_color, 
                        pygame.Rect(0, 0, self.rect.width, self.rect.height))
        
        # Blit the surface to the screen at the wall position
        self.screen.blit(preview_surface, (self.rect.x, self.rect.y))

    def collides(self, wall):
        """ Returns if the given wall collides with this one
        """
        if self.horiz == wall.horiz:
            wc = wall.coords
            for c in self.coords:
                if c in wc:
                    return True

            return False

        # Only can collide if they form a cross
        if self.coord == wall.coord:
            return True

        return False

    @property
    def state(self) -> str:
        """ Returns a string containing IJH
        """
        return "%i%i%i" % (self.coord.row, self.coord.col, self.horiz)
