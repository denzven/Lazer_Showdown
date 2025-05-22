# main.py

import os, json, random

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import BooleanProperty, ListProperty, StringProperty, NumericProperty
from kivy.clock import Clock
from kivy.graphics import (
    Color, Line, Rectangle,
    PushMatrix, PopMatrix, Rotate, Scale
)
from kivy.core.image import Image as CoreImage
from kivy.core.image import Image as CoreImage
from kivy.core.text import LabelBase

# ── Window ────────────────────────────────────────────────────────────────────
Window.size = (1500, 1000)
Window.minimum_width, Window.minimum_height = (800, 600)
Window.clearcolor = (0, 0, 0, 1)

# ── Constants ─────────────────────────────────────────────────────────────────
GRID_SIZE   = 8
CELL_SIZE   = 100

BUTTON_CTR  = {
    'fire':    (200, 100),
    'rotate':  (200, 200),
    'roll':    (200, 300),
    'restart': (200, 450),
    'save':    (1300, 825),
    'load':    (1300, 945),
}
PIECE_SLOTS_Y = [150,250,350,450,550,650]
DICE_COORDS   = [(200-CELL_SIZE//2,850),(200-CELL_SIZE//2,700)]
SAVE_FILE     = "lazer_showdown_save.json"

LabelBase.register(name="GameFont", fn_regular="assets/fonts/Font.ttf")

# ── Helpers ──────────────────────────────────────────────────────────────────
def snap_to_grid(x, y, gx, gy):
    cx = int((x - gx)//CELL_SIZE); cy = int((y - gy)//CELL_SIZE)
    if 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE:
        return cx, cy
    return None

# ── Draggable & Subclasses ───────────────────────────────────────────────────
class DraggablePiece(Image):
    dragging = BooleanProperty(False)
    grid_position = ListProperty([None, None])
    palette_position = ListProperty([0, 0])
    slot_index = NumericProperty(-1)

    def __init__(self, **k):
        super().__init__(**k)
        self.allow_stretch = True
        self.size = (CELL_SIZE, CELL_SIZE)
        Clock.schedule_once(self._store)

    def _store(self, dt):
        self.palette_position = list(self.pos)

    def on_touch_down(self, t):
        if self.collide_point(*t.pos):
            self.dragging = True
            return True
        return super().on_touch_down(t)

    def on_touch_move(self, t):
        if self.dragging:
            self.center = t.pos
            return True
        return super().on_touch_move(t)

    def on_touch_up(self, touch):
        if self.dragging:
            self.dragging = False
            gx, gy = self.parent.grid_x, self.parent.grid_y
            g = snap_to_grid(*self.center, gx, gy)
            if g:
                # dropped on grid
                self.grid_position = g
                self.pos = (gx + g[0]*CELL_SIZE, gy + g[1]*CELL_SIZE)

                # if it's a mirror, spawn a fresh one in its palette slot
                if isinstance(self, MirrorPiece):
                    # compute palette pos from slot_index
                    h = Window.height
                    px = self.parent.palette_x
                    top = PIECE_SLOTS_Y[self.slot_index]
                    py = h - top - CELL_SIZE

                    m = MirrorPiece(self.mirror_type, slot_index=self.slot_index)
                    m.pos = (px, py)
                    m.palette_position = (px, py)
                    self.parent.add_widget(m)
                    self.parent.pieces.append(m)

            else:
                # return to palette
                self.pos = tuple(self.palette_position)
            return True
        return super().on_touch_up(touch)

class LaserPiece(DraggablePiece):
    direction = StringProperty("up")
    def __init__(self, **k):
        super().__init__(**k)
        self.source = "assets/images/lzrImg.png"
        # beam sprite
        self.beam_tex = CoreImage("assets/images/lzrBeamImg.png").texture
        # rotation transform
        with self.canvas.before:
            PushMatrix()
            self._rot = Rotate(origin=self.center, angle=0)
        with self.canvas.after:
            PopMatrix()
        self.bind(direction=self._upd, pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self._rot.origin = self.center
        self._rot.angle = {"up":0,"right":-90,"down":180,"left":90}[self.direction]

class PointPiece(DraggablePiece):
    def __init__(self, v, **k):
        super().__init__(**k)
        self.value = v
        self.source = f"assets/images/pntImg{v}.png"

class MirrorPiece(DraggablePiece):
    mirror_type = StringProperty("/")

    def __init__(self, mirror_type, slot_index=-1, **kwargs):
        super().__init__(**kwargs)
        self.mirror_type = mirror_type
        self.slot_index = slot_index
        self.source = "assets/images/mirrImg.png"

        # flip only the "/" mirror
        if mirror_type == "/":
            with self.canvas.before:
                PushMatrix()
                # flip horizontally
                self._flip = Scale(-1, 1, 1, origin=self.center)
            with self.canvas.after:
                PopMatrix()
            # keep origin updated
            self.bind(pos=self._update_flip_origin, size=self._update_flip_origin)

    def _update_flip_origin(self, *args):
        if hasattr(self, "_flip"):
            self._flip.origin = self.center

# ── GridWidget ───────────────────────────────────────────────────────────────
class GridWidget(Widget):
    def __init__(self, **k):
        super().__init__(**k)
        self.pieces = []
        self._undo, self._redo = [], []
        # laser slot
        self.laser = LaserPiece(slot_index=0); self.add_widget(self.laser)
        # point slots
        for i, v in enumerate([20,30,50], start=1):
            p = PointPiece(v, slot_index=i); self.add_widget(p); self.pieces.append(p)
        # mirror slots
        for i,mt in enumerate(['/','\\'], start=4):
            m = MirrorPiece(mt, slot_index=i); self.add_widget(m); self.pieces.append(m)
        Clock.schedule_once(lambda dt: self._layout())
        Window.bind(size=lambda *a: self._layout())

    def _layout(self):
        w,h = Window.size
        self.grid_x = w//2 - (GRID_SIZE*CELL_SIZE)//2
        self.grid_y = h//2 - (GRID_SIZE*CELL_SIZE)//2
        self.palette_x = self.grid_x + GRID_SIZE*CELL_SIZE + CELL_SIZE

        self.canvas.before.clear()
        with self.canvas.before:
            Color(1,1,1)
            for i in range(GRID_SIZE+1):
                Line(points=[self.grid_x, self.grid_y+i*CELL_SIZE,
                             self.grid_x+GRID_SIZE*CELL_SIZE, self.grid_y+i*CELL_SIZE], width=2)
                Line(points=[self.grid_x+i*CELL_SIZE, self.grid_y,
                             self.grid_x+i*CELL_SIZE, self.grid_y+GRID_SIZE*CELL_SIZE], width=2)
            Color(0,0,0); Rectangle(pos=(self.palette_x,0), size=(CELL_SIZE,h))
            Color(1,1,1)
            for y in PIECE_SLOTS_Y:
                py = h - y - CELL_SIZE
                Line(rectangle=(self.palette_x,py,CELL_SIZE,CELL_SIZE), width=2)

        for wgt in [self.laser] + self.pieces:
            gp = wgt.grid_position
            if gp[0] is not None:
                wgt.pos = (self.grid_x+gp[0]*CELL_SIZE, self.grid_y+gp[1]*CELL_SIZE)
            else:
                top = PIECE_SLOTS_Y[wgt.slot_index]
                py = h - top - CELL_SIZE
                wgt.pos = (self.palette_x, py)
                wgt.palette_position = wgt.pos

    def save_state(self):
        snap = {
            'laser': (list(self.laser.grid_position), self.laser.direction),
            'pieces': [(w.__class__.__name__, list(w.grid_position or []),
                        getattr(w,'value',None), getattr(w,'mirror_type',None))
                       for w in self.pieces]
        }
        self._undo.append(snap); self._redo.clear()

    def restore_state(self, snap):
        lp,dr = snap['laser']
        self.laser.grid_position = lp or [None,None]; self.laser.direction = dr
        for w in list(self.pieces): self.remove_widget(w)
        self.pieces.clear()
        for idx,(cls,g,val,mt) in enumerate(snap['pieces'], start=1):
            if cls=="PointPiece": w=PointPiece(val,slot_index=idx)
            else: w=MirrorPiece(mt,slot_index=idx)
            self.add_widget(w); self.pieces.append(w); w.grid_position = g or [None,None]
        self._layout()

    def undo(self):
        if self._undo:
            s=self._undo.pop(); self._redo.append(s); self.restore_state(s)
    def redo(self):
        if self._redo:
            s=self._redo.pop(); self._undo.append(s); self.restore_state(s)

    def trace_laser(self, cb):
        if self.laser.grid_position[0] is None: return
        d = self.laser.direction; x,y = self.laser.grid_position
        deltas = {'up':(0,1),'down':(0,-1),'left':(-1,0),'right':(1,0)}
        dx,dy = deltas[d]; x+=dx; y+=dy
        path = []
        while 0<=x<GRID_SIZE and 0<=y<GRID_SIZE:
            cx = self.grid_x + x*CELL_SIZE + CELL_SIZE/2
            cy = self.grid_y + y*CELL_SIZE + CELL_SIZE/2
            path.append((cx,cy))
            hit = None
            for w in list(self.pieces):
                if w.grid_position == [x,y]:
                    if isinstance(w, PointPiece):
                        hit = w.value; self.remove_widget(w); self.pieces.remove(w)
                    else:
                        refl = {'/':{'up':'right','right':'up','down':'left','left':'down'},
                                '\\':{'up':'left','left':'up','down':'right','right':'down'}}[w.mirror_type]
                        d = refl[d]; dx,dy = deltas[d]
                    break
            if hit is not None:
                cb(hit); break
            x+=dx; y+=dy
        else:
            cb(0)

        # draw beam sprites
        self.canvas.after.clear()
        with self.canvas.after:
            for (cx,cy),next_pt in zip(path, path[1:]):
                nx,ny = next_pt
                ang = ((nx-cx, ny-cy))
                # compute angle in degrees
                from math import atan2, degrees
                a = degrees(atan2(ny-cy, nx-cx))
                PushMatrix()
                Rotate(angle=a, origin=(cx,cy))
                Rectangle(texture=self.laser.beam_tex,
                          size=(CELL_SIZE, CELL_SIZE),
                          pos=(cx-CELL_SIZE/2, cy-CELL_SIZE/2))
                PopMatrix()
        Clock.schedule_once(lambda dt: self.canvas.after.clear(), .5)

# ── ControlPanel ────────────────────────────────────────────────────────────
class ControlPanel(FloatLayout):
    def __init__(self, grid, **k):
        super().__init__(**k)
        self.grid, self.score, self.dice = grid, 0, [1,1]

        # — Buttons —
        self._btns = {}
        for name, (cx, cy) in BUTTON_CTR.items():
            # load the PNG to get its natural size
            tex = CoreImage(f"assets/images/btn/{name.capitalize()}BtnImg.png").texture
            w, h = tex.size
            w, h = w*1.5, h*1.5

            btn = Button(
                size_hint=(None,None), size=(w,h),
                background_normal=f"assets/images/btn/{name.capitalize()}BtnImg.png",
                background_down=f"assets/images/btn/{name.capitalize()}BtnImg.png"
            )
            # position by center
            btn.center_x = cx
            btn.center_y = Window.height - cy

            btn.bind(on_press=getattr(self, name))
            self._btns[name] = btn
            self.add_widget(btn)

        # — Dice images —
        self.dice_imgs = []
        for x, y in DICE_COORDS:
            img = Image(size_hint=(None,None), size=(CELL_SIZE,CELL_SIZE), allow_stretch=True)
            img.center_x = x + CELL_SIZE/2
            img.center_y = Window.height - y - CELL_SIZE/2
            img.coord = (x,y)
            self.dice_imgs.append(img)
            self.add_widget(img)

        # — Score label —
        self.score_lbl = Label(
            text="Score: 0",
            font_name="GameFont",
            font_size=32,
            size_hint=(None,None)
        )
        self.score_lbl.pos = (50, Window.height - 50)
        self.add_widget(self.score_lbl)

        Window.bind(size=lambda *a: self._layout())
        Clock.schedule_once(lambda dt: self._layout())

    def _layout(self, *args):
        w,h = Window.size

        # re-center buttons
        for name, btn in self._btns.items():
            cx, cy = BUTTON_CTR[name]
            btn.center_x = cx
            btn.center_y = h - cy

        # re-center dice
        for i, img in enumerate(self.dice_imgs):
            x,y = img.coord
            img.source = f"assets/images/dice/{self.dice[i]}.png"
            img.center_x = x + CELL_SIZE/2
            img.center_y = h - y - CELL_SIZE/2

        # score
        self.score_lbl.pos = (50, h - 50)
        # reposition dice
        for i, img in enumerate(self.dice_imgs):
            x, y = img.coord
            img.source = f"assets/images/dice/{self.dice[i]}.png"
            img.pos = (x, h - y - CELL_SIZE)

        # reposition score
        self.score_lbl.pos = (50, h - 50)

    def update_score(self,v):
        self.score+=v; self.score_lbl.text = f"Score: {self.score}"

    def fire(self, *_):    self.grid.save_state(); self.grid.trace_laser(self._on_hit)
    def _on_hit(self, v):  self.update_score(v) if v else None
    def rotate(self, *_):  self.grid.save_state(); lp=self.grid.laser; dirs=['up','right','down','left']; lp.direction = dirs[(dirs.index(lp.direction)+1)%4]
    def roll(self, *_):    self.grid.save_state(); self.dice=[random.randint(1,6) for _ in self.dice]; self._layout()
    def undo(self, *_):    self.grid.undo()
    def redo(self, *_):    self.grid.redo()
    def restart(self,*_):  self.grid.restore_state(self.grid._undo[0]) if self.grid._undo else None
    def save(self, *_):
        snap={"score":self.score,"dice":self.dice,
              "laser":{"pos":self.grid.laser.grid_position,"dir":self.grid.laser.direction},
              "pieces":[{"type":w.__class__.__name__,"grid":w.grid_position,"value":getattr(w,'value',None),"mirror_type":getattr(w,'mirror_type',None)} for w in self.grid.pieces]}
        with open(SAVE_FILE,'w') as f: json.dump(snap,f)
    def load(self, *_):
        try: d=json.load(open(SAVE_FILE))
        except: return
        self.score,self.dice = d["score"],d["dice"]
        self.score_lbl.text = f"Score: {self.score}"
        self.grid.restore_state({
            'laser': (d["laser"]["pos"],d["laser"]["dir"]),
            'pieces': [(p["type"],p["grid"],p["value"],p["mirror_type"]) for p in d["pieces"]]
        })
        self._layout()

# ── App ──────────────────────────────────────────────────────────────────────
class LazerShowdownApp(App):
    def build(self):
        root = FloatLayout()
        self.grid = GridWidget(size_hint=(1,1)); root.add_widget(self.grid)
        self.ctrl = ControlPanel(self.grid, size_hint=(1,1)); root.add_widget(self.ctrl)
        return root

if __name__ == "__main__":
    LazerShowdownApp().run()
