import multiprocessing
from puzzle import Puzzle
from solver import Solver


FUNNYONE = False # Change to true to see the terrible 1 work (or not)
lite = False #only uses one heuristic, for testing purposes

no_misplaced =False #misplaced is not really effective, put true to make it much faster

number_of_puzzles = 100 # Number of puzzles to solve *2, 3x3 and 4x4
max_threads = 50 # Number of threads to use, if > number of puzzles, will use number of puzzles

"Uses a lot of memory, if limited lower number of randomizie or threads <3"

randomize = 50 # Number of random moves to make on the puzzle before solving
# more random moves = harder puzzle, = more ram, = bad idea
def solve_puzzle(index,lock,results,size,stats):
    #Function to solve a puzzle and store results in a shared dictionary between threads.
    puzzle = Puzzle(size)
    puzzle.randomize(randomize)
    solver = Solver(puzzle,size)

    output = f"puzzle {index + 1}\n{puzzle}"

    if lite:
        heuristics = ['manhattan']
    elif FUNNYONE:
        heuristics = ['manhattan', 'misplaced','euclidian', 'goingFishing']
    elif no_misplaced:
        heuristics = ['manhattan','euclidian']
    else:
        heuristics = ['manhattan', 'misplaced','euclidian']

    for heuristic in heuristics:
        solution, moves = solver.solve(heuristic)
        if solution:
            output += f"\nHeuristic:{heuristic}, Path Length: {moves}, Number of nodes explored: {solver.nodes_explored}"
            #keeps track of stats per heuristic
            if size == 4:
                if heuristic+' For 4x4' in stats:
                    with lock:
                        stats[heuristic+' For 4x4'] += solver.nodes_explored
                else:
                    with lock:
                        stats[heuristic+' For 4x4'] = solver.nodes_explored
            else:
                if heuristic+' For 3x3' in stats:
                    with lock:
                        stats[heuristic+' For 3x3'] += solver.nodes_explored
                else:
                    with lock:
                        stats[heuristic+' For 3x3'] = solver.nodes_explored
    with lock:
        results[index] = output

if __name__ == '__main__':
    puzzles = []
    print("This will take some time, please wait")
    print("-----------------------------------------")

    results = multiprocessing.Manager().dict()
    threads = []



    lock = multiprocessing.Lock()
    stats = multiprocessing.Manager().dict({ #normal dictionary does not work with multiprocessing :fire:
        'manhattan For 3x3': 0,
        'misplaced For 3x3': 0,
        'euclidian For 3x3': 0,
        'manhattan For 4x4': 0,
        'misplaced For 4x4': 0,
        'euclidian For 4x4': 0




    })
    x = 0
    for size in range(0,2): # 1 for 3x3 and 1 for 4x4
        for i in range(number_of_puzzles):
                while len(threads) >= max_threads: #limits numbers of threads
                    for thread in threads:
                        if not thread.is_alive():
                            thread.join()
                            threads.remove(thread)
                            x += 1
                            print(f"Thread finished {x/number_of_puzzles*50:.2f}%")
                            if (x/number_of_puzzles*50) == 74:
                                print('Usually slows down around here, its still working!')
                thread = multiprocessing.Process(target=solve_puzzle, args=(i +(number_of_puzzles*size), lock, results,size+3,stats))
                threads.append(thread)
                thread.start()
    for thread in threads:
        thread.join()
        x += 1
        print(f"Thread finished {x / number_of_puzzles * 50:.2f}%")

    for i in range(number_of_puzzles*2):
        if i in results:
            print(results[i])
            print("\n-----------------------------------------")
    for i in range(number_of_puzzles * 2):
        if i not in results:
            print(f"puzzle {i+1} failed to solve")



    for key in stats:
        print(f"Average number of Nodes Explored for {key}: {stats[key] / number_of_puzzles}")