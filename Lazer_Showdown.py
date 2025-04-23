import pygame
import random
import os
import sys
import json
import uuid

"""
Lazer Showdown Game Module

Welcome to Lazer Showdown—a dynamic, grid-based puzzle of precision and strategy. The player begins with a red laser emitter on the right-hand palette, along with angled mirrors and point pieces valued at 20, 30, or 50 points. Drag and place these elements onto an 8×8 board to chart the perfect beam path:

- Position and rotate the laser emitter to aim your shot.
- Place mirrors ("/" or "\") to reflect the beam.
- Collect point pieces by directing the laser through them before it exits the grid.
- Roll dice to introduce random events, and use undo/redo to refine your strategy.

Controls:
  • Drag with the mouse to move pieces; right-click to place.
  • Press R or the Rotate button to spin the laser emitter.
  • Press SPACE or the Fire button to launch the beam.
  • Press D or the Roll button to shake the dice.
  • Press Z/Y for undo/redo moves.
  • Press S/L to save or load your game.

Master the art of reflection, maximize your score, and outsmart each puzzle in Lazer Showdown!
"""

# Constants for grid and UI layout
GRID_SIZE = 8
GRID_WIDTH = 4
CELL_SIZE = 100
TOP_MARGIN = 100
PALETTE_BOX_SIZE = CELL_SIZE
BUTTON_WIDTH, BUTTON_HEIGHT = 128, 64

# Color definitions
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (200, 50, 50)
LIGHT_BLUE = (173, 216, 230)
PINK = (255, 182, 193)
GRAY = (100, 100, 100)

def platform():
    """
    Detect current running platform.

    Returns:
        str: One of 'android', 'linux', or 'win' indicating platform type.
    """
    if 'ANDROID_ARGUMENT' in os.environ:
        return "android"
    elif sys.platform in ('linux', 'linux2', 'linux3'):
        return "linux"
    elif sys.platform in ('win32', 'cygwin'):
        return 'win'

# Determine asset path based on platform
if platform() == "android":
    PATH = "/data/data/org.test.pgame/files/app/"
elif platform() == "linux":
    PATH = "./"
else:
    PATH = os.path.abspath(".") + "/"

class Button:
    """
    UI button representation supporting mouse and touch interaction.

    Attributes:
        image (Surface): Pygame surface for the button graphic.
        rect (Rect): Rectangle defining button position and size.
        pressed (bool): Internal state to debounce press events.

    Methods:
        draw(screen): Render the button on the given screen surface.
        is_pressed(): Return True once when the button is pressed.
    """
    def __init__(self, image_path, position, scale=1.0):
        """
        Initialize a Button instance.

        Args:
            image_path (str): Path to the button image file.
            position (tuple): (x, y) coordinates for the button center.
            scale (float): Scale factor for the button image.
        """
        self.image = pygame.image.load(image_path).convert_alpha()
        w, h = self.image.get_width(), self.image.get_height()
        self.image = pygame.transform.scale(self.image, (int(w * scale), int(h * scale)))
        self.rect = self.image.get_rect(center=position)
        self.pressed = False

    def draw(self, screen):
        """
        Draw the button on the given screen.

        Args:
            screen (Surface): Pygame display surface.
        """
        screen.blit(self.image, self.rect)

    def is_pressed(self):
        """
        Check if the button has been pressed this frame.

        Supports mouse click and touch events.

        Returns:
            bool: True if the button transitioned to pressed state.
        """
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]
        touch_events = [e for e in pygame.event.get(pygame.FINGERDOWN)]
        touch_pos = None
        if touch_events:
            t = touch_events[0]
            touch_pos = (int(t.x * screen.get_width()), int(t.y * screen.get_height()))
        pressed = (mouse_pressed and self.rect.collidepoint(mouse_pos)) or (touch_pos and self.rect.collidepoint(touch_pos))
        if pressed and not self.pressed:
            self.pressed = True
            return True
        if not mouse_pressed and not touch_events:
            self.pressed = False
        return False

