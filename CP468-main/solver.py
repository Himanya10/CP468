import heapq


from puzzle import Puzzle



class Solver:
    def __init__(self, initial_puzzle, SIZEOFPUZZLE=3):
        self.nodes_explored = 0
        self.initial = initial_puzzle
        self.goal = Puzzle(SIZEOFPUZZLE)

        self.sizeofpuzzle = SIZEOFPUZZLE

        self.heuristics = {"misplaced": self.misplaced,"manhattan": self.manhattan,"goingFishing": self.goingFishing,"euclidian": self.euclidian}

    def goingFishing(self, puzzle):#Heuristic made for fun thats not really a heurisitic dont use
        #an absolutely atrocious heuristic that Should never work
        return 3

    def misplaced(self, puzzle): #returns the number of misplaced tiles, a very crude analysis hence it being very inefficient
        #Calculate the misplaced tiles heuristic.
        misplaced = 0
        for x in range(self.sizeofpuzzle):
            for y in range(self.sizeofpuzzle):
                if puzzle.board[x][y] != self.goal.board[x][y]:
                    misplaced += 1

        return misplaced

    def manhattan(self, puzzle):
        #Calculate the Manhattan distance heuristic.
        # Very efficient heuristic
        distance = 0
        for x in range(self.sizeofpuzzle):
            for y in range(self.sizeofpuzzle):
                value = puzzle.board[x][y]
                if value == 0:
                    continue
                if self.goal.board[x][y] != value:
                    x_goal, y_goal = self.goal.find(value)
                    distance += abs(x_goal - x) + abs(y_goal - y)

        return distance

    def euclidian(self, puzzle):
        #Calculate the Euclidian distance heuristic.
        # Second most efficient heuristic
        distance = 0
        for x in range(self.sizeofpuzzle):
            for y in range(self.sizeofpuzzle):
                value = puzzle.board[x][y]
                if value == 0:
                    continue
                if self.goal.board[x][y] != value:
                    x_goal, y_goal = self.goal.find(value)
                    distance += ((x_goal - x) ** 2 + (y_goal - y) ** 2) ** 0.5 # Euclidian distance formula sqrt((x2-x1)^2 + (y2-y1)^2), similar to pythagorean theorem

        return distance

    def get_neighbors(self, puzzle):
        """Generate all possible moves (children of current state)."""
        neighbors = []
        possible_moves = ["up", "down", "left", "right"] # Possible moves, there's a fifth secret move but im not telling you what it is (there isn't)

        for move in possible_moves:
            new_puzzle = Puzzle(self.sizeofpuzzle)  # Create a new puzzle state
            new_puzzle.board = [row[:] for row in puzzle.board]  # Copy the board
            if getattr(new_puzzle, move)():  # Call the move method and check if its valid
                neighbors.append((new_puzzle, move)) # Append the new state and the move made

        return neighbors


    def solve(self, heuristic="manhattan"):
        """A* algorithm to solve the puzzle."""
        priority_queue = [] # Priority queue to store the states
        heapq.heappush(priority_queue, (0, 0, self.initial, []))  # (f(n), g(n), puzzle, path)
        visited = set()
        self.nodes_explored = 0 # keep track of the number of nodes explored

        while priority_queue:
            _, g, current, path = heapq.heappop(priority_queue) # Pop the state with the lowest f(n)
            self.nodes_explored += 1
            if current == self.goal:
                return path,g  # Return the moves that lead to the goal

            state_tuple = hash(str(current.board))  # unchangeable state representation

            if state_tuple in visited:
                continue
            visited.add(state_tuple) # Add the state to the visited set

            for neighbor, move_name in self.get_neighbors(current):
                new_g = g + 1 # g(n+1) = g(n) + 1 or g(n) = g(n-1) + 1
                f = new_g + self.heuristics[heuristic](neighbor) # f(n) = g(n) + h(n)
                heapq.heappush(priority_queue, (f, new_g, neighbor, path + [move_name])) # Push the new state to the priority queue

        return None

