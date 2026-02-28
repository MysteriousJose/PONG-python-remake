"""Pong game built with cmu_graphics.

Controls:
- Singleplayer: P1 uses mouse movement, P2 is AI controlled.
- Twoplayer: P1 uses W/S, P2 uses Up/Down.
- Press R during a match to return to the menu and reset the session.

Gameplay notes:
- The menu lets players choose color scheme, speed cap (difficulty), and mode.
- Ball speed increases every 10 successful paddle hits.
- The game includes responsive scaling so layout and movement stay proportional
  when the window size changes.
"""

from cmu_graphics import *
import random
import time
import re

from cmu_graphics import cmu_graphics

# Startup window size. You can change these freely.
BASE_W = 1920
BASE_H = 1080

# Design-space resolution used by all hardcoded coordinates below.
DESIGN_W = 2560
DESIGN_H = 1440


def sx(x):
    # Convert an X coordinate from design-space (2560 width) to current window width.
    return x * app.width / DESIGN_W


def sy(y):
    # Convert a Y coordinate from design-space (1440 height) to current window height.
    return y * app.height / DESIGN_H


def ss(v):
    # Uniform scaling helper for sizes/radii: uses the smaller axis scale factor.
    return v * min(app.width / DESIGN_W, app.height / DESIGN_H)


def speedUnit():
    # Centralized speed unit so BASE_FPS and scale are defined in one place.
    return BASE_FPS * ss(1)

### APP VARIABLES ###
# Global app setup.
app.background = 'white'
app.width = BASE_W
app.height = BASE_H
app.stepsPerSecond = 240  # Simulation tick rate (onStep calls per second).
app.speedMultiplier = 1
app.gameStart = False  # False = in menu, True = match started.
app.prevTime = time.perf_counter()
app.dt = 1/app.stepsPerSecond  # Time between steps, used for frame-rate independent movement if desired.
BASE_FPS = 144  # Used for frame-rate independent movement if desired.

# Menu selections (defaults).
app.selectedColor = 1
app.selectedLevel = 5

# Core game objects (configured for a 2560x1440 play area).
ball = Circle(sx(1280), sy(720), ss(32), fill="white", visible=False)
app.p1 = Rect(sx(160), sy(576), ss(16), sy(256), fill=None, visible=False)
app.p2 = Rect(sx(2400), sy(576), ss(16), sy(256), fill=None, visible=False)
app.border1 = Rect(0, sy(-30), app.width, sy(40), fill='black', visible=False) # Top border (also used for ball bounce collision).
app.border2 = Rect(0, sy(1430), app.width, sy(40), visible=False) # Bottom border (also used for ball bounce collision).
app.backWall = Rect(0, 0, ss(10), app.height, visible=False)      # Left goal wall.
app.frontWall = Rect(app.width - ss(10), 0, ss(10), app.height, visible=False)  # Right goal wall.

# UI labels for round outcome and score.
loseMsg = Label("P2 Win!", sx(1280), sy(720), size=ss(110), visible=False, fill='green')
winMsg = Label("P1 Win!", sx(1280), sy(720), size=ss(110), visible=False, fill='green')
counter = Label(0, sx(1280), sy(60), size=ss(56), visible=False)

# Ball velocity (pixels per step).
app.dx = 0
app.dy = 0

# Mouse state (safe defaults until first mouse move event).
app.mouseX = 0
app.mouseY = 0
app.mouseTargetY = 200

# Key-hold state for continuous movement.
app.upHeld = False
app.downHeld = False
app.wHeld = False
app.sHeld = False

# Misc game state.
app.scheme2 = False
app.scheme1 = False
app.maxSpeed = 0
app.speedTier = 0
app.paddleSpeed = 30 * BASE_FPS * ss(1)  # Max follow speed for smoothed mouse control (pixels/second).
app.playerPaddleSpeed = 10 * BASE_FPS * ss(1)  # Human paddle speed (pixels/second).
app.p2IsAI = True  # True: singleplayer (P2 AI), False: twoplayer (P2 human).
app.roundOver = False
app.roundTimer = 0
app.roundDelay = 1.5  # How long winner text stays visible.
app.prevW = app.width
app.prevH = app.height