class GameState:
    """
    Encapsulates the dynamic state of the game including pieces, score, and dice.

    Attributes:
        score (int): Current player score.
        laser_piece (lazerPiece): The player's laser piece.
        point_pieces (list): List of pointPiece instances on the palette or board.
        mirror_pieces (list): List of mirrorPiece instances on the palette or board.
        dice_list (list): List of Dice objects representing game dice.

    Methods:
        reset(palette_origin): Reset to initial state and populate palette.
        get_all_pieces(): Return all game pieces for rendering or interaction.
        save(): Serialize state to a dictionary for persistence.
        load(serialized): Load state from a serialized dictionary.
    """
    def __init__(self):
        """
        Create a fresh GameState with default empty values.
        """
        self.score = 0
        self.laser_piece = None
        self.point_pieces = []
        self.mirror_pieces = []
        self.dice_list = []

    def reset(self, palette_origin):
        """
        Initialize or reset state with default pieces at the palette origin.

        Args:
            palette_origin (int): X-coordinate offset for the palette column.
        """
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
        """
        Gather all pieces (laser, points, mirrors) in a single list.

        Returns:
            list: Combined list of the laser and other pieces.
        """
        return [self.laser_piece] + self.point_pieces + self.mirror_pieces

    def save(self):
        """
        Serialize the current game state to a dictionary.

        Returns:
            dict: Dictionary containing score, piece positions, types, and dice values.
        """
        return {
            'score': self.score,
            'laser': {'pos': self.laser_piece.grid_position, 'dir': self.laser_piece.direction, 'palette': self.laser_piece.palette_position},
            'points': [{'pos': p.grid_position, 'value': p.value, 'palette': p.palette_position} for p in self.point_pieces],
            'mirrors': [{'pos': m.grid_position, 'type': m.mirror_type, 'palette': m.palette_position} for m in self.mirror_pieces],
            'dice': [{'value': d.value} for d in self.dice_list]
        }

    def load(self, s):
        """
        Load game state from a serialized dictionary.

        Args:
            s (dict): Serialized state from a previous save().
        """
        self.score = s.get('score', 0)
        li = s.get('laser', {})
        if li and self.laser_piece:
            if 'palette' in li and li['palette'] is not None:
                self.laser_piece.palette_position = tuple(li['palette'])
            pos = li.get('pos')
            self.laser_piece.grid_position = tuple(pos) if pos is not None else None
            self.laser_piece.direction = li.get('dir', self.laser_piece.direction)
            self.laser_piece.update_position_from_grid()
        self.point_pieces = []
        for info in s.get('points', []):
            p = pointPiece(0, 0, info['value'])
            if info.get('palette') is not None:
                p.palette_position = tuple(info['palette'])
            pos = info.get('pos')
            p.grid_position = tuple(pos) if pos is not None else None
            p.update_position_from_grid()
            self.point_pieces.append(p)
        self.mirror_pieces = []
        for info in s.get('mirrors', []):
            m = mirrorPiece(0, 0, info['type'])
            if info.get('palette') is not None:
                m.palette_position = tuple(info['palette'])
            pos = info.get('pos')
            m.grid_position = tuple(pos) if pos is not None else None
            m.update_position_from_grid()
            self.mirror_pieces.append(m)
        for d, info in zip(self.dice_list, s.get('dice', [])):
            d.value = info.get('value', d.value)
            d.image = d.images[d.value]

