import pygame

# Lazer Showdown - A Grid-Based Laser Reflection Game
# --------------------------------------------------
# This game consists of a grid where players can place and move laser pieces, mirror pieces, and point pieces.
# The laser piece fires a laser in a given direction, and the goal is to reflect the laser using mirrors to hit point pieces.
# The player scores points when the laser successfully hits a point piece. The game allows drag-and-drop movement of pieces
# and provides a simple restart mechanism.

# Constants
GRID_SIZE = 8  # The grid consists of 8x8 cells
CELL_SIZE = 100  # Each grid cell has a fixed size
TOP_MARGIN = 100  # Margin at the top
PALETTE_BOX_SIZE = CELL_SIZE  # Size of each palette box
BUTTON_WIDTH, BUTTON_HEIGHT = CELL_SIZE, 40  # Restart button dimensions

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (200, 50, 50)  # Color for the laser piece
LIGHT_BLUE = (173, 216, 230)
PINK = (255, 182, 193)  # Color for point pieces
GRAY = (100, 100, 100)  # Color for mirror pieces

score = 0  # Player's score
game_state = {}  # Dictionary to save game state

def reset_game():  
    """Resets the game by reinitializing pieces and resetting the score."""
    global lzrpiece, pntpiece, mirrpiece, score
    scrWidth, scrHeight = get_dimensions()
    x_origin = ((scrWidth // 2) + ((GRID_SIZE // 2) * CELL_SIZE)) + (CELL_SIZE)
    pygame.draw.rect(screen, BLACK, (x_origin, 0, CELL_SIZE, scrHeight))
    lzrpiece = lazerPiece(x_origin, 150)
    pntpiece = [pointPiece(x_origin, 250, 20), pointPiece(x_origin, 350, 30), pointPiece(x_origin, 450, 50)]   
    mirrpiece = [mirrorPiece(x_origin, 550, "/"), mirrorPiece(x_origin, 650, "\\")]

    score = 0
    save_game_state()
    
def get_dimensions():
    """Returns the current screen dimensions."""
    width, height = screen.get_size()
    return width, height

def get_grid_origin():
    """Calculates and returns the origin point of the grid."""
    scrWidth, scrHeight = get_dimensions()
    x_origin = (scrWidth // 2) - ((GRID_SIZE // 2) * CELL_SIZE)
    y_origin = (scrHeight // 2) - ((GRID_SIZE // 2) * CELL_SIZE)
    return x_origin, y_origin

def draw_grid():
    """Draws the game grid on the screen."""
    x_origin, y_origin = get_grid_origin()
    for i in range(GRID_SIZE + 1):
        pygame.draw.line(screen, WHITE, (x_origin, y_origin + i * CELL_SIZE), (x_origin + GRID_SIZE * CELL_SIZE, y_origin + i * CELL_SIZE))
        pygame.draw.line(screen, WHITE, (x_origin + i * CELL_SIZE, y_origin), (x_origin + i * CELL_SIZE, y_origin + GRID_SIZE * CELL_SIZE))

def draw_palette():
    """Draws the palette area where draggable pieces are placed."""
    scrWidth, scrHeight = get_dimensions()
    x_origin = ((scrWidth // 2) + ((GRID_SIZE // 2) * CELL_SIZE)) + (CELL_SIZE)
    pygame.draw.rect(screen, BLACK, (x_origin, 0, CELL_SIZE, scrHeight))
    piece_positions = [(x_origin, 150), (x_origin, 250), (x_origin, 350), (x_origin, 450),(x_origin, 550),(x_origin, 650)]
    for pos in piece_positions:
        pygame.draw.rect(screen, WHITE, (pos[0], pos[1], PALETTE_BOX_SIZE, PALETTE_BOX_SIZE), 2)

def save_game_state():
    """Saves the current state of all pieces."""
    game_state['lzrpiece'] = lzrpiece.grid_position
    game_state['pntpieces'] = [piece.grid_position for piece in pntpiece]
    game_state['mirrpieces'] = [piece.grid_position for piece in mirrpiece]

def load_game_state():
    """Loads saved game state and updates piece positions."""
    if 'lzrpiece' in game_state:
        lzrpiece.grid_position = game_state['lzrpiece']
        lzrpiece.update_position_from_grid()
    if 'pntpieces' in game_state:
        for piece, position in zip(pntpiece, game_state['pntpieces']):
            piece.grid_position = position
            piece.update_position_from_grid()
    if 'mirrpieces' in game_state:
        for piece, position in zip(mirrpiece, game_state['mirrpieces']):
            piece.grid_position = position
            piece.update_position_from_grid()

def redraw_scene():
    """Redraws all game elements on the screen."""
    screen.fill(BLACK)
    draw_palette()
    draw_grid()
    lzrpiece.draw(screen)
    for piece in pntpiece:
        piece.draw(screen)
    for piece in mirrpiece:
        piece.draw(screen)
    draw_restart_button()
    draw_scoreboard()
    pygame.display.flip()

def draw_restart_button():
    """Draws the restart button on the screen."""
    scrWidth, scrHeight = get_dimensions()
    global button_x, button_y
    button_x = (((scrWidth // 2) + ((GRID_SIZE // 2) * CELL_SIZE)) + (CELL_SIZE // 2))
    button_y = ((scrHeight - BUTTON_HEIGHT) // 2) + ((GRID_SIZE // 2) * CELL_SIZE) - BUTTON_HEIGHT
    pygame.draw.rect(screen, GRAY, (button_x, button_y, BUTTON_WIDTH, BUTTON_HEIGHT))
    text = font.render("Restart", True, WHITE)
    screen.blit(text, (button_x + 7, button_y + 10))

def draw_scoreboard():
    """Displays the current score on the screen."""
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (50, 50))

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
            x_origin, y_origin = get_grid_origin()
            self.rect = pygame.Rect(x_origin + self.grid_position[0] * CELL_SIZE, y_origin + self.grid_position[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        else:
            self.rect = pygame.Rect(self.palette_position[0], self.palette_position[1], CELL_SIZE, CELL_SIZE)
    
    def snap_to_grid(self, occupied_spaces):
        """Snaps the piece to the nearest valid grid position."""
        x_origin, y_origin = get_grid_origin()
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
    """Represents the laser-emitting piece that fires the laser beam."""
    def __init__(self, x, y):
        super().__init__(x, y, RED,image_path="assets/images/lzrImg.png")
        self.x, self.y = x, y
        self.rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
        self.grid_position = None
        self.direction = "up"
        self.og_img = self.image
        self.lzrBeamImg = pygame.image.load('assets/images/lzrBeamImg.png')  # Load your laser sprite image
        self.lzrBeamImg = pygame.transform.scale(self.lzrBeamImg, (CELL_SIZE, CELL_SIZE))  # Scale the sprite if needed
    
    def draw(self, surface):
        """Draws the piece on the given surface."""
        if self.image:
            self.rotate_img_direction(screen)
            screen.blit(self.image, self.rect.topleft)
        else:
            pygame.draw.rect(surface, self.color, self.rect)
    
    def rotate_laser(self):
        """Rotates the laser to a new set direction."""
        directions = ["up", "right", "down", "left"]
        current_index = directions.index(self.direction)
        self.direction = directions[(current_index + 1) % len(directions)]

    def rotate_img_direction(self,screen):
        if self.direction == "up":
            self.image = pygame.transform.rotate(self.og_img, 0) 
        elif self.direction == "down":
            self.image = pygame.transform.rotate(self.og_img, 180) 
        elif self.direction == "left":
            self.image = pygame.transform.rotate(self.og_img, 90) 
        elif self.direction == "right":
            self.image = pygame.transform.rotate(self.og_img, -90) 
        
        self.rect = self.image.get_rect(center=self.rect.center)
            
    def fire_laser(self):
        """Fires the laser in its set direction, checking for collisions and scoring points."""
        global score
        if self.grid_position:
            x, y = self.grid_position
            x_origin, y_origin = get_grid_origin()
            laser_path = []  # Store laser path points

            # Move the laser beam once ahead
            if self.direction == "up":
                y -= 1
            elif self.direction == "down":
                y += 1
            elif self.direction == "left":
                x -= 1
            elif self.direction == "right":
                x += 1
                    
            while 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
                start_pos = (x_origin + x * CELL_SIZE + CELL_SIZE // 2, y_origin + y * CELL_SIZE + CELL_SIZE // 2)
                laser_path.append(start_pos)
                
                
                # Check for collisions
                for piece in pntpiece:
                    if piece.grid_position == (x, y):
                        score += piece.value
                        pntpiece.remove(piece)
                        self.draw_laser_path(laser_path)
                        return

                for piece in mirrpiece:
                    if piece.grid_position == (x, y):
                        self.direction = self.reflect_laser(self.direction, piece.mirror_type)
                        break  # Prevent multiple reflections at once
                
                # Check if the laser is at the laser piece's position
                if (x, y) == self.grid_position:
                    break
                                       
                # Move the laser in the current direction
                if self.direction == "up":
                    y -= 1
                elif self.direction == "down":
                    y += 1
                elif self.direction == "left":
                    x -= 1
                elif self.direction == "right":
                    x += 1

            self.draw_laser_path(laser_path)

    def reflect_laser(self, direction, mirror_type):
        """Reflects the laser based on the mirror type."""
        if mirror_type == "/":
            reflection_map = {
                "up": "left",
                "down": "right",
                "left": "up",
                "right": "down"
            }
        else:  # "\" type
            reflection_map = {
                "up": "right",
                "down": "left",
                "left": "down",
                "right": "up"
            }
        return reflection_map[direction]


    def draw_laser_path(self, laser_path):
        """Draws the laser beam with a visual delay, and sprite."""
        for i in range(len(laser_path) - 1):
            start_pos = laser_path[i]
            end_pos = laser_path[i + 1]
            
            # Calculate the direction and length of the segment
            direction = pygame.math.Vector2(end_pos[0] - start_pos[0], end_pos[1] - start_pos[1])
            segment_length = direction.length()
            
            # Normalize the direction vector
            direction.normalize_ip()

            # Calculate the angle for rotation
            angle = direction.angle_to(pygame.math.Vector2(1, 0))

            # Create the sprite and rotate it
            rotated_sprite = pygame.transform.rotate(self.lzrBeamImg, angle)
            sprite_rect = rotated_sprite.get_rect()

            # Position the sprite at the start of the segment, but move it forward by half the sprite's width
            offset = direction * (sprite_rect.width / 2)  # Move the sprite forward by half of its width
            start_pos_offset = start_pos + offset

            # Center the sprite at the adjusted starting position
            sprite_rect.center = start_pos_offset
            sprite_rect.width = int(segment_length)  # Stretch the sprite to match the segment length
            sprite_rect.height = 64  # Keep the height fixed to the sprite's height

            # Draw the rotated sprite
            screen.blit(rotated_sprite, sprite_rect.topleft)

            pygame.display.flip()
            pygame.time.delay(100)



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
    title_font = pygame.font.Font(None, 72)
    subtitle_font = pygame.font.Font(None, 36)
    
    # Title and Subtitle
    title_text = title_font.render("Lazer Showdown", True, WHITE)
    screen.blit(title_text, (screen.get_width() // 2 - title_text.get_width() // 2, 100))
    
    # Instructions
    instructions_text = subtitle_font.render("Click to Start", True, LIGHT_BLUE)
    screen.blit(instructions_text, (screen.get_width() // 2 - instructions_text.get_width() // 2, 300))
    
    # Button area (optional, you can use a button or click anywhere to start)
    pygame.draw.rect(screen, GRAY, (screen.get_width() // 2 - 100, 400, 200, 50))  # Start button
    start_button_text = subtitle_font.render("Start", True, WHITE)
    screen.blit(start_button_text, (screen.get_width() // 2 - start_button_text.get_width() // 2, 415))

    pygame.display.flip()  # Update the screen to show the start screen

    # Event loop for the start screen
    waiting_for_input = True
    while waiting_for_input:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()  # Exit the game entirely
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # If the mouse is clicked inside the start button area, start the game
                button_rect = pygame.Rect(screen.get_width() // 2 - 100, 400, 200, 50)
                if button_rect.collidepoint(event.pos):
                    waiting_for_input = False  # Exit the start screen loop to start the game

#Main Game Loop
def main_game_loop(screen):    
    reset_game()
    draggable_piece = None
    running = True

    while running:
        redraw_scene()

        # Update occupied spaces only when necessary (to track where pieces are placed)
        occupied_spaces = {piece.grid_position for piece in [lzrpiece] + pntpiece + mirrpiece if piece.grid_position}

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False  # Exit the game loop when the window is closed
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)  # Adjust screen size
                redraw_scene()  # Redraw to fit new window size
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if the reset button was clicked
                if button_x <= event.pos[0] <= button_x + BUTTON_WIDTH and button_y <= event.pos[1] <= button_y + BUTTON_HEIGHT:
                    reset_game()
                else:
                    # Iterate through pieces in reverse order to select the top-most one
                    for piece in reversed([lzrpiece] + pntpiece + mirrpiece):
                        if piece.rect.collidepoint(event.pos):  # Check if mouse click is on a piece
                            draggable_piece = piece  # Assign the selected piece
                            draggable_piece.dragging = True  # Enable dragging mode
                            # Store the offset to maintain relative positioning during drag
                            mouse_offset_x = event.pos[0] - piece.rect.x
                            mouse_offset_y = event.pos[1] - piece.rect.y
                            break  # Stop checking after selecting a piece
            elif event.type == pygame.MOUSEBUTTONUP:
                if draggable_piece:
                    draggable_piece.snap_to_grid(occupied_spaces)  # Snap piece to grid after release
                    draggable_piece.dragging = False  # Disable dragging mode
                    # If a mirror was placed, create a duplicate in the palette
                    if isinstance(draggable_piece, mirrorPiece) and draggable_piece.grid_position:
                        mirror_type = draggable_piece.mirror_type
                        x_origin = ((screen.get_width() // 2) + ((GRID_SIZE // 2) * CELL_SIZE)) + (CELL_SIZE)
                        mirrpiece.append(mirrorPiece(x_origin, 550 if mirror_type == '/' else 650, mirror_type))
                    draggable_piece = None  # Clear the selected piece
                    save_game_state()  # Save the current state after movement
            elif event.type == pygame.MOUSEMOTION:
                if draggable_piece and draggable_piece.dragging:
                    # Move the piece while maintaining the relative offset from the cursor
                    draggable_piece.rect.topleft = (event.pos[0] - mouse_offset_x, event.pos[1] - mouse_offset_y)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    lzrpiece.fire_laser()  # Fire the laser when spacebar is pressed
                elif event.key == pygame.K_r:
                    lzrpiece.rotate_laser()  # Rotate the laser when 'R' is pressed
pygame.init()
screen = pygame.display.set_mode((1500, 1000), pygame.RESIZABLE)
pygame.display.set_caption("Lazer Showdown")
font = pygame.font.Font(None, 36)

start_screen()
main_game_loop(screen)

pygame.quit()  # Properly exit pygame when the loop ends

# Made with Love by Denzven 💜 & guided by ChatGPT 🤖