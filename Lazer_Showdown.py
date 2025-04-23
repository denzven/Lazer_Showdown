import pygame
import random
import os
import json
import uuid
from os import environ
from sys import platform as _sys_platform


# Lazer Showdown - A Grid-Based Laser Reflection Game
# --------------------------------------------------
# This game consists of a grid where players can place and move laser pieces, mirror pieces, and point pieces.
# The laser piece fires a laser in a given direction, and the goal is to reflect the laser using mirrors to hit point pieces.
# The player scores points when the laser successfully hits a point piece. The game allows drag-and-drop movement of pieces
# and provides a simple restart mechanism.

# Constants
GRID_SIZE = 8  # The grid consists of 8x8 cells
GRID_WIDTH = 4
CELL_SIZE = 100  # Each grid cell has a fixed size
TOP_MARGIN = 100  # Margin at the top
PALETTE_BOX_SIZE = CELL_SIZE  # Size of each palette box
BUTTON_WIDTH, BUTTON_HEIGHT = 128, 64  # Restart button dimensions

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (200, 50, 50)  # Color for the laser piece
LIGHT_BLUE = (173, 216, 230)
PINK = (255, 182, 193)  # Color for point pieces
GRAY = (100, 100, 100)  # Color for mirror pieces

def platform():
    if 'ANDROID_ARGUMENT' in environ:
        return "android"
    elif _sys_platform in ('linux', 'linux2','linux3'):
        return "linux"
    elif _sys_platform in ('win32', 'cygwin'):
        return 'win'

if platform()=="android":
    PATH="/data/data/org.test.pgame/files/app/"
elif platform()=="linux":
    PATH="./"
else:
    PATH = os.path.abspath(".") + "/"

score = 0  # Player's score
game_state = {}  # Dictionary to save game state

class Button:
    def __init__(self, image_path, position, scale=1.0):
        self.image = pygame.image.load(image_path).convert_alpha()
        original_width = self.image.get_width()
        original_height = self.image.get_height()
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        self.image = pygame.transform.scale(self.image, (new_width, new_height))
        self.rect = self.image.get_rect(center=position)
        self.pressed = False

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def is_pressed(self):
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]

        touch_events = [event for event in pygame.event.get(pygame.FINGERDOWN)]
        touch_pos = None
        if touch_events:
            first_touch = touch_events[0]
            touch_pos = (int(first_touch.x * screen.get_width()), int(first_touch.y * screen.get_height()))

        # Detect mouse or touch press
        press_detected = (mouse_pressed and self.rect.collidepoint(mouse_pos)) or (touch_pos and self.rect.collidepoint(touch_pos))

        if press_detected and not self.pressed:
            self.pressed = True
            return True

        # Reset when neither mouse nor touch is pressed
        if not mouse_pressed and not touch_events:
            self.pressed = False

        return False