class GameManager:
    """
    Coordinates rendering, user input, undo/redo, and save/load operations.

    Attributes:
        screen (Surface): Main display surface.
        state (GameState): Current game state instance.
        font (Font): Font used for UI text rendering.
        undo_stack (list): History stack for undo operations.
        redo_stack (list): History stack for redo operations.
        save_folder (str): Directory path for saving game files.

    Methods:
        get_dimensions(): Return screen size.
        get_grid_origin(): Calculate top-left origin of the game grid.
        reset_game(): Initialize a new game session.
        draw_grid(): Draw the square grid lines on screen.
        draw_palette(): Render the piece palette UI.
        draw_scoreboard(): Display current score.
        redraw_scene(): Clear and redraw entire game UI.
        save_state(): Push current state to undo stack.
        undo(): Revert to previous state.
        redo(): Apply next state from redo stack.
        save_to_file(filename=None): Write serialized state to JSON file.
        choose_save_file(): Show UI to pick a save JSON file.
        load_from_file(filename=None): Load state from selected JSON file.
    """
    def __init__(self, screen):
        """
        Initialize GameManager with provided display surface.

        Args:
            screen (Surface): Pygame display to render to.
        """
        self.screen = screen
        self.state = GameState()
        self.font = pygame.font.Font(PATH + 'assets/fonts/Font.ttf', 32)
        self.undo_stack = []
        self.redo_stack = []
        self.save_folder = PATH + "savedgames/"

    def get_dimensions(self):
        """
        Retrieve current window dimensions.

        Returns:
            tuple: (width, height) of the screen surface.
        """
        return self.screen.get_size()

    def get_grid_origin(self):
        """
        Compute top-left pixel coordinates for the grid.

        Returns:
            tuple: (x_offset, y_offset) for grid drawing.
        """
        w, h = self.get_dimensions()
        return (w//2 - (GRID_SIZE//2)*CELL_SIZE, h//2 - (GRID_SIZE//2)*CELL_SIZE)

    def reset_game(self):
        """
        Reset game state and clear relevant UI regions for a new session.
        """
        w, h = self.get_dimensions()
        po = (w//2 + (GRID_SIZE//2)*CELL_SIZE) + CELL_SIZE
        pygame.draw.rect(self.screen, BLACK, (po, 0, CELL_SIZE, h))
        self.state.reset(po)
        self.redraw_scene()

    def draw_grid(self):
        """
        Render the background grid lines on the screen.
        """
        xo, yo = self.get_grid_origin()
        for i in range(GRID_SIZE+1):
            pygame.draw.line(self.screen, WHITE, (xo, yo + i*CELL_SIZE), (xo + GRID_SIZE*CELL_SIZE, yo + i*CELL_SIZE), GRID_WIDTH)
            pygame.draw.line(self.screen, WHITE, (xo + i*CELL_SIZE, yo), (xo + i*CELL_SIZE, yo + GRID_SIZE*CELL_SIZE), GRID_WIDTH)

    def draw_palette(self):
        """
        Render the border and slots for draggable pieces.
        """
        w, h = self.get_dimensions()
        xo = (w//2 + (GRID_SIZE//2)*CELL_SIZE) + CELL_SIZE
        pygame.draw.rect(self.screen, BLACK, (xo, 0, CELL_SIZE, h), GRID_WIDTH)
        for y in [150,250,350,450,550,650]:
            pygame.draw.rect(self.screen, WHITE, (xo, y, PALETTE_BOX_SIZE, PALETTE_BOX_SIZE), GRID_WIDTH)

    def draw_scoreboard(self):
        """
        Draw the current score text on screen.
        """
        t = self.font.render(f"Score: {self.state.score}", True, WHITE)
        self.screen.blit(t, (50,50))

    def redraw_scene(self):
        """
        Clear screen and draw palette, grid, pieces, buttons, and scoreboard.
        """
        self.screen.fill(BLACK)
        self.draw_palette(); self.draw_grid()
        self.state.laser_piece.draw(self.screen)
        for p in self.state.point_pieces: p.draw(self.screen)
        for m in self.state.mirror_pieces: m.draw(self.screen)
        for d in self.state.dice_list: d.draw(self.screen)
        restartBtn.draw(self.screen); rollBtn.draw(self.screen)
        fireBtn.draw(self.screen); rotateBtn.draw(self.screen)
        self.draw_scoreboard(); pygame.display.flip()

    @staticmethod
    def get_grid_origin_static():
        """
        Static version of get_grid_origin using current display surface.

        Returns:
            tuple: (x_offset, y_offset) for grid drawing based on active display.
        """
        s=pygame.display.get_surface(); w,h=s.get_size()
        return (w//2 - (GRID_SIZE//2)*CELL_SIZE, h//2 - (GRID_SIZE//2)*CELL_SIZE)

    def save_state(self):
        """
        Push current serialized state onto the undo stack and clear redo stack.
        """
        self.undo_stack.append(self.state.save()); self.redo_stack.clear()

    def undo(self):
        """
        Restore previous state from undo stack, pushing current to redo stack.
        """
        if self.undo_stack:
            self.redo_stack.append(self.state.save())
            prev=self.undo_stack.pop(); self.state.load(prev); self.redraw_scene()

    def redo(self):
        """
        Reapply next state from redo stack, pushing current to undo stack.
        """
        if self.redo_stack:
            self.undo_stack.append(self.state.save())
            nxt=self.redo_stack.pop(); self.state.load(nxt); self.redraw_scene()

    def save_to_file(self, filename=None):
        """
        Write current state to a JSON file in the save folder.

        Args:
            filename (str, optional): Specific filename to save to.
        """
        if filename is None:
            code=uuid.uuid4().hex[:8]
            filename=os.path.join(self.save_folder, f"lzrshwdn_{code}.json")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename,'w') as f: json.dump(self.state.save(),f,indent=2)
        print(f"Game saved to {filename}")

    def choose_save_file(self):
        """
        Display a scrollable UI list of saved game files for selection.

        Returns:
            str or None: Path to the selected save file, or None if cancelled.
        """
        folder=os.path.join(self.save_folder); os.makedirs(folder,exist_ok=True)
        files=[f for f in os.listdir(folder) if f.endswith(".json")]
        if not files: return None
        w,h=self.screen.get_size(); bx=w-CELL_SIZE
        upBtn=Button(PATH+"assets/images/btn/UpBtnImg.png",(bx,150))
        downBtn=Button(PATH+"assets/images/btn/DownBtnImg.png",(bx,250))
        selectBtn=Button(PATH+"assets/images/btn/SelectBtnImg.png",(bx,350))
        idx=0; clock=pygame.time.Clock(); font=pygame.font.Font(PATH+'assets/fonts/Font.ttf',28)
        while True:
            self.screen.fill((30,30,30))
            panel=pygame.Rect(20,20,w-CELL_SIZE-60,h-40)
            pygame.draw.rect(self.screen,(50,50,50),panel,border_radius=8)
            title=font.render("Select save file",True,WHITE); self.screen.blit(title,(40,40))
            for i,fname in enumerate(files):
                y=80+i*30; col=LIGHT_BLUE if i==idx else WHITE
                txt=font.render(fname,True,col); self.screen.blit(txt,(40,y))
                if i==idx: pygame.draw.rect(self.screen,(100,100,150),pygame.Rect(35,y-2,panel.width-30,28),width=2,border_radius=4)
            upBtn.draw(self.screen); downBtn.draw(self.screen); selectBtn.draw(self.screen); pygame.display.flip()
            for event in pygame.event.get():
                if event.type==pygame.QUIT: return None
            if upBtn.is_pressed(): idx=(idx-1)%len(files)
            if downBtn.is_pressed(): idx=(idx+1)%len(files)
            if selectBtn.is_pressed(): return os.path.join(folder,files[idx])
            keys=pygame.key.get_pressed()
            if keys[pygame.K_UP]: idx=(idx-1)%len(files); pygame.time.delay(150)
            elif keys[pygame.K_DOWN]: idx=(idx+1)%len(files); pygame.time.delay(150)
            elif keys[pygame.K_RETURN]: return os.path.join(folder,files[idx])
            elif keys[pygame.K_ESCAPE]: return None
            clock.tick(30)

    def load_from_file(self, filename=None):
        """
        Load game state from a chosen JSON file and clear history stacks.

        Args:
            filename (str, optional): Specific file to load, or prompts UI if None.
        """
        if filename is None:
            filename=self.choose_save_file()
            if not filename: return
        with open(filename,'r') as f: snapshot=json.load(f)
        self.undo_stack.clear(); self.redo_stack.clear()
        self.state.load(snapshot); self.redraw_scene(); print(f"Game loaded from {filename}")

class Piece:
    """
    Base class for draggable pieces with grid snapping support.

    Attributes:
        grid_position (tuple): (x, y) cell coordinates on board, or None.
        palette_position (tuple): Pixel position in palette when not on board.
        color (tuple): RGB color for rectangle fallback.
        image (Surface): Optional image for the piece.
        rect (Rect): Pygame rect for drawing and collision.
        dragging (bool): Flag indicating if piece is being dragged.

    Methods:
        draw(surface): Render piece at current rect.
        update_position_from_grid(): Update rect based on grid_position or palette_position.
        snap_to_grid(occupied): Snap rect to nearest empty grid cell.
    """
    def __init__(self,x,y,color,image_path=None):
        """
        Initialize a Piece at palette coordinates or load image.

        Args:
            x (int): X pixel coordinate in palette.
            y (int): Y pixel coordinate in palette.
            color (tuple): RGB tuple for fallback drawing.
            image_path (str, optional): Path to an image file.
        """
        self.grid_position=None; self.palette_position=(x,y); self.update_position_from_grid()
        self.color=color; self.dragging=False; self.image=None
        if image_path:
            self.image=pygame.image.load(image_path)
            self.image=pygame.transform.scale(self.image,(CELL_SIZE,CELL_SIZE))
        self.rect=pygame.Rect(x,y,CELL_SIZE,CELL_SIZE)
    def draw(self,surface):
        """
        Draw the piece on a surface using image or colored rect.

        Args:
            surface (Surface): Pygame surface to draw on.
        """
        if self.image: surface.blit(self.image,self.rect.topleft)
        else: pygame.draw.rect(surface,self.color,self.rect)
    def update_position_from_grid(self):
        """
        Update rect position based on grid alignment or palette origin.
        """
        if self.grid_position:
            xo,yo=GameManager.get_grid_origin_static()
            self.rect=pygame.Rect(xo+self.grid_position[0]*CELL_SIZE,yo+self.grid_position[1]*CELL_SIZE,CELL_SIZE,CELL_SIZE)
        else:
            self.rect=pygame.Rect(self.palette_position[0],self.palette_position[1],CELL_SIZE,CELL_SIZE)
    def snap_to_grid(self,occupied):
        """
        Attempt to snap piece center to nearest grid cell if free.

        Args:
            occupied (set): Set of grid positions already taken.
        """
        xo,yo=GameManager.get_grid_origin_static()
        gx=(self.rect.x-xo+CELL_SIZE//2)//CELL_SIZE; gy=(self.rect.y-yo+CELL_SIZE//2)//CELL_SIZE
        if 0<=gx<GRID_SIZE and 0<=gy<GRID_SIZE and (gx,gy) not in occupied: self.grid_position=(gx,gy)
        else: self.grid_position=None
        self.update_position_from_grid()

class lazerPiece(Piece):
    """
    Special piece representing the laser emitter controlled by player.

    Attributes:
        direction (str): One of 'up', 'down', 'left', 'right'.
        og_img (Surface): Original oriented image for rotation.
        lzrBeamImg (Surface): Beam segment image.
        lzrBeamstrtImg (Surface): Beam start image.

    Methods:
        draw(screen): Render laser piece oriented correctly.
        rotate_laser(): Cycle laser direction clockwise.
        rotate_img_direction(): Rotate sprite based on direction.
        fire_laser(gs): Trace and animate laser path on board state.
        calculate_laser_path(gs): Compute beam path until exit or hit.
        apply_laser_effects(gs,path): Apply scoring or removal effects.
        draw_laser_path(path): Animate beam segments visually.
        reflect_laser(d,mt): Reflect direction on mirror interaction.
        _dir_to_delta(d): Convert direction to grid delta.
    """
    def __init__(self,x,y):
        """
        Initialize laser piece at palette location.

        Args:
            x (int): X pixel coordinate in palette.
            y (int): Y pixel coordinate in palette.
        """
        super().__init__(x,y,RED,image_path="assets/images/lzrImg.png")
        self.grid_position=None; self.direction="up"; self.og_img=self.image
        self.lzrBeamImg=pygame.transform.scale(pygame.image.load(PATH+'assets/images/lzrBeamImg.png'),(CELL_SIZE,CELL_SIZE))
        self.lzrBeamstrtImg=pygame.transform.scale(pygame.image.load(PATH+'assets/images/lzrBeamstrtImg.png'),(CELL_SIZE,CELL_SIZE))
    def draw(self,screen):
        self.rotate_img_direction(); screen.blit(self.image,self.rect.topleft)
    def rotate_laser(self):
        """
        Rotate laser direction 90 degrees clockwise.
        """
        dirs=["up","right","down","left"]; idx=dirs.index(self.direction); self.direction=dirs[(idx+1)%4]
    def rotate_img_direction(self):
        """
        Rotate piece sprite to match current direction.
        """
        ang={"up":0,"down":180,"left":90,"right":-90}[self.direction]
        self.image=pygame.transform.rotate(self.og_img,ang); self.rect=self.image.get_rect(center=self.rect.center)
    def fire_laser(self,gs):
        """
        Trigger laser path tracing, effects, and animation.

        Args:
            gs (GameState): Current game state.
        """
        if not self.grid_position: return
        path=self.calculate_laser_path(gs); self.apply_laser_effects(gs,path); self.draw_laser_path(path)
    def calculate_laser_path(self,gs):
        """
        Compute sequence of pixel coordinates for beam through grid.

        Args:
            gs (GameState): Current game state.
        Returns:
            list[tuple]: Ordered list of beam segment center points.
        """
        x,y=self.grid_position; d=self.direction; xo,yo=GameManager.get_grid_origin_static()
        path=[]; dx,dy=self._dir_to_delta(d); x+=dx; y+=dy
        while 0<=x<GRID_SIZE and 0<=y<GRID_SIZE:
            path.append((xo+x*CELL_SIZE+CELL_SIZE//2, yo+y*CELL_SIZE+CELL_SIZE//2))
            for m in gs.mirror_pieces:
                if m.grid_position==(x,y): d=self.reflect_laser(d,m.mirror_type); dx,dy=self._dir_to_delta(d); break
            else:
                for p in gs.point_pieces:
                    if p.grid_position==(x,y): gs.score+=p.value; gs.point_pieces.remove(p); return path
            x+=dx; y+=dy
        return path
    def apply_laser_effects(self,gs,path): pass
    def draw_laser_path(self,path):
        """
        Animate beam segments along computed path.

        Args:
            path (list[tuple]): Beam segment coordinates.
        """
        pygame.display.flip(); pygame.time.delay(100)
        for i in range(len(path)-1):
            s=path[i]; e=path[i+1]
            v=pygame.math.Vector2(e[0]-s[0],e[1]-s[1]); ang=v.angle_to(pygame.math.Vector2(1,0))
            spr=pygame.transform.rotate(self.lzrBeamImg,ang); surface=pygame.display.get_surface(); surface.blit(spr,pygame.Rect(spr.get_rect(center=s).topleft,()).topleft)
            if i==0:
                st=pygame.transform.rotate(self.lzrBeamstrtImg,ang); surface.blit(st,st.get_rect(center=s).topleft)
            pygame.display.flip(); pygame.time.delay(100)
    def reflect_laser(self,d,mt):
        """
        Reflect laser direction based on mirror type.

        Args:
            d (str): Incoming direction.
            mt (str): Mirror type, '/' or '\\'.
        Returns:
            str: New direction after reflection.
        """
        if mt=="/": return {"up":"left","down":"right","left":"up","right":"down"}[d]
        return {"up":"right","down":"left","left":"down","right":"up"}[d]
    def _dir_to_delta(self,d):
        """
        Map direction string to grid coordinate delta.

        Args:
            d (str): Direction keyword.
        Returns:
            tuple: (dx, dy) movement in grid spaces.
        """
        return {"up":(0,-1),"down":(0,1),"left":(-1,0),"right":(1,0)}[d]

class pointPiece(Piece):
    """
    Piece awarding score values when hit by laser.

    Attributes:
        value (int): Point value for this piece.

    Methods:
        get_image_path(value): Return image path for given point value.
    """
    def __init__(self,x,y,val):
        """
        Initialize a scoring piece at palette.

        Args:
            x (int): X pixel coordinate in palette.
            y (int): Y pixel coordinate in palette.
            val (int): Point value (20, 30, or 50).
        """
        super().__init__(x,y,PINK,image_path=self.get_image_path(val))
        self.value=val
    def get_image_path(self,v):
        """
        Map point value to the corresponding asset path.

        Args:
            v (int): Numeric point value.
        Returns:
            str: Relative path to image file.
        """
        return {20:"assets/images/pntImg20.png",30:"assets/images/pntImg30.png",50:"assets/images/pntImg50.png"}.get(v,"assets/images/pntDefImg.png")

class mirrorPiece(Piece):
    """
    Reflective piece that changes laser direction upon contact.

    Attributes:
        mirror_type (str): '/' or '\\' specifying orientation.
        og_img (Surface): Original sprite for flipping.

    Methods:
        draw(screen): Render mirror oriented correctly.
    """
    def __init__(self,x,y,mt="/"):
        """
        Initialize a mirror piece at palette.

        Args:
            x (int): X pixel coordinate in palette.
            y (int): Y pixel coordinate in palette.
            mt (str): Mirror type character ('/' or '\\').
        """
        super().__init__(x,y,GRAY,image_path="assets/images/mirrImg.png")
        self.mirror_type=mt; self.grid_position=None; self.og_img=self.image
    def draw(self,screen):
        """
        Draw the mirror, flipped horizontally if needed.

        Args:
            screen (Surface): Pygame display surface.
        """
        if self.mirror_type=="/": screen.blit(self.image,self.rect.topleft)
        else: screen.blit(pygame.transform.flip(self.og_img,True,False),self.rect.topleft)

class Dice(pygame.sprite.Sprite):
    """
    Six-sided die with random roll behavior and image representation.

    Attributes:
        images (list): Six images for faces 1-6.
        value (int): Current face index (0-5).
        image (Surface): Currently displayed face image.
        rect (Rect): Position and size on screen.

    Methods:
        roll(): Randomly choose a new face value.
        draw(surface): Render die face to surface.
    """
    def __init__(self,x,y):
        """
        Load dice face images and initialize random face.

        Args:
            x (int): X pixel coordinate on board.
            y (int): Y pixel coordinate on board.
        """
        super().__init__()
        self.images=[pygame.transform.scale(pygame.image.load(PATH+f'assets/images/dice/{i}.png'),(CELL_SIZE,CELL_SIZE)) for i in range(1,7)]
        self.value=random.randint(0,5); self.image=self.images[self.value]; self.rect=self.image.get_rect(x=x,y=y)
    def roll(self):
        """
        Change the die to a new random face and update image.
        """
        self.value=random.randint(0,5); self.image=self.images[self.value]
    def draw(self,surface):
        """
        Draw the current die face or fallback rectangle.

        Args:
            surface (Surface): Pygame surface to render on.
        """
        if self.image: surface.blit(self.image,self.rect.topleft)
        else: pygame.draw.rect(surface,RED,self.rect)

def start_screen():
    """
    Display the game's start/title screen and wait for user to begin.
    """
    screen.fill(BLACK)
    title_f=pygame.font.Font(PATH+'assets/fonts/Font.ttf',72)
    sub_f=pygame.font.Font(PATH+'assets/fonts/Font.ttf',32)
    logo=pygame.transform.scale(pygame.image.load("assets/images/logo.png"),(768,192))
    screen.blit(logo,(screen.get_width()//2-logo.get_width()//2,50))
    screen.blit(title_f.render("Lazer Showdown",True,WHITE),(screen.get_width()//2-title_f.size("Lazer Showdown")[0]//2,320))
    instr=["Click to Start","Press R to rotate the lazer","Press SPACE to fire the lazer","Press D to roll the dice","Pick pieces and mirrors with your mouse","Right-click to place pieces"]
    for i,line in enumerate(instr): screen.blit(sub_f.render(line,True,LIGHT_BLUE),(screen.get_width()//2-sub_f.size(line)[0]//2,400+i*40))
    startBtn.draw(screen); pygame.display.flip()
    wait=True
    while wait:
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); exit()
            elif startBtn.is_pressed(): wait=False

def main_game_loop(screen):
    """
    Main event loop handling game updates, rendering, and input.

    Args:
        screen (Surface): Pygame display surface to render game.
    """
    mgr=GameManager(screen); mgr.reset_game(); state=mgr.state; draggable=None; running=True
    while running:
        mgr.redraw_scene(); occupied={p.grid_position for p in state.get_all_pieces() if p.grid_position}
        for e in pygame.event.get():
            if e.type==pygame.QUIT: running=False
            elif e.type==pygame.VIDEORESIZE:
                screen=pygame.display.set_mode((e.w,e.h),pygame.RESIZABLE); mgr.screen=screen; mgr.redraw_scene()
            elif e.type==pygame.MOUSEBUTTONDOWN:
                if restartBtn.is_pressed(): mgr.save_state(); mgr.reset_game()
                else:
                    for p in reversed(state.get_all_pieces()):
                        if p.rect.collidepoint(e.pos): mgr.save_state(); draggable=p; p.dragging=True; offx=e.pos[0]-p.rect.x; offy=e.pos[1]-p.rect.y; break
            elif e.type==pygame.MOUSEBUTTONUP and draggable:
                mgr.save_state(); draggable.snap_to_grid(occupied); draggable.dragging=False
                if isinstance(draggable,mirrorPiece) and draggable.grid_position:
                    mt=draggable.mirror_type; po=(screen.get_width()//2+(GRID_SIZE//2)*CELL_SIZE)+CELL_SIZE; yo=550 if mt=='/' else 650; state.mirror_pieces.append(mirrorPiece(po,yo,mt))
                draggable=None
            elif e.type==pygame.MOUSEMOTION and draggable and draggable.dragging:
                draggable.rect.topleft=(e.pos[0]-offx,e.pos[1]-offy)
            elif e.type==pygame.KEYDOWN:
                if e.key==pygame.K_z: mgr.undo()
                elif e.key==pygame.K_y: mgr.redo()
                elif e.key==pygame.K_SPACE: mgr.save_state(); state.laser_piece.fire_laser(state)
                elif e.key==pygame.K_r: mgr.save_state(); state.laser_piece.rotate_laser()
                elif e.key==pygame.K_d: mgr.save_state(); [d.roll() for d in state.dice_list]
                elif e.key==pygame.K_s: mgr.save_to_file()
                elif e.key==pygame.K_l: mgr.load_from_file()
        if fireBtn.is_pressed(): mgr.save_state(); state.laser_piece.fire_laser(state)
        if rotateBtn.is_pressed(): mgr.save_state(); state.laser_piece.rotate_laser()
        if rollBtn.is_pressed(): mgr.save_state(); [d.roll() for d in state.dice_list]
        if restartBtn.is_pressed(): mgr.save_state(); mgr.reset_game()

# Entry point
pygame.init()
screen=pygame.display.set_mode((1500,1000),pygame.RESIZABLE)
icon=pygame.image.load(PATH+'assets/images/icon.ico')
pygame.display.set_caption("Lazer Showdown")
pygame.display.set_icon(icon)
font=pygame.font.Font(PATH+'assets/fonts/Font.ttf',32)

startBtn=Button(PATH+'assets/images/btn/StartBtnImg.png',(screen.get_width()//2,750),1.5)
fireBtn=Button(PATH+'assets/images/btn/FireBtnImg.png',(200,200),1.5)
rotateBtn=Button(PATH+'assets/images/btn/RotateBtnImg.png',(200,300),1.5)
rollBtn=Button(PATH+'assets/images/btn/RollBtnImg.png',(200,400),1.5)
restartBtn=Button(PATH+'assets/images/btn/RestartBtnImg.png',(200,550),1.5)

start_screen()
main_game_loop(screen)
pygame.quit()

# Made with Love by Denzven 💜 & guided by ChatGPT 🤖