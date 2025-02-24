**TODO list**

**🚨 Urgent:** (Core usability + foundation for scaling)  
- [ ] **Modularize the codebase** — Split into separate files like `pieces.py`, `ui.py`, `game_logic.py`, and `config.py` to make collaboration easier.  
- [ ] **Fix grid snapping issues** — Make drag-and-drop smoother and more predictable.  
- [ ] **Optimize laser reflection and pathing logic** — Clean up and simplify how the laser moves and reflects for easier debugging and future changes.  
- [ ] **Add mobile-friendly controls** — Implement virtual buttons (rotate, fire) and touch-based drag-and-drop for phone compatibility.  
- [ ] **Adaptive UI for different screen sizes** — Ensure grid, buttons, and text scale properly on different resolutions and aspect ratios.  
- [ ] **Add sound effects** — Essential for feedback and the 8-bit vibe (laser firing, hitting pieces, reflections).  

---

**🔥 Important:** (Enhance user experience + visual polish)  
- [ ] **Improve start screen** — Add retro pixel art, flashy logo, and some simple music to set the arcade vibe.  
- [ ] **Add visual feedback** — Pieces glow, shake, or animate when hit by the laser or picked up.  
- [ ] **Laser beam animations** — Make the beam flicker or pulse, and add cool reflection effects.  
- [ ] **Add settings and pause menu** — Options for sound toggle, restart, and quitting the game.  
- [ ] **Add simple particle effects** — Sparks or bursts when the laser hits something.  
- [ ] **Screen shake on impacts** — Small shake effect when the laser hits a point piece for dramatic feedback.  

---

**✅ Required:** (Quality of life + keeping things maintainable)  
- [ ] **Create a config file** — Move all hardcoded numbers, colors, and paths into a single `config.py` for easy tweaks.  
- [ ] **Refactor drawing methods** — Reduce redundant code across piece classes.  
- [ ] **Polish UI layout** — Better alignment and spacing for side palette and buttons.  
- [ ] **Add error handling** — Prevent weird bugs when dragging, rotating, or firing out of bounds.  

---

**🕐 Later:** (Extra flair + long-term expansion)  
- [ ] **Add CRT-style screen effect** — Scanlines or slight distortion to add an old-school arcade feel.  
- [ ] **Implement high-score tracking** — Save top scores locally or to an online leaderboard.  
- [ ] **New mirror types and mechanics** — Introduce more advanced mirror types with different reflection behaviors.  
- [ ] **Power-ups or special items** — Pieces that change the laser’s properties or give bonuses.  
- [ ] **Multiplayer mode** — Local or online competitive/co-op play.  
- [ ] **Level editor** — Let players create and share custom levels.  

