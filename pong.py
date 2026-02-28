from cmu_graphics import *
import random
import time

### Pong ###
### DESCRIPTION ###
### Use W/S or mouse for player one, and Arrow Up and Arrow Down for player two.
### When useing singleplayer mode, player two will be controlled by a simple AI that tracks the ball's Y position.
### Also when in singleplayermode the paddle can be controlled by the mouse.
### Press 9 for singleplayer (P2 AI) or 0 for twoplayer (P2 human).
### The ball will speed up every 10 points.
###

## TO DO ##
# Add GUI for color and mode selectors


### APP VARIABLES ###
# Global app setup.
app.background = 'white'
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
ball = Circle(1280, 720, 32, fill="white", visible=False)
app.p1 = Rect(160, 576, 16, 256, fill=None, visible=False)
app.p2 = Rect(2400, 576, 16, 256, fill=None, visible=False)
app.border1 = Rect(0, -30, 2560, 40, fill='black', visible=False) # Top border (also used for ball bounce collision).
app.border2 = Rect(0, 1430, 2560, 40, visible=False) # Bottom border (also used for ball bounce collision).
app.backWall = Rect(0, 0, 10, 1440, visible=False)      # Left goal wall.
app.frontWall = Rect(2550, 0, 40, 1440, visible=False)  # Right goal wall.

# UI labels for round outcome and score.
loseMsg = Label("P2 Win!", 200, 200, size=75, visible=False, fill='green')
winMsg = Label("P1 Win!", 200, 200, size=75, visible=False, fill='green')
counter = Label(0, 1280, 30, size=30, visible=False)

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
app.paddleSpeed = 30 * BASE_FPS  # Max follow speed for smoothed mouse control (pixels/second).
app.playerPaddleSpeed = 10 * BASE_FPS  # Human paddle speed (pixels/second).
app.p2IsAI = True  # True: singleplayer (P2 AI), False: twoplayer (P2 human).
app.roundOver = False
app.roundTimer = 0
app.roundDelay = 1.5  # How long winner text stays visible.

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


### GUI LEVEL SELECT ###
# Start/menu labels. Hidden when game starts.
menuTitle = Label("PONG", 1280, 288, size=256, fill="black")
colorText = Label("Press 1-3 to Select Color Scheme", 1280, 468, fill='black', size=76)
levelText = Label("Press 5-8 to Select Difficulty", 1280, 576, fill='black', size=76)
modeText = Label("Press 9 for Singleplayer, 0 for Twoplayer", 1280, 670, fill='black', size=76)
startText = Label("Press Enter to Start", 1280, 1200, fill="black", size=76)
shcemeShow = Label('1 is SkyBlue and Salmon, 2 is Lime and Orange, 3 is White and Black', 1280, 850, fill='Black', size=76)
diffShow = Label('5 is Easy, 6 is Medium, 7 is Hard, 8 is Infinite Speed Scaling',1280, 946, fill='Black', size=76)
modeShow = Label('Mode: Singleplayer', 1280, 1048, fill='Black', size=76)


### START SCRIPT ###
def start(color1, color2, levelSelect):
    # Show gameplay objects.
    ball.visible = True
    app.p1.visible = True
    app.p1.fill = color1
    app.p2.visible = True
    app.p2.fill = color2
    app.border1.visible = True
    app.border2.visible = True
    app.backWall.visible = True
    app.frontWall.visible = True
    counter.visible = True

    # Reset ball and launch with random horizontal direction.
    ball.centerX = 1280
    ball.centerY = 720
    app.dx = random.choice([-9, 9]) * BASE_FPS  # Start left or right.
    app.dy = random.randrange(-2, 3) * BASE_FPS
    app.maxSpeed = levelSelect * BASE_FPS
    app.roundOver = False
    app.roundTimer = 0
    loseMsg.visible = False
    winMsg.visible = False

    # Hide menu UI during match.
    menuTitle.visible = False
    colorText.visible = False
    levelText.visible = False
    modeText.visible = False
    startText.visible = False
    shcemeShow.visible = False
    diffShow.visible = False
    modeShow.visible = False
    app.background = "darkGray"

def endRound(p1Won):
    # Freeze game motion and display round winner.
    app.roundOver = True
    app.roundTimer = app.roundDelay
    app.dx = 0
    app.dy = 0
    winMsg.visible = p1Won
    loseMsg.visible = (not p1Won)