# Key -> color options map: (P1 color, P2 color).
colorOptions = {
    1: ('skyBlue', 'salmon'),
    2: ('lime', 'orange'),
    3: ('white', 'red')
}

# Key -> max speed map by difficulty.
levelOptions = {
    5: 25,    # Easy
    6: 29,    # Medium
    7: 33,    # Hard
    8: 9999   # Infinite speed scaling
}

KEY_HELD_ATTR = {
    'up': 'upHeld',
    'down': 'downHeld',
    'w': 'wHeld',
    's': 'sHeld'
}


### GUI LEVEL SELECT ###
# Start/menu labels. Hidden when game starts.
menuTitle = Label("PONG", sx(1280), sy(288), size=ss(256), fill="black")

# Menu buttons for mouse-based selection.
LEVEL_BTN_TEXT = {
    5: 'Easy',
    6: 'Medium',
    7: 'Hard',
    8: 'Infinite'
}

colorButtons = {}
levelButtons = {}
modeSingleBtn = Rect(0, 0, 1, 1, fill='gainsboro', border='black', borderWidth=2)
modeSingleLbl = Label('Singleplayer', 0, 0, fill='black', size=ss(42))
modeTwoBtn = Rect(0, 0, 1, 1, fill='gainsboro', border='black', borderWidth=2)
modeTwoLbl = Label('Twoplayer', 0, 0, fill='black', size=ss(42))
startBtn = Rect(0, 0, 1, 1, fill='lightGreen', border='darkGreen', borderWidth=2)
startLbl = Label('Start', 0, 0, fill='black', size=ss(52))

for idx in (1, 2, 3):
    colorButtons[idx] = (
        Rect(0, 0, 1, 1, fill='gainsboro', border='black', borderWidth=2),
        Label('', 0, 0, fill='black', size=ss(32))
    )
for idx in (5, 6, 7, 8):
    levelButtons[idx] = (
        Rect(0, 0, 1, 1, fill='gainsboro', border='black', borderWidth=2),
        Label(LEVEL_BTN_TEXT[idx], 0, 0, fill='black', size=ss(38))
    )


def pointInRect(px, py, rect):
    # Basic hit test used by the menu click handler.
    return rect.left <= px <= rect.right and rect.top <= py <= rect.bottom


def updateMenuButtonStyles():
    # Visually indicate selected color, difficulty, and game mode.
    for idx, (btn, _) in colorButtons.items():
        selected = (idx == app.selectedColor)
        btn.border = 'black'
        btn.borderWidth = 6 if selected else 2

    for idx, (btn, _) in levelButtons.items():
        selected = (idx == app.selectedLevel)
        btn.fill = 'khaki' if selected else 'gainsboro'
        btn.borderWidth = 4 if selected else 2

    singleSelected = app.p2IsAI
    modeSingleBtn.fill = 'plum' if singleSelected else 'gainsboro'
    modeSingleBtn.borderWidth = 4 if singleSelected else 2
    modeTwoBtn.fill = 'plum' if not singleSelected else 'gainsboro'
    modeTwoBtn.borderWidth = 4 if not singleSelected else 2


def updateColorButtonPreviews():
    # Keep color button preview swatches and text in sync with colorOptions.
    def prettyColorName(name):
        words = re.sub(r'([a-z])([A-Z])', r'\1 \2', str(name)).replace('-', ' ').split()
        return ' '.join(word.capitalize() for word in words)

    for idx, (btn, lbl) in colorButtons.items():
        p1Color, p2Color = colorOptions[idx]
        lbl.value = f'{prettyColorName(p1Color)}/{prettyColorName(p2Color)}'
        if p1Color == p2Color:
            btn.fill = p1Color
        else:
            btn.fill = gradient(p1Color, p2Color, start='left')


