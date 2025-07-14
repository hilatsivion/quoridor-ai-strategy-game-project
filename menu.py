# -*- coding: utf-8 -*-

import pygame
from pygame.locals import *
from pygame import Color
import config as cfg
from entities.drawable import Drawable


class Button:
    """Simple button class for menu interactions"""
    def __init__(self, x, y, width, height, text, color, text_color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.action = action
        self.hovered = False
        
    def draw(self, screen):
        # Draw button with hover effect
        button_color = self.color
        if self.hovered:
            # Lighten color when hovered
            button_color = tuple(min(255, c + 30) for c in self.color)
            
        pygame.draw.rect(screen, button_color, self.rect)
        pygame.draw.rect(screen, (80, 80, 80), self.rect, 2)
        
        # Draw text
        font = pygame.font.SysFont(None, 24)
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
    
    def handle_event(self, event):
        if event.type == MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.action:
                self.action()
                return True
        return False


class Slider:
    """Custom difficulty slider"""
    def __init__(self, x, y, width, height, min_val, max_val, initial_val):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial_val
        self.dragging = False
        self.knob_radius = 12
        
    def draw(self, screen):
        # Draw slider track
        track_rect = pygame.Rect(self.rect.x, self.rect.y + self.rect.height // 2 - 3, 
                                self.rect.width, 6)
        pygame.draw.rect(screen, (180, 180, 180), track_rect)
        pygame.draw.rect(screen, (100, 100, 100), track_rect, 1)
        
        # Calculate knob position
        progress = (self.val - self.min_val) / (self.max_val - self.min_val)
        knob_x = self.rect.x + int(progress * self.rect.width)
        knob_y = self.rect.y + self.rect.height // 2
        
        # Draw knob
        pygame.draw.circle(screen, (220, 220, 220), (knob_x, knob_y), self.knob_radius)
        pygame.draw.circle(screen, (100, 100, 100), (knob_x, knob_y), self.knob_radius, 2)
        
        # Draw value
        font = pygame.font.SysFont(None, 20)
        value_text = font.render(str(self.val), True, (50, 50, 50))
        value_rect = value_text.get_rect(center=(knob_x, knob_y - 25))
        screen.blit(value_text, value_rect)
    
    def handle_event(self, event):
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            knob_x = self.rect.x + int(((self.val - self.min_val) / (self.max_val - self.min_val)) * self.rect.width)
            knob_y = self.rect.y + self.rect.height // 2
            if ((event.pos[0] - knob_x) ** 2 + (event.pos[1] - knob_y) ** 2) <= self.knob_radius ** 2:
                self.dragging = True
                return True
        elif event.type == MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == MOUSEMOTION and self.dragging:
            # Update slider value based on mouse position
            relative_x = event.pos[0] - self.rect.x
            progress = max(0, min(1, relative_x / self.rect.width))
            self.val = int(self.min_val + progress * (self.max_val - self.min_val))
            return True
        return False


class Menu:
    """Main menu system for difficulty selection and game start"""
    def __init__(self, screen):
        self.screen = screen
        self.selected_difficulty = 2  # Default to Easy
        
        # Calculate center positions
        screen_width, screen_height = screen.get_size()
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        # Title
        self.title_font = pygame.font.SysFont(None, 72)
        self.subtitle_font = pygame.font.SysFont(None, 32)
        self.text_font = pygame.font.SysFont(None, 24)
        
        # Button layout
        button_width = 200
        button_height = 50
        button_spacing = 70
        
        # Difficulty buttons
        start_y = center_y - 100
        self.easy_button = Button(center_x - button_width // 2, start_y, 
                                 button_width, button_height, "Easy (Depth 2)", 
                                 (150, 220, 150), (50, 50, 50), 
                                 lambda: self.set_difficulty(2))
        
        self.medium_button = Button(center_x - button_width // 2, start_y + button_spacing, 
                                   button_width, button_height, "Medium (Depth 3)", 
                                   (220, 200, 120), (50, 50, 50), 
                                   lambda: self.set_difficulty(3))
        
        self.hard_button = Button(center_x - button_width // 2, start_y + button_spacing * 2, 
                                 button_width, button_height, "Hard (Depth 5)", 
                                 (220, 150, 150), (50, 50, 50), 
                                 lambda: self.set_difficulty(5))
        
        # Custom difficulty slider
        self.custom_slider = Slider(center_x - 150, start_y + button_spacing * 3 + 20, 
                                   300, 30, 1, 8, 2)
        
        # Start game button
        self.start_button = Button(center_x - button_width // 2, start_y + button_spacing * 4 + 60, 
                                  button_width, button_height, "Start Game", 
                                  (100, 150, 220), (255, 255, 255), lambda: None)  # Action will be handled in handle_event
        
        self.buttons = [self.easy_button, self.medium_button, self.hard_button, self.start_button]
        
    def set_difficulty(self, level):
        """Set the selected difficulty level"""
        self.selected_difficulty = level
        self.custom_slider.val = level
        
    def draw(self):
        """Draw the complete menu"""
        # Light background
        self.screen.fill((245, 248, 250))
        
        # Title
        title_text = self.title_font.render("QUORIDOR", True, (60, 80, 120))
        title_rect = title_text.get_rect(center=(self.screen.get_width() // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        # Subtitle
        subtitle_text = self.subtitle_font.render("Strategic Board Game", True, (100, 120, 140))
        subtitle_rect = subtitle_text.get_rect(center=(self.screen.get_width() // 2, 140))
        self.screen.blit(subtitle_text, subtitle_rect)
        
        # Instructions - positioned relative to buttons for better layout
        center_x = self.screen.get_width() // 2
        
        # "Choose AI Difficulty:" above first button
        choose_text = self.text_font.render("Choose AI Difficulty:", True, (80, 100, 120))
        choose_rect = choose_text.get_rect(center=(center_x, self.easy_button.rect.y - 30))
        self.screen.blit(choose_text, choose_rect)
        
        # "Custom Difficulty:" above slider with proper spacing
        custom_text = self.text_font.render("Custom Difficulty:", True, (80, 100, 120))
        custom_rect = custom_text.get_rect(center=(center_x, self.custom_slider.rect.y - 50))
        self.screen.blit(custom_text, custom_rect)
        
        # Draw buttons
        for button in self.buttons:
            # Highlight selected difficulty
            if button == self.easy_button and self.selected_difficulty == 2:
                button.color = (120, 200, 120)
            elif button == self.medium_button and self.selected_difficulty == 3:
                button.color = (200, 180, 100)
            elif button == self.hard_button and self.selected_difficulty == 5:
                button.color = (200, 120, 120)
            else:
                # Reset to default colors
                if button == self.easy_button:
                    button.color = (150, 220, 150)
                elif button == self.medium_button:
                    button.color = (220, 200, 120)
                elif button == self.hard_button:
                    button.color = (220, 150, 150)
            
            button.draw(self.screen)
        
        # Draw custom slider
        self.custom_slider.draw(self.screen)
        
        # Update selected difficulty from slider if it changed
        if self.custom_slider.val not in [2, 3, 5]:
            self.selected_difficulty = self.custom_slider.val
    
    def handle_event(self, event):
        """Handle menu events, return True if start game requested"""
        # Handle slider events
        if self.custom_slider.handle_event(event):
            self.selected_difficulty = self.custom_slider.val
        
        # Handle button events
        for button in self.buttons:
            if button.handle_event(event):
                if button == self.start_button:
                    return True  # Start game
        
        return False
    
    def get_selected_difficulty(self):
        """Return the currently selected difficulty level"""
        return self.selected_difficulty 