def resetRound():
    # Hide winner text and relaunch from center for next point.
    winMsg.visible = False
    loseMsg.visible = False
    app.roundOver = False
    app.roundTimer = 0
    ball.centerX = 1280
    ball.centerY = 720
    app.p1.centerY = 720
    app.p2.centerY = 720
    app.mouseTargetY = app.p1.centerY
    app.dx = random.choice([-9, 9]) * BASE_FPS  # Start left or right.
    app.dy = random.randrange(-2, 3) * BASE_FPS


### MOVEMENT OF THE PADDLES ###
def onMouseMove(mouseX, mouseY):
    # Save raw mouse values if needed for debugging.
    app.mouseX = mouseX
    app.mouseY = mouseY

    # Move target only. Actual paddle motion is smoothed in onStep.
    app.mouseTargetY = mouseY


### KEY PRESS FUNCTIONS ###
def onKeyPress(key):
    # In menu: choose color/difficulty and start game.
    if not app.gameStart:
        if key in ['1', '2', '3']:
            app.selectedColor = int(key)
        if key in ['5', '6', '7', '8']:
            app.selectedLevel = int(key)
        if key == '9':
            app.p2IsAI = True
            modeShow.value = 'Mode: Singleplayer'
        if key == '0':
            app.p2IsAI = False
            modeShow.value = 'Mode: Twoplayer'
        if key == 'enter':
            colors = colorOptions[app.selectedColor]
            levelSpeed = levelOptions[app.selectedLevel]
            start(colors[0], colors[1], levelSpeed)
            app.gameStart = True

    # In game: set key-held flags for continuous movement.
    else:
        if key == 'r':
            # Reset game state and return to menu.
            app.gameStart = False
            counter.value = 0
            app.speedTier = 0
            app.dx = 0
            app.dy = 0
            app.background = 'white'
            ball.visible = False
            app.p1.visible = False
            app.p2.visible = False
            app.border1.visible = False
            app.border2.visible = False
            app.backWall.visible = False
            app.frontWall.visible = False
            winMsg.visible = False
            loseMsg.visible = False

            # Show menu UI.
            menuTitle.visible = True
            colorText.visible = True
            levelText.visible = True
            modeText.visible = True
            startText.visible = True
            shcemeShow.visible = True
            diffShow.visible = True
            modeShow.visible = True
        if key == 'up':
            app.upHeld = True
        if key == 'down':
            app.downHeld = True
        if key == 'w':
            app.wHeld = True
        if key == 's':
            app.sHeld = True


def onKeyRelease(key):
    # Clear key-held flags on release.
    if key == 'up':
        app.upHeld = False
    if key == 'down':
        app.downHeld = False
    if key == 'w':
        app.wHeld = False
    if key == 's':
        app.sHeld = False


### INCREASE SPEED EVERY 10 SCORE ###
def increaseSpeed():
    # Every 10 points, increase speed tier once.
    newTier = counter.value // 10  # 0, 1, 2, 3...
    if newTier > app.speedTier:
        app.speedTier = newTier

        # Increase speed while preserving direction.
        if app.dx > 0:
            app.dx += BASE_FPS
        else:
            app.dx -= BASE_FPS

        if app.dy > 0:
            app.dy += BASE_FPS
        else:
            app.dy -= BASE_FPS


# Keep speed from increasing beyond selected level max.
def clampSpeed():
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
    # Calculate delta time for this step, which can be used to make movement frame-rate independent if desired.
    now = time.perf_counter()
    app.dt = now - app.prevTime
    app.prevTime = now
    app.dt = min(app.dt, 1/60) #Clamp big frame spikes to avoid extreme ball speeds.
    
    if not app.gameStart:
        return

    # During round-end freeze, wait then auto-reset.
    if app.roundOver:
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
        AI_SPEED = app.paddleSpeed  # AI paddle speed (pixels/second).
        aiDeltaY = ball.centerY - app.p2.centerY
        aiStep = max(-AI_SPEED * app.dt, min(AI_SPEED * app.dt, aiDeltaY))
        app.p2.centerY += aiStep

    # Keep paddles inside screen bounds.
    app.p1.centerY = max(138, min(1262, app.p1.centerY))
    app.p2.centerY = max(138, min(1262, app.p2.centerY))

    ### COLLISIONS ###
    # Paddle collisions: reflect horizontal direction and randomize vertical bounce.
    if ball.hitsShape(app.p1):
        app.dx = abs(app.dx)
        app.dy = random.randrange(-5, 5) * BASE_FPS
        ball.left = app.p1.right + 1
        counter.value += 1
        increaseSpeed()
        clampSpeed()

    if ball.hitsShape(app.p2):
        app.dx = -abs(app.dx)
        app.dy = random.randrange(-5, 5) * BASE_FPS
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

cmu_graphics.run()