# Welcome to MazeWorld

MazeWorld is a simple 2d overhead RPG adventure where you play a square trying to find your way out of a fully connected maze.

Written in python3.11.9

## Layout
```
MazeWorld/
├─ main.py #This is the script which builds the exe. This generates the primatives which are used to create the map, the items, etc.
├─ config.py #Tells main how many levels, npcs, items, and which GenAI models to use
├─ requirements.txt #Contains python libraries and versions
├─ src/
│  ├─ utils/ #python classes
│  ├─ models/ #GenAI models
│  ├─ controllers/ 
│  ├─ views/
├─ data/
│  ├─ npcs/ #primatives outlining NPC definitions - these are generated upon running `python main.py` 
│  ├─ items/ #primatives outlining item definitions - these are generated upon running `python main.py`
│  ├─ events/ #primatives for event seeds, these are the starting text of events for each level - generated upon running `python main.py`
│  ├─ logs/ #.txt files outlining generation, play events, and gpu/cpu consumption as well as any warnings that occurs during play
│  ├─ saves/ #save files used for reload incase a player saves to continue their game later
└─ build/ #A demo of MazeWorld for immediate play
```

Here we see the general build of the MazeWorld builder. 

## Development Roadmap to v0.1
1. Refactor code for pre-generation llm primatives 
2. add diffusion generated graphics
3. add logs
4. add saves
5. add events
    - make sure there are 10% of the spaces covered in events
    - NPCs aware of random events nearby and will mention them
        (if random event within N steps, they say something like I think I saw something nearby...)
    - NPCS have a random event?5. add combat
6. Start/Save/Load/End screens 
7. Implement Portals to next level
8. Implement level backgrounds and themes
9. Implement mac support for llm/dm generation


## Known Bugs
- npcs have a randomly generated env, rather than reading from the env of the maze
- dialogue does not always start at the top of the text when npcs respond, it can start in the middle of the reply