def setMenuButtonsVisible(visible):
    # Show/hide every menu widget in one place to avoid duplicated UI toggles.
    for btn, lbl in colorButtons.values():
        btn.visible = visible
        lbl.visible = visible
    for btn, lbl in levelButtons.values():
        btn.visible = visible
        lbl.visible = visible
    modeSingleBtn.visible = visible
    modeSingleLbl.visible = visible
    modeTwoBtn.visible = visible
    modeTwoLbl.visible = visible
    startBtn.visible = visible
    startLbl.visible = visible


def setGameplayVisible(visible):
    # Show/hide all gameplay-only objects in one place.
    ball.visible = visible
    app.p1.visible = visible
    app.p2.visible = visible
    counter.visible = visible
    app.border1.visible = visible
    app.border2.visible = visible
    app.backWall.visible = visible
    app.frontWall.visible = visible


def serveBall(resetPaddles=False):
    # Place ball at center and relaunch with a randomized direction.
    ball.centerX = sx(1280)
    ball.centerY = sy(720)
    if resetPaddles:
        app.p1.centerY = sy(720)
        app.p2.centerY = sy(720)
        app.mouseTargetY = app.p1.centerY
    app.dx = random.choice([-9, 9]) * speedUnit()  # Start left or right.
    app.dy = random.randrange(-2, 3) * speedUnit()


def clampPaddles():
    # Keep paddles inside playable vertical bounds.
    # Bounds are design-space tuned values scaled to current window size.
    minY = sy(138)
    maxY = sy(1262)
    app.p1.centerY = max(minY, min(maxY, app.p1.centerY))
    app.p2.centerY = max(minY, min(maxY, app.p2.centerY))


