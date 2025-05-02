# To run :

## For both
in terminal run `py .\main.py`
### On Windows:

Ensure the code is up to date using ```git pull origin main``` and then run `windows.bat`

### On Mac/Unix based:
Ensure the code is up to date using ```git pull origin main``` and then run `unix.sh`
# Settings:

number_of_puzzles, the number of puzzles to be randomly generated, will be doubled half for 3x3 half for 4x4

max_threads, the maximum of concurrent number of puzzles being solved, lower if system resources are limited / strained

randomize, the number of random moves to perform on the puzzle, i.e. how shuffled is it


# Information :

Randomly generates 200 puzzles, 100 8 size, and 100 15 size. (Configurable).

Uses A* path finding algorithim with 3 different heuristics, so technically 600 puzzles will be solved. Each heuristic will be summarized at the end of execuation, a sample output with randomize = 75 can be found below:
```
Average number of Nodes Explored for manhattan For 3x3: 289.58
Average number of Nodes Explored for manhattan For 4x4: 1253.42
Average number of Nodes Explored for misplaced For 3x3: 2152.48
Average number of Nodes Explored for misplaced For 4x4: 95276.43
Average number of Nodes Explored for euclidian For 3x3: 371.41
Average number of Nodes Explored for euclidian For 4x4: 2366.6
```

As you can see, manhattan was most effective for both 3x3 and 4x4 sized puzzles, followed by euclidian, and misplaced performing so much worse in comparision to the other two. With the 3x3 being less effective than 4x4 manhattan. 
There is also an option to disable misplaced due to its ineffeciency. See `no_misplaced` in `main.py`

An alternative heuristic should have replaced misplaced, although it still works just a little slowly

Note: a higher randomize value, will usually mean a higher time to solve, and more ram used, recommeneded a lower number of threads for higher randomize values.

Note: used [this](https://theory.stanford.edu/~amitp/GameProgramming/Heuristics.html) resource, as well as course textbook
