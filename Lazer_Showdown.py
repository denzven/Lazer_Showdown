import pygame
import random
import os
import sys
import json
import uuid

GRID_SIZE = 8
GRID_WIDTH = 4
CELL_SIZE = 100
TOP_MARGIN = 100
PALETTE_BOX_SIZE = CELL_SIZE
BUTTON_WIDTH, BUTTON_HEIGHT = 128, 64

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (200, 50, 50)
LIGHT_BLUE = (173, 216, 230)
PINK = (255, 182, 193)
GRAY = (100, 100, 100)

def platform():
    if 'ANDROID_ARGUMENT' in os.environ:
        return "android"
    elif sys.platform in ('linux', 'linux2', 'linux3'):
        return "linux"
    elif sys.platform in ('win32', 'cygwin'):
        return 'win'

if platform() == "android":
    PATH = "/data/data/org.test.pgame/files/app/"
elif platform() == "linux":
    PATH = "./"
else:
    PATH = os.path.abspath(".") + "/"

class Button:
    def __init__(self, image_path, position, scale=1.0):
        self.image = pygame.image.load(image_path).convert_alpha()
        w, h = self.image.get_width(), self.image.get_height()
        self.image = pygame.transform.scale(self.image, (int(w * scale), int(h * scale)))
        self.rect = self.image.get_rect(center=position)
        self.pressed = False

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def is_pressed(self):
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
        return {
            'score': self.score,
            'laser': {'pos': self.laser_piece.grid_position, 'dir': self.laser_piece.direction, 'palette': self.laser_piece.palette_position},
            'points': [{'pos': p.grid_position, 'value': p.value, 'palette': p.palette_position} for p in self.point_pieces],
            'mirrors': [{'pos': m.grid_position, 'type': m.mirror_type, 'palette': m.palette_position} for m in self.mirror_pieces],
            'dice': [{'value': d.value} for d in self.dice_list]
        }

    def load(self, s):
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
    def __init__(self, screen):
        self.screen = screen
        self.state = GameState()
        self.font = pygame.font.Font(PATH + 'assets/fonts/Font.ttf', 32)
        self.undo_stack = []
        self.redo_stack = []
        self.save_folder = PATH + "savedgames/"

    def get_dimensions(self): return self.screen.get_size()

    def get_grid_origin(self):
        w, h = self.get_dimensions()
        return (w//2 - (GRID_SIZE//2)*CELL_SIZE, h//2 - (GRID_SIZE//2)*CELL_SIZE)

    def reset_game(self):
        w, h = self.get_dimensions()
        po = (w//2 + (GRID_SIZE//2)*CELL_SIZE) + CELL_SIZE
        pygame.draw.rect(self.screen, BLACK, (po, 0, CELL_SIZE, h))
        self.state.reset(po)
        self.redraw_scene()

    def draw_grid(self):
        xo, yo = self.get_grid_origin()
        for i in range(GRID_SIZE+1):
            pygame.draw.line(self.screen, WHITE, (xo, yo + i*CELL_SIZE), (xo + GRID_SIZE*CELL_SIZE, yo + i*CELL_SIZE), GRID_WIDTH)
            pygame.draw.line(self.screen, WHITE, (xo + i*CELL_SIZE, yo), (xo + i*CELL_SIZE, yo + GRID_SIZE*CELL_SIZE), GRID_WIDTH)

    def draw_palette(self):
        w, h = self.get_dimensions()
        xo = (w//2 + (GRID_SIZE//2)*CELL_SIZE) + CELL_SIZE
        pygame.draw.rect(self.screen, BLACK, (xo, 0, CELL_SIZE, h), GRID_WIDTH)
        for y in [150,250,350,450,550,650]:
            pygame.draw.rect(self.screen, WHITE, (xo, y, PALETTE_BOX_SIZE, PALETTE_BOX_SIZE), GRID_WIDTH)

    def draw_scoreboard(self):
        t = self.font.render(f"Score: {self.state.score}", True, WHITE)
        self.screen.blit(t, (50,50))

    def redraw_scene(self):
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
        s=pygame.display.get_surface(); w,h=s.get_size()
        return (w//2 - (GRID_SIZE//2)*CELL_SIZE, h//2 - (GRID_SIZE//2)*CELL_SIZE)

    def save_state(self): self.undo_stack.append(self.state.save()); self.redo_stack.clear()
    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.state.save())
            prev=self.undo_stack.pop(); self.state.load(prev); self.redraw_scene()
    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.state.save())
            nxt=self.redo_stack.pop(); self.state.load(nxt); self.redraw_scene()

    def save_to_file(self, filename=None):
        if filename is None:
            code=uuid.uuid4().hex[:8]
            filename=os.path.join(self.save_folder, f"lzrshwdn_{code}.json")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename,'w') as f: json.dump(self.state.save(),f,indent=2)
        print(f"Game saved to {filename}")

    def choose_save_file(self):
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
        if filename is None:
            filename=self.choose_save_file()
            if not filename: return
        with open(filename,'r') as f: snapshot=json.load(f)
        self.undo_stack.clear(); self.redo_stack.clear()
        self.state.load(snapshot); self.redraw_scene(); print(f"Game loaded from {filename}")

class Piece:
    def __init__(self,x,y,color,image_path=None):
        self.grid_position=None; self.palette_position=(x,y); self.update_position_from_grid()
        self.color=color; self.dragging=False; self.image=None
        if image_path:
            self.image=pygame.image.load(image_path)
            self.image=pygame.transform.scale(self.image,(CELL_SIZE,CELL_SIZE))
        self.rect=pygame.Rect(x,y,CELL_SIZE,CELL_SIZE)
    def draw(self,surface):
        if self.image: surface.blit(self.image,self.rect.topleft)
        else: pygame.draw.rect(surface,self.color,self.rect)
    def update_position_from_grid(self):
        if self.grid_position:
            xo,yo=GameManager.get_grid_origin_static()
            self.rect=pygame.Rect(xo+self.grid_position[0]*CELL_SIZE,yo+self.grid_position[1]*CELL_SIZE,CELL_SIZE,CELL_SIZE)
        else:
            self.rect=pygame.Rect(self.palette_position[0],self.palette_position[1],CELL_SIZE,CELL_SIZE)
    def snap_to_grid(self,occupied):
        xo,yo=GameManager.get_grid_origin_static()
        gx=(self.rect.x-xo+CELL_SIZE//2)//CELL_SIZE; gy=(self.rect.y-yo+CELL_SIZE//2)//CELL_SIZE
        if 0<=gx<GRID_SIZE and 0<=gy<GRID_SIZE and (gx,gy) not in occupied: self.grid_position=(gx,gy)
        else: self.grid_position=None
        self.update_position_from_grid()

class lazerPiece(Piece):
    def __init__(self,x,y):
        super().__init__(x,y,RED,image_path="assets/images/lzrImg.png")
        self.grid_position=None; self.direction="up"; self.og_img=self.image
        self.lzrBeamImg=pygame.transform.scale(pygame.image.load(PATH+'assets/images/lzrBeamImg.png'),(CELL_SIZE,CELL_SIZE))
        self.lzrBeamstrtImg=pygame.transform.scale(pygame.image.load(PATH+'assets/images/lzrBeamstrtImg.png'),(CELL_SIZE,CELL_SIZE))
    def draw(self,screen): self.rotate_img_direction(); screen.blit(self.image,self.rect.topleft)
    def rotate_laser(self):
        dirs=["up","right","down","left"]; idx=dirs.index(self.direction); self.direction=dirs[(idx+1)%4]
    def rotate_img_direction(self):
        ang={"up":0,"down":180,"left":90,"right":-90}[self.direction]
        self.image=pygame.transform.rotate(self.og_img,ang); self.rect=self.image.get_rect(center=self.rect.center)
    def fire_laser(self,gs):
        if not self.grid_position: return
        path=self.calculate_laser_path(gs); self.apply_laser_effects(gs,path); self.draw_laser_path(path)
    def calculate_laser_path(self,gs):
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
        pygame.display.flip(); pygame.time.delay(100)
        for i in range(len(path)-1):
            s=path[i]; e=path[i+1]
            v=pygame.math.Vector2(e[0]-s[0],e[1]-s[1]); ang=v.angle_to(pygame.math.Vector2(1,0))
            spr=pygame.transform.rotate(self.lzrBeamImg,ang); screen.blit(spr,pygame.Rect(spr.get_rect(center=s).topleft,()).topleft)
            if i==0:
                st=pygame.transform.rotate(self.lzrBeamstrtImg,ang); screen.blit(st,st.get_rect(center=s).topleft)
            pygame.display.flip(); pygame.time.delay(100)
    def reflect_laser(self,d,mt):
        if mt=="/": return {"up":"left","down":"right","left":"up","right":"down"}[d]
        return {"up":"right","down":"left","left":"down","right":"up"}[d]
    def _dir_to_delta(self,d): return {"up":(0,-1),"down":(0,1),"left":(-1,0),"right":(1,0)}[d]

class pointPiece(Piece):
    def __init__(self,x,y,val): super().__init__(x,y,PINK,image_path=self.get_image_path(val)); self.value=val
    def get_image_path(self,v):
        return {20:"assets/images/pntImg20.png",30:"assets/images/pntImg30.png",50:"assets/images/pntImg50.png"}.get(v,"assets/images/pntDefImg.png")

class mirrorPiece(Piece):
    
    def __init__(self,x,y,mt="/"): super().__init__(x,y,GRAY,image_path="assets/images/mirrImg.png"); self.mirror_type=mt; self.grid_position=None; self.og_img=self.image
    def draw(self,screen):
        if self.mirror_type=="/": screen.blit(self.image,self.rect.topleft)
        else: screen.blit(pygame.transform.flip(self.og_img,True,False),self.rect.topleft)

class Dice(pygame.sprite.Sprite):
    def __init__(self,x,y):
        super().__init__()
        self.images=[pygame.transform.scale(pygame.image.load(PATH+f'assets/images/dice/{i}.png'),(CELL_SIZE,CELL_SIZE)) for i in range(1,7)]
        self.value=random.randint(0,5); self.image=self.images[self.value]; self.rect=self.image.get_rect(x=x,y=y)
    def roll(self): self.value=random.randint(0,5); self.image=self.images[self.value]
    def draw(self,surface):
        if self.image: surface.blit(self.image,self.rect.topleft)
        else: pygame.draw.rect(surface,RED,self.rect)

def start_screen():
    screen.fill(BLACK)
    title_f=pygame.font.Font(PATH+'assets/fonts/Font.ttf',72)
    sub_f=pygame.font.Font(PATH+'assets/fonts/Font.ttf',32)
    logo=pygame.transform.scale(pygame.image.load("assets/images/logo.png"),(768,192)); screen.blit(logo,(screen.get_width()//2-logo.get_width()//2,50))
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