class GameState:
    def __init__(self):
        self.score = 0
        self.laser_piece = None
        self.point_pieces = []
        self.mirror_pieces = []
        self.dice_list = []

    def reset(self, palette_origin):
        self.score = 0
        self.laser_piece = lazerPiece(palette_origin, 150)
        self.point_pieces = [
            pointPiece(palette_origin, 250, 20),
            pointPiece(palette_origin, 350, 30),
            pointPiece(palette_origin, 450, 50)
        ]
        self.mirror_pieces = [
            mirrorPiece(palette_origin, 550, "/"),
            mirrorPiece(palette_origin, 650, "\\")
        ]
        self.dice_list = [
            Dice(200 - CELL_SIZE // 2, 850),
            Dice(200 - CELL_SIZE // 2, 700)
        ]
        
    def get_all_pieces(self):
        return [self.laser_piece] + self.point_pieces + self.mirror_pieces
    
    def save(self):
        # snapshot everything, including each piece’s palette_position
        return {
            'score': self.score,
            'laser': {
                'pos': self.laser_piece.grid_position,
                'dir': self.laser_piece.direction,
                'palette': self.laser_piece.palette_position
            },
            'points': [
                {
                  'pos': p.grid_position,
                  'value': p.value,
                  'palette': p.palette_position
                }
                for p in self.point_pieces
            ],
            'mirrors': [
                {
                  'pos': m.grid_position,
                  'type': m.mirror_type,
                  'palette': m.palette_position
                }
                for m in self.mirror_pieces
            ],
            'dice': [
                {'value': d.value}
                for d in self.dice_list
            ]
        }

    def load(self, state_dict):
        # restore score
        self.score = state_dict.get('score', 0)

        # restore laser piece
        laser_info = state_dict.get('laser', {})
        if laser_info and self.laser_piece:
            # palette position
            if 'palette' in laser_info and laser_info['palette'] is not None:
                self.laser_piece.palette_position = tuple(laser_info['palette'])
            # grid position (may be None)
            pos = laser_info.get('pos', None)
            self.laser_piece.grid_position = tuple(pos) if pos is not None else None
            self.laser_piece.direction = laser_info.get('dir', self.laser_piece.direction)
            self.laser_piece.update_position_from_grid()

        # rebuild point pieces list
        self.point_pieces = []
        for info in state_dict.get('points', []):
            p = pointPiece(0, 0, info['value'])
            # restore palette_position
            if info.get('palette') is not None:
                p.palette_position = tuple(info['palette'])
            # restore grid_position if not None
            pos = info.get('pos', None)
            p.grid_position = tuple(pos) if pos is not None else None
            p.update_position_from_grid()
            self.point_pieces.append(p)

        # rebuild mirror pieces list
        self.mirror_pieces = []
        for info in state_dict.get('mirrors', []):
            m = mirrorPiece(0, 0, info['type'])
            # restore palette_position
            if info.get('palette') is not None:
                m.palette_position = tuple(info['palette'])
            # restore grid_position if not None
            pos = info.get('pos', None)
            m.grid_position = tuple(pos) if pos is not None else None
            m.update_position_from_grid()
            self.mirror_pieces.append(m)

        # restore dice values
        for d, info in zip(self.dice_list, state_dict.get('dice', [])):
            d.value = info.get('value', d.value)
            d.image = d.images[d.value]

 
class GameManager:
    def __init__(self, screen):
        self.screen = screen
        self.state = GameState()
        self.font = pygame.font.Font(PATH + 'assets/fonts/Font.ttf', 32)
        self.undo_stack = []
        self.redo_stack = []
        # you can still have a default folder if you like
        self.save_folder = PATH + "savedgames/"


    def get_dimensions(self):
        return self.screen.get_size()

    def get_grid_origin(self):
        scr_width, scr_height = self.get_dimensions()
        x_origin = (scr_width // 2) - ((GRID_SIZE // 2) * CELL_SIZE)
        y_origin = (scr_height // 2) - ((GRID_SIZE // 2) * CELL_SIZE)
        return x_origin, y_origin

    def reset_game(self):
        scr_width, scr_height = self.get_dimensions()
        palette_origin = ((scr_width // 2) + ((GRID_SIZE // 2) * CELL_SIZE)) + (CELL_SIZE)
        pygame.draw.rect(self.screen, BLACK, (palette_origin, 0, CELL_SIZE, scr_height))
        self.state.reset(palette_origin)
        self.redraw_scene()

    def draw_grid(self):
        x_origin, y_origin = self.get_grid_origin()
        for i in range(GRID_SIZE + 1):
            pygame.draw.line(
                self.screen, WHITE,
                (x_origin, y_origin + i * CELL_SIZE),
                (x_origin + GRID_SIZE * CELL_SIZE, y_origin + i * CELL_SIZE),
                GRID_WIDTH
            )
            pygame.draw.line(
                self.screen, WHITE,
                (x_origin + i * CELL_SIZE, y_origin),
                (x_origin + i * CELL_SIZE, y_origin + GRID_SIZE * CELL_SIZE),
                GRID_WIDTH
            )

    def draw_palette(self):
        scr_width, scr_height = self.get_dimensions()
        x_origin = ((scr_width // 2) + ((GRID_SIZE // 2) * CELL_SIZE)) + (CELL_SIZE)
        pygame.draw.rect(self.screen, BLACK, (x_origin, 0, CELL_SIZE, scr_height), GRID_WIDTH)
        piece_positions = [(x_origin, 150), (x_origin, 250), (x_origin, 350), 
                           (x_origin, 450), (x_origin, 550), (x_origin, 650)]
        for pos in piece_positions:
            pygame.draw.rect(self.screen, WHITE, (pos[0], pos[1], PALETTE_BOX_SIZE, PALETTE_BOX_SIZE), GRID_WIDTH)

    def draw_scoreboard(self):
        score_text = self.font.render(f"Score: {self.state.score}", True, WHITE)
        self.screen.blit(score_text, (50, 50))

    def redraw_scene(self):
        self.screen.fill(BLACK)
        self.draw_palette()
        self.draw_grid()

        self.state.laser_piece.draw(self.screen)

        for piece in self.state.point_pieces:
            piece.draw(self.screen)
        for piece in self.state.mirror_pieces:
            piece.draw(self.screen)
        for dice in self.state.dice_list:
            dice.draw(self.screen)

        restartBtn.draw(self.screen)
        rollBtn.draw(self.screen)
        fireBtn.draw(self.screen)
        rotateBtn.draw(self.screen)
        self.draw_scoreboard()
        pygame.display.flip()
        
    @staticmethod
    def get_grid_origin_static():
        screen = pygame.display.get_surface()
        scr_width, scr_height = screen.get_size()
        x_origin = (scr_width // 2) - ((GRID_SIZE // 2) * CELL_SIZE)
        y_origin = (scr_height // 2) - ((GRID_SIZE // 2) * CELL_SIZE)
        return x_origin, y_origin
    
    def save_state(self):
        self.undo_stack.append(self.state.save())
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.state.save())
            previous = self.undo_stack.pop()
            self.state.load(previous)
            self.redraw_scene()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.state.save())
            next_state = self.redo_stack.pop()
            self.state.load(next_state)
            self.redraw_scene()
            

    def save_to_file(self, filename: str = None):
        """
        Write current GameState snapshot to a JSON file.
        If no filename is provided, generate one of the form 'lzrshwdn_<8-char>.json'
        inside the 'savedgames' folder.
        """
        # generate filename if not provided
        if filename is None:
            code = uuid.uuid4().hex[:8]
            filename = os.path.join(self.save_folder, f"lzrshwdn_{code}.json")

        # ensure folder exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # write out the snapshot
        with open(filename, 'w') as f:
            json.dump(self.state.save(), f, indent=2)

        print(f"Game saved to {filename}")
        
    def choose_save_file(self):
        """
        In‐game file picker using Button sprites for Up/Down/Select.
        Returns full path or None.
        """
        # ensure save folder exists
        folder = os.path.join(PATH, "savedgames")
        os.makedirs(folder, exist_ok=True)
    
        # gather .json files
        files = [f for f in os.listdir(folder) if f.endswith(".json")]
        if not files:
            return None
    
        # create sprite-style buttons
        # positions: right side, vertically stacked
        w, h = self.screen.get_size()
        bx = w - CELL_SIZE  # one cell from right
        upBtn     = Button(PATH + "assets/images/btn/UpBtnImg.png",    (bx, 150), scale=1.0)
        downBtn   = Button(PATH + "assets/images/btn/DownBtnImg.png",  (bx, 250), scale=1.0)
        selectBtn = Button(PATH + "assets/images/btn/SelectBtnImg.png",(bx, 350), scale=1.0)
    
        idx = 0
        clock = pygame.time.Clock()
        font = pygame.font.Font(PATH + 'assets/fonts/Font.ttf', 28)
    
        while True:
            # draw background panel
            self.screen.fill((30,30,30))
            panel = pygame.Rect(20, 20, w - CELL_SIZE - 60, h - 40)
            pygame.draw.rect(self.screen, (50,50,50), panel, border_radius=8)
    
            # title
            title = font.render("Select save file", True, WHITE)
            self.screen.blit(title, (40, 40))
    
            # file list
            for i, fname in enumerate(files):
                y = 80 + i * 30
                col = LIGHT_BLUE if i == idx else WHITE
                txt = font.render(fname, True, col)
                self.screen.blit(txt, (40, y))
                if i == idx:
                    highlight = pygame.Rect(35, y-2, panel.width-30, 28)
                    pygame.draw.rect(self.screen, (100,100,150), highlight, width=2, border_radius=4)
    
            # draw buttons
            upBtn.draw(self.screen)
            downBtn.draw(self.screen)
            selectBtn.draw(self.screen)
    
            pygame.display.flip()
    
            # handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
    
            # button actions
            if upBtn.is_pressed():
                idx = (idx - 1) % len(files)
            if downBtn.is_pressed():
                idx = (idx + 1) % len(files)
            if selectBtn.is_pressed():
                return os.path.join(folder, files[idx])
    
            # keyboard fallback
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                idx = (idx - 1) % len(files)
                pygame.time.delay(150)
            elif keys[pygame.K_DOWN]:
                idx = (idx + 1) % len(files)
                pygame.time.delay(150)
            elif keys[pygame.K_RETURN]:
                return os.path.join(folder, files[idx])
            elif keys[pygame.K_ESCAPE]:
                return None
    
            clock.tick(30)


    def load_from_file(self, filename: str = None):
        if filename is None:
            filename = self.choose_save_file()
            if not filename:
                return
        with open(filename, 'r') as f:
            snapshot = json.load(f)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.state.load(snapshot)
        self.redraw_scene()
        print(f"Game loaded from {filename}")



       
class Piece:
    """Base class for all game pieces that can be placed on the grid."""
    def __init__(self, x, y, color,image_path=None):
        self.grid_position = None
        self.palette_position = (x, y)
        self.update_position_from_grid()
        self.color = color
        self.dragging = False
        self.image = None
        
        if image_path:
            self.image = pygame.image.load(image_path)  # Load the sprite
            self.image = pygame.transform.scale(self.image, (CELL_SIZE, CELL_SIZE))  # Resize it
        self.rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)  # For positioning        
    
    def draw(self, surface):
        """Draws the piece on the given surface."""
        if self.image:
            screen.blit(self.image, self.rect.topleft)
        else:
            pygame.draw.rect(surface, self.color, self.rect)
    
    def update_position_from_grid(self):
        """Updates the piece position based on the grid or palette placement."""
        if self.grid_position:
            x_origin, y_origin = GameManager.get_grid_origin_static()
            self.rect = pygame.Rect(x_origin + self.grid_position[0] * CELL_SIZE, y_origin + self.grid_position[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        else:
            self.rect = pygame.Rect(self.palette_position[0], self.palette_position[1], CELL_SIZE, CELL_SIZE)
    
    def snap_to_grid(self, occupied_spaces):
        """Snaps the piece to the nearest valid grid position."""
        x_origin, y_origin = GameManager.get_grid_origin_static()
        grid_x = (self.rect.x - x_origin + CELL_SIZE // 2) // CELL_SIZE
        grid_y = (self.rect.y - y_origin + CELL_SIZE // 2) // CELL_SIZE
        
        if 0 <= grid_x < GRID_SIZE and 0 <= grid_y < GRID_SIZE:
            if (grid_x, grid_y) not in occupied_spaces:
                self.grid_position = (grid_x, grid_y)
            else:
                self.grid_position = None
        else:
            self.grid_position = None
        self.update_position_from_grid()

class lazerPiece(Piece):
    def __init__(self, x, y):
        super().__init__(x, y, RED, image_path="assets/images/lzrImg.png")
        self.rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
        self.grid_position = None
        self.direction = "up"
        self.og_img = self.image

        self.lzrBeamImg = pygame.image.load(PATH + 'assets/images/lzrBeamImg.png')
        self.lzrBeamImg = pygame.transform.scale(self.lzrBeamImg, (CELL_SIZE, CELL_SIZE))

        self.lzrBeamstrtImg = pygame.image.load(PATH + 'assets/images/lzrBeamstrtImg.png')
        self.lzrBeamstrtImg = pygame.transform.scale(self.lzrBeamstrtImg, (CELL_SIZE, CELL_SIZE))

    def draw(self, surface):
        self.rotate_img_direction()
        surface.blit(self.image, self.rect.topleft)

    def rotate_laser(self):
        directions = ["up", "right", "down", "left"]
        current_index = directions.index(self.direction)
        self.direction = directions[(current_index + 1) % 4]

    def rotate_img_direction(self):
        angles = {"up": 0, "down": 180, "left": 90, "right": -90}
        self.image = pygame.transform.rotate(self.og_img, angles[self.direction])
        self.rect = self.image.get_rect(center=self.rect.center)

    def fire_laser(self, game_state):
        if not self.grid_position:
            return
        path = self.calculate_laser_path(game_state)
        self.apply_laser_effects(game_state, path)
        self.draw_laser_path(path)

    def calculate_laser_path(self, game_state):
        x, y = self.grid_position
        direction = self.direction
        x_origin, y_origin = GameManager.get_grid_origin_static()

        path = []
        dx, dy = self._dir_to_delta(direction)
        x += dx
        y += dy

        while 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
            path.append((x_origin + x * CELL_SIZE + CELL_SIZE // 2,
                         y_origin + y * CELL_SIZE + CELL_SIZE // 2))

            # Check mirrors for reflection
            for mirror in game_state.mirror_pieces:
                if mirror.grid_position == (x, y):
                    direction = self.reflect_laser(direction, mirror.mirror_type)
                    dx, dy = self._dir_to_delta(direction)
                    break
            else:
                # Check point pieces for scoring
                for point in game_state.point_pieces:
                    if point.grid_position == (x, y):
                        game_state.score += point.value
                        game_state.point_pieces.remove(point)
                        return path

            if (x, y) == self.grid_position:
                break

            x += dx
            y += dy

        return path

    def apply_laser_effects(self, game_state, path):
        # Can be extended to affect other state elements if needed
        pass

    def draw_laser_path(self, path):
        pygame.display.flip()
        pygame.time.delay(100)

        for i in range(len(path) - 1):
            start = path[i]
            end = path[i + 1]

            direction_vec = pygame.math.Vector2(end[0] - start[0], end[1] - start[1])
            angle = direction_vec.angle_to(pygame.math.Vector2(1, 0))

            rotated_sprite = pygame.transform.rotate(self.lzrBeamImg, angle)
            sprite_rect = rotated_sprite.get_rect(center=start)
            screen.blit(rotated_sprite, sprite_rect.topleft)

            if i == 0:  # draw the start beam
                start_sprite = pygame.transform.rotate(self.lzrBeamstrtImg, angle)
                start_rect = start_sprite.get_rect(center=start)
                screen.blit(start_sprite, start_rect.topleft)

            pygame.display.flip()
            pygame.time.delay(100)

    def reflect_laser(self, direction, mirror_type):
        if mirror_type == "/":
            return {"up": "left", "down": "right", "left": "up", "right": "down"}[direction]
        else:  # mirror_type == "\\"
            return {"up": "right", "down": "left", "left": "down", "right": "up"}[direction]

    def _dir_to_delta(self, direction):
        return {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
        }[direction]

class pointPiece(Piece):
    """Represents a point piece that adds score when hit by the laser."""
    def __init__(self, x, y, value):
        pntImg = self.get_image_path(value)
        super().__init__(x, y, PINK,image_path=pntImg)
        self.value = value
    
    def draw(self, surface):
        """Draws the point piece with its score value."""
        super().draw(surface)
           
    def get_image_path(self, value):
         """Returns the appropriate image path based on the point piece value."""
         if value == 20:
             return "assets/images/pntImg20.png"
         elif value == 30:
             return "assets/images/pntImg30.png"
         elif value == 50:
             return "assets/images/pntImg50.png"
         return "assets/images/pntDefImg.png"  # Default image if no match
     
class mirrorPiece(Piece):
    """Represents a mirror piece that reflects the laser beam."""
    def __init__(self, x, y, mirror_type="/"):
        super().__init__(x, y, GRAY,image_path="assets/images/mirrImg.png")
        self.mirror_type = mirror_type  # Either "/" or "\"
        self.rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
        self.grid_position = None
        self.og_img = self.image

    def draw(self, surface):
        """Draws the mirror with a diagonal reflection indicator."""
        #pygame.draw.rect(surface, GRAY, self.rect)
        if self.mirror_type == "/":
            screen.blit(self.image, self.rect.topleft)
        else:  # "\" type
            self.image = pygame.transform.flip(self.og_img, True, False)
            screen.blit(self.image, self.rect.topleft)



def start_screen():
    """Displays the start screen."""
    screen.fill(BLACK)  # Clear the screen
    title_font = pygame.font.Font(PATH + 'assets/fonts/Font.ttf', 72)
    subtitle_font = pygame.font.Font(PATH + 'assets/fonts/Font.ttf', 32)


    # Logo
    logo = pygame.image.load("assets/images/logo.png")
    logo = pygame.transform.scale(logo, (128*6, 32*6))  # Resize if needed
    screen.blit(logo, (screen.get_width() // 2 - logo.get_width() // 2, 50))

    # Title and Subtitle
    title_text = title_font.render("Lazer Showdown", True, WHITE)
    screen.blit(title_text, (screen.get_width() // 2 - title_text.get_width() // 2, 320))

    # Instructions
    instructions = [
        "Click to Start \n",
        "Controls:",
        "Press   R   to rotate the lazer",
        "Press   SPACE   to fire the lazer",
        "Press   D   to roll the dice",
        "Pick pieces and mirrors with your mouse",
        "Right-click to place pieces"
    ]

    for i, line in enumerate(instructions):
        line_text = subtitle_font.render(line, True, LIGHT_BLUE)
        screen.blit(line_text, (screen.get_width() // 2 - line_text.get_width() // 2, 400 + i * 40))
        

    # Start Button
    startBtn.draw(screen)
    pygame.display.flip()  # Update the screen to show the start screen

    # Event loop for the start screen
    waiting_for_input = True
    while waiting_for_input:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()  # Exit the game entirely
            elif startBtn.is_pressed():
                    waiting_for_input = False  # Exit the start screen loop to start the game


#Main Game Loop
def main_game_loop(screen):
    manager = GameManager(screen)
    manager.reset_game()
    state = manager.state

    draggable_piece = None
    running = True

    while running:
        manager.redraw_scene()

        occupied_spaces = {
            piece.grid_position
            for piece in state.get_all_pieces()
            if piece.grid_position
        }


        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                manager.screen = screen
                manager.redraw_scene()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Save before any potential drag‐and‐drop placement
                if restartBtn.is_pressed():
                    manager.save_state()
                    manager.reset_game()
                else:
                    for piece in reversed(state.get_all_pieces()):
                        if piece.rect.collidepoint(event.pos):
                            manager.save_state()
                            draggable_piece = piece
                            draggable_piece.dragging = True
                            mouse_offset_x = event.pos[0] - piece.rect.x
                            mouse_offset_y = event.pos[1] - piece.rect.y
                            break

            elif event.type == pygame.MOUSEBUTTONUP:
                if draggable_piece:
                    # state will change when we snap
                    manager.save_state()
                    draggable_piece.snap_to_grid(occupied_spaces)
                    draggable_piece.dragging = False

                    # Clone a new mirror in palette if placed on board
                    if isinstance(draggable_piece, mirrorPiece) and draggable_piece.grid_position:
                        mirror_type = draggable_piece.mirror_type
                        palette_origin = ((screen.get_width() // 2) + ((GRID_SIZE // 2) * CELL_SIZE)) + (CELL_SIZE)
                        y_offset = 550 if mirror_type == '/' else 650
                        state.mirror_pieces.append(mirrorPiece(palette_origin, y_offset, mirror_type))

                    draggable_piece = None

            elif event.type == pygame.MOUSEMOTION:
                if draggable_piece and draggable_piece.dragging:
                    draggable_piece.rect.topleft = (
                        event.pos[0] - mouse_offset_x,
                        event.pos[1] - mouse_offset_y
                    )

            elif event.type == pygame.KEYDOWN:
                # UNDO / REDO
                if event.key == pygame.K_z:        # press Z for undo
                    manager.undo()
                elif event.key == pygame.K_y:      # press Y for redo
                    manager.redo()

                # LASER FIRE
                elif event.key == pygame.K_SPACE:
                    manager.save_state()
                    state.laser_piece.fire_laser(state)

                # LASER ROTATE
                elif event.key == pygame.K_r:
                    manager.save_state()
                    state.laser_piece.rotate_laser()

                # DICE ROLL
                elif event.key == pygame.K_d:
                    manager.save_state()
                    for dice in state.dice_list:
                        dice.roll()
                        
                # SAVE
                elif event.key == pygame.K_s:
                    manager.save_to_file()      # will create lzrshwdn_<code>.json
                # LOAD (you could hardcode or ask user for filename)
                elif event.key == pygame.K_l:
                    manager.load_from_file()

        # Button actions (touch or mouse)
        if fireBtn.is_pressed():
            manager.save_state()
            state.laser_piece.fire_laser(state)
        if rotateBtn.is_pressed():
            manager.save_state()
            state.laser_piece.rotate_laser()
        if rollBtn.is_pressed():
            manager.save_state()
            for dice in state.dice_list:
                dice.roll()
        if restartBtn.is_pressed():
            manager.save_state()
            manager.reset_game()

                    
# Dice Class
class Dice(pygame.sprite.Sprite):
    """ two dice on the side of the board for random number gen"""
    def __init__(self, x, y):
        super().__init__()
        self.images = [pygame.image.load(PATH + f'assets/images/dice/{i}.png') for i in range(1, 7)]
        self.images = [pygame.transform.scale(self.images[i], (CELL_SIZE, CELL_SIZE)) for i in range(0, 6)]
        self.value = random.randint(0, 5)
        self.image = self.images[self.value]
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def roll(self):
        """ roll the dice and get a random number"""
        # Randomly choose an image between 1 and 6
        self.value = random.randint(0, 5)
        self.image = self.images[self.value]
                
    def draw(self, surface):
        """Draws the piece on the given surface."""
        if self.image:
            screen.blit(self.image, self.rect.topleft)
        else:
            pygame.draw.rect(surface, RED, self.rect)

pygame.init()
screen = pygame.display.set_mode((1500, 1000), pygame.RESIZABLE)
icon = pygame.image.load(PATH + 'assets/images/icon.ico')
pygame.display.set_caption("Lazer Showdown")
pygame.display.set_icon(icon)
font = pygame.font.Font(PATH + 'assets/fonts/Font.ttf', 32)

# Create buttons using the common button sprite
startBtn = Button(PATH + 'assets/images/btn/StartBtnImg.png', (screen.get_width() // 2, 750), 1.5)

fireBtn = Button(PATH + 'assets/images/btn/FireBtnImg.png', (200, 200), 1.5)
rotateBtn = Button(PATH + 'assets/images/btn/RotateBtnImg.png', (200, 300), 1.5)
rollBtn = Button(PATH + 'assets/images/btn/RollBtnImg.png', (200, 400), 1.5)
restartBtn = Button(PATH + 'assets/images/btn/RestartBtnImg.png', (200, 550), 1.5)

start_screen()
main_game_loop(screen)

pygame.quit()  # Properly exit pygame when the loop ends

# Made with Love by Denzven 💜 & guided by ChatGPT 🤖