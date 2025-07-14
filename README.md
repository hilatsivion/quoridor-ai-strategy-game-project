# 🎮 Quoridor AI – Strategic Game with Classic AI

This project implements an advanced AI opponent for the strategy game **Quoridor**, using classical search algorithms (not deep learning). The player competes against an AI that uses the **Minimax algorithm with Alpha-Beta Pruning** to determine its optimal moves.

The project was developed as part of the final assignment in the course  
**"Advanced Algorithms for Planning and Scheduling Intelligent Systems"**.

---

## 🧠 What Makes Our Game Unique?

Beyond the standard Quoridor mechanics, we've added:
- **Power Bomb (🧨)** – a strategic special move that destroys surrounding walls
- **Dynamic difficulty** – board size changes based on difficulty level
- **AI Opponent** – thinks multiple steps ahead and adapts to changes in the game
- **Loop detection & caching** – for efficient and smart decision-making

---

## ⚙️ Algorithms Used

- **Minimax with Alpha-Beta Pruning** – to evaluate the best possible move from the current state
- **Custom Evaluation Function** – considers shortest path to goal, player progress, penalties for looping, and distance from opponent
- **Memoization (caching)** – stores previously evaluated board states to avoid redundant calculations
- **Loop Detection** – prevents repetitive moves that lead to game stagnation

---

## 🖥️ Technologies Used

- **Language**: Python 3.x  
- **Graphics & UI**: [Pygame](https://www.pygame.org/) (version 1.9.6)

---

## 🚀 How to Run

1. Clone the repository  
2. Make sure you have Python 3.x and Pygame installed  
3. Run the game with:

```bash
python quoridor.py -l [LEVEL]
```

- The `LEVEL` is optional and determines AI difficulty (higher = smarter but slower).
- Default is level 0 if not specified.

---

## 🎮 Controls

- 🖱 **Mouse**: Click to move the player or place walls  
- ⎵ **SPACEBAR**: Activate power bomb (if available)  
- ⎋ **ESC**: Exit the game

---

## 💥 Special Feature: Power Bomb

Each player has **one Power Bomb** per game:

- **Effect**: Destroys all walls in a 3x3 area around the player
- **Walls Return**: Destroyed walls are returned to their original owners
- **Can Move Through**: Temporarily allows movement through those walls on the same turn
- **Strategic Use**: Ideal for escaping traps or reclaiming wall inventory

---

## 📎 Project Links

🎥 Presentation & Game Demo Videos
**Google Drive Folder (Both videos):**
https://drive.google.com/drive/folders/1h3rZ3PVH0aXc0yB0Sw9qHhV9-MFXLwyW?usp=sharing

**YouTube – Project Presentation:**
https://youtu.be/z-LJ28UVD9Y

**YouTube – Game Demo:**
https://youtu.be/R8Zjumhq8HQ

**🖼️ Presentation Slide Deck**
https://www.canva.com/design/DAGsHLvYAU4/mR-bhfZ2lCyryQAUUXdXHQ/view?utm_content=DAGsHLvYAU4&utm_campaign=designshare&utm_medium=link2&utm_source=uniquelinks&utlId=h6a7fb68f7c

---


## 📜 License

This project is licensed under the [GPLv3 License](https://www.gnu.org/licenses/gpl-3.0.en.html).