def applyResponsiveLayout(oldW=None, oldH=None):
    """Recompute all geometry after startup or window resize.

    If previous dimensions are provided, dynamic objects preserve their
    proportional positions so gameplay does not "jump" on resize.
    """
    # Capture relative positions so dynamic objects stay in-place during resize.
    if oldW is None or oldH is None or oldW <= 0 or oldH <= 0:
        ballRX, ballRY = 0.5, 0.5
        p1RY, p2RY = 0.5, 0.5
    else:
        ballRX = ball.centerX / oldW
        ballRY = ball.centerY / oldH
        p1RY = app.p1.centerY / oldH
        p2RY = app.p2.centerY / oldH

    # Gameplay shape sizes and anchored positions.
    ball.radius = ss(32)
    app.p1.width = ss(16)
    app.p1.height = sy(256)
    app.p2.width = ss(16)
    app.p2.height = sy(256)
    app.p1.left = sx(160)
    app.p2.left = sx(2400)
    app.border1.left = 0
    app.border1.top = sy(-30)
    app.border1.width = app.width
    app.border1.height = sy(40)
    app.border2.left = 0
    app.border2.top = sy(1430)
    app.border2.width = app.width
    app.border2.height = sy(40)
    app.backWall.left = 0
    app.backWall.top = 0
    app.backWall.width = ss(10)
    app.backWall.height = app.height
    app.frontWall.left = app.width - ss(10)
    app.frontWall.top = 0
    app.frontWall.width = ss(10)
    app.frontWall.height = app.height

    # UI positions and text sizes.
    loseMsg.centerX, loseMsg.centerY, loseMsg.size = sx(1280), sy(720), ss(110)
    winMsg.centerX, winMsg.centerY, winMsg.size = sx(1280), sy(720), ss(110)
    counter.centerX, counter.centerY, counter.size = sx(1280), sy(60), ss(56)
    menuTitle.centerX, menuTitle.centerY, menuTitle.size = sx(1280), sy(288), ss(256)

    # Menu button layout.
    colorW, colorH = sx(320), sy(90)
    levelW, levelH = sx(230), sy(90)
    modeW, modeH = sx(340), sy(90)
    startW, startH = sx(400), sy(110)
    colorGap = sx(120)
    levelGap = sx(90)
    modeGap = sx(180)
    colorRowY = sy(860)
    levelRowY = sy(1000)
    modeRowY = sy(1160)
    startRowY = sy(1320)
    colorRowLeft = sx(1280) - ((3 * colorW) + (2 * colorGap)) / 2
    levelRowLeft = sx(1280) - ((4 * levelW) + (3 * levelGap)) / 2

    for i, idx in enumerate((1, 2, 3)):
        btn, lbl = colorButtons[idx]
        btn.left = colorRowLeft + i * (colorW + colorGap)
        btn.top = colorRowY
        btn.width = colorW
        btn.height = colorH
        lbl.centerX = btn.centerX
        lbl.centerY = btn.centerY
        lbl.size = ss(32)

    for i, idx in enumerate((5, 6, 7, 8)):
        btn, lbl = levelButtons[idx]
        btn.left = levelRowLeft + i * (levelW + levelGap)
        btn.top = levelRowY
        btn.width = levelW
        btn.height = levelH
        lbl.centerX = btn.centerX
        lbl.centerY = btn.centerY
        lbl.size = ss(38)

    modeSingleBtn.left, modeSingleBtn.top = sx(1280) - modeGap / 2 - modeW, modeRowY
    modeSingleBtn.width, modeSingleBtn.height = modeW, modeH
    modeSingleLbl.centerX, modeSingleLbl.centerY, modeSingleLbl.size = modeSingleBtn.centerX, modeSingleBtn.centerY, ss(42)

    modeTwoBtn.left, modeTwoBtn.top = sx(1280) + modeGap / 2, modeRowY
    modeTwoBtn.width, modeTwoBtn.height = modeW, modeH
    modeTwoLbl.centerX, modeTwoLbl.centerY, modeTwoLbl.size = modeTwoBtn.centerX, modeTwoBtn.centerY, ss(42)

    startBtn.width, startBtn.height = startW, startH
    startBtn.centerX, startBtn.centerY = sx(1280), startRowY
    startLbl.centerX, startLbl.centerY, startLbl.size = startBtn.centerX, startBtn.centerY, ss(52)

    # Keep object positions proportional to new screen size.
    ball.centerX = ballRX * app.width
    ball.centerY = ballRY * app.height
    app.p1.centerY = p1RY * app.height
    app.p2.centerY = p2RY * app.height
    clampPaddles()
    updateColorButtonPreviews()
    updateMenuButtonStyles()


def onResize():
    """Handle live window resizing.

    Layout is recalculated first, then active movement speeds are scaled
    so current gameplay feel remains consistent at the new size.
    """
    oldW, oldH = app.prevW, app.prevH
    oldScale = min(oldW / DESIGN_W, oldH / DESIGN_H) if oldW > 0 and oldH > 0 else 1
    newScale = min(app.width / DESIGN_W, app.height / DESIGN_H)
    speedFactor = newScale / oldScale if oldScale > 0 else 1

    applyResponsiveLayout(oldW, oldH)

    # Keep movement speeds proportional to the current screen scale.
    app.dx *= speedFactor
    app.dy *= speedFactor
    app.maxSpeed *= speedFactor
    app.paddleSpeed = 30 * BASE_FPS * newScale
    app.playerPaddleSpeed = 10 * BASE_FPS * newScale
    app.prevW = app.width
    app.prevH = app.height


### START SCRIPT ###
def start(color1, color2, levelSelect):
    """Start a new match from the menu selections."""
    # Show gameplay objects.
    setGameplayVisible(True)
    app.p1.fill = color1
    app.p2.fill = color2

    # Reset ball and launch with random horizontal direction.
    serveBall()
    app.maxSpeed = levelSelect * speedUnit()
    app.roundOver = False
    app.roundTimer = 0
    loseMsg.visible = False
    winMsg.visible = False

    # Hide menu UI during match.
    menuTitle.visible = False
    setMenuButtonsVisible(False)
    app.background = "darkGray"

def endRound(p1Won):
    """Stop motion, show winner text, and start short delay before restart."""
    # Freeze game motion and display round winner.
    app.roundOver = True
    app.roundTimer = app.roundDelay
    app.dx = 0
    app.dy = 0
    winMsg.visible = p1Won
    loseMsg.visible = (not p1Won)

def resetRound():
    """Start the next rally after the round-end delay expires."""
    # Hide winner text and relaunch from center for next point.
    winMsg.visible = False
    loseMsg.visible = False
    app.roundOver = False
    app.roundTimer = 0
    counter.value = 0
    serveBall(resetPaddles=True)


### MOVEMENT OF THE PADDLES ###
def onMouseMove(mouseX, mouseY):
    """Update stored mouse position and target paddle position.

    In singleplayer mode, P1 follows this target smoothly in `onStep`.
    """
    # Save raw mouse values if needed for debugging.
    app.mouseX = mouseX
    app.mouseY = mouseY

    # Move target only. Actual paddle motion is smoothed in onStep.
    app.mouseTargetY = mouseY


def onMousePress(mouseX, mouseY):
    # Ignore menu click handling once gameplay has started.
    if app.gameStart:
        return

    for idx, (btn, _) in colorButtons.items():
        if pointInRect(mouseX, mouseY, btn):
            app.selectedColor = idx
            updateMenuButtonStyles()
            return

    for idx, (btn, _) in levelButtons.items():
        if pointInRect(mouseX, mouseY, btn):
            app.selectedLevel = idx
            updateMenuButtonStyles()
            return

    if pointInRect(mouseX, mouseY, modeSingleBtn):
        app.p2IsAI = True
        updateMenuButtonStyles()
        return

    if pointInRect(mouseX, mouseY, modeTwoBtn):
        app.p2IsAI = False
        updateMenuButtonStyles()
        return

    if pointInRect(mouseX, mouseY, startBtn):
        colors = colorOptions[app.selectedColor]
        levelSpeed = levelOptions[app.selectedLevel]
        start(colors[0], colors[1], levelSpeed)
        app.gameStart = True


### KEY PRESS FUNCTIONS ###
def onKeyPress(key):
    """Track key-hold state for continuous movement and handle reset key."""
    # Menu is mouse-only.
    if not app.gameStart:
        return

    # In game: set key-held flags for continuous movement.
    if key == 'r':
        # Reset game state and return to menu.
        app.gameStart = False
        counter.value = 0
        app.speedTier = 0
        app.dx = 0
        app.dy = 0
        app.background = 'white'
        setGameplayVisible(False)
        winMsg.visible = False
        loseMsg.visible = False

        # Show menu UI.
        menuTitle.visible = True
        setMenuButtonsVisible(True)
        updateMenuButtonStyles()
    if key in KEY_HELD_ATTR:
        setattr(app, KEY_HELD_ATTR[key], True)


def onKeyRelease(key):
    """Stop movement on key release by clearing hold flags."""
    # Clear key-held flags on release.
    if key in KEY_HELD_ATTR:
        setattr(app, KEY_HELD_ATTR[key], False)


### INCREASE SPEED EVERY 10 SCORE ###
def increaseSpeed():
    """Increase ball speed once per 10-hit tier."""
    # Every 10 points, increase speed tier once.
    newTier = counter.value // 10  # 0, 1, 2, 3...
    if newTier > app.speedTier:
        app.speedTier = newTier

        # Increase speed while preserving direction.
        if app.dx > 0:
            app.dx += speedUnit()
        else:
            app.dx -= speedUnit()

        if app.dy > 0:
            app.dy += speedUnit()
        else:
            app.dy -= speedUnit()


# Keep speed from increasing beyond selected level max.
def clampSpeed():
    """Keep ball velocity components within the configured speed cap."""
    if app.dx > app.maxSpeed:
        app.dx = app.maxSpeed
    if app.dx < -app.maxSpeed:
        app.dx = -app.maxSpeed
    if app.dy > app.maxSpeed:
        app.dy = app.maxSpeed
    if app.dy < -app.maxSpeed:
        app.dy = -app.maxSpeed


### MOVEMENT OF THE BALL ###
def onStep():
    """Main simulation loop.

    Responsibilities:
    - update frame delta time
    - process current input mode (singleplayer or twoplayer)
    - move paddles and ball
    - run collision and scoring logic
    - process round-end delay and restart
    """
    # Calculate delta time for this step, which can be used to make movement frame-rate independent if desired.
    now = time.perf_counter()
    app.dt = now - app.prevTime
    app.prevTime = now
    app.dt = min(app.dt, 1/60) #Clamp big frame spikes to avoid extreme ball speeds.

    # Fallback: keep layout correct even if a resize event was not delivered.
    if app.width != app.prevW or app.height != app.prevH:
        onResize()
    
    if not app.gameStart:
        # While in menu state, skip gameplay simulation entirely.
        return

    # During round-end freeze, wait then auto-reset.
    if app.roundOver:
        # Round winner has been shown; count down before relaunching.
        app.roundTimer -= app.dt
        if app.roundTimer <= 0:
            resetRound()
        return

    # Player controls by mode:
    # Singleplayer: P1 = mouse, P2 = AI.
    # Twoplayer: P1 = W/S, P2 = Up/Down.
    if app.p2IsAI:
        # Smooth P1 mouse-follow using a max movement speed.
        paddleDeltaY = app.mouseTargetY - app.p1.centerY
        maxPaddleStep = app.paddleSpeed * app.dt
        if abs(paddleDeltaY) <= maxPaddleStep:
            app.p1.centerY = app.mouseTargetY
        else:
            app.p1.centerY += maxPaddleStep if paddleDeltaY > 0 else -maxPaddleStep
    else:
        if app.wHeld:
            app.p1.centerY -= app.playerPaddleSpeed * app.dt
        if app.sHeld:
            app.p1.centerY += app.playerPaddleSpeed * app.dt
        if app.upHeld:
            app.p2.centerY -= app.playerPaddleSpeed * app.dt
        if app.downHeld:
            app.p2.centerY += app.playerPaddleSpeed * app.dt

    # Move ball each frame.
    ball.centerX += app.dx * app.dt
    ball.centerY += app.dy * app.dt

    # AI only applies in singleplayer mode.
    if app.p2IsAI:
        AI_SPEED = app.paddleSpeed  # Match AI max speed to smoothed human-follow speed.
        aiDeltaY = ball.centerY - app.p2.centerY
        aiStep = max(-AI_SPEED * app.dt, min(AI_SPEED * app.dt, aiDeltaY))
        app.p2.centerY += aiStep

    # Keep paddles inside screen bounds.
    clampPaddles()

    ### COLLISIONS ###
    # Paddle collisions: reflect horizontal direction and randomize vertical bounce.
    if ball.hitsShape(app.p1):
        app.dx = abs(app.dx)
        app.dy = random.randrange(-5, 5) * BASE_FPS * ss(1)
        ball.left = app.p1.right + 1
        counter.value += 1
        increaseSpeed()
        clampSpeed()

    if ball.hitsShape(app.p2):
        app.dx = -abs(app.dx)
        app.dy = random.randrange(-5, 5) * BASE_FPS * ss(1)
        ball.right = app.p2.left - 1
        counter.value += 1
        increaseSpeed()
        clampSpeed()

    # Top/bottom collisions: reflect vertical direction.
    if ball.hitsShape(app.border1):
        app.dy = abs(app.dy)
    if ball.hitsShape(app.border2):
        app.dy = -abs(app.dy)

    # Goal wall collisions: show winner text.
    if ball.hitsShape(app.backWall):
        endRound(False)
    elif ball.hitsShape(app.frontWall):
        endRound(True)


### DEBUG ###
# These print once at startup.
print(app.stepsPerSecond)
print(app.dx)
print(app.dy)

applyResponsiveLayout(app.width, app.height)
setMenuButtonsVisible(True)
updateMenuButtonStyles()

cmu_graphics.run()
