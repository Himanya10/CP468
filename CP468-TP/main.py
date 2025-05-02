import math
import logging
import time
import os
import re
from typing import List, Tuple, Callable, Dict
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import random

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    filename='game_log.txt',
    filemode='w'
)

# Configuration and Constants
BOARD_SIZES = [3, 4, 5]  # Supported board sizes

class TicTacToeAI:
    # Class constants
    PLAYER_X = 'X'
    PLAYER_O = 'O'
    EMPTY = ' '
    
    def __init__(self, board_size: int = 3, max_depth: int = 5):
        if board_size not in BOARD_SIZES:
            raise ValueError(f"Board size must be one of {BOARD_SIZES}")
        
        self.BOARD_SIZE = board_size
        self.MAX_DEPTH = max_depth
        self.nodes_evaluated = 0
        self.api_wait_time = 0  # Track time spent waiting for API
        
        # Secure API key handling
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            try:
                genai.configure(api_key=api_key)
            except Exception as e:
                logging.error(f"API Configuration Error: {e}")
                raise
        else:
            logging.warning("No Gemini API key found. Gemini-based moves will use random strategy.")

    def print_board(self, board: List[List[str]]) -> None:
        print(f"\n{self.BOARD_SIZE}x{self.BOARD_SIZE} Board:")
        for row in board:
            print(' | '.join(row))
            print('-' * (self.BOARD_SIZE * 4 - 1))

    def check_win(self, board: List[List[str]], player: str) -> bool:
        """Check if the specified player has won."""
        # Horizontal and vertical checks
        for i in range(self.BOARD_SIZE):
            if all(board[i][j] == player for j in range(self.BOARD_SIZE)) or \
               all(board[j][i] == player for j in range(self.BOARD_SIZE)):
                return True
        
        # Diagonal checks
        if all(board[i][i] == player for i in range(self.BOARD_SIZE)) or \
           all(board[i][self.BOARD_SIZE-1-i] == player for i in range(self.BOARD_SIZE)):
            return True
        
        return False

    def is_board_full(self, board: List[List[str]]) -> bool:
        """More efficient board full check"""
        return all(cell != self.EMPTY for row in board for cell in row)

    def minimax(self, board: List[List[str]], depth: int,
                alpha: float, beta: float, is_maximizing: bool) -> float:
        self.nodes_evaluated += 1
        
        # Terminal state checks
        if depth >= self.MAX_DEPTH:
            return 0
        
        if self.check_win(board, self.PLAYER_X):
            return 10 - depth
        if self.check_win(board, self.PLAYER_O):
            return depth - 10
        if self.is_board_full(board):
            return 0
        
        if is_maximizing:
            max_eval = float('-inf')
            for i in range(self.BOARD_SIZE):
                for j in range(self.BOARD_SIZE):
                    if board[i][j] == self.EMPTY:
                        board[i][j] = self.PLAYER_X
                        eval = self.minimax(board, depth + 1, alpha, beta, False)
                        board[i][j] = self.EMPTY
                        max_eval = max(max_eval, eval)
                        alpha = max(alpha, eval)
                        if beta <= alpha:
                            break
            return max_eval
        else:
            min_eval = float('inf')
            for i in range(self.BOARD_SIZE):
                for j in range(self.BOARD_SIZE):
                    if board[i][j] == self.EMPTY:
                        board[i][j] = self.PLAYER_O
                        eval = self.minimax(board, depth + 1, alpha, beta, True)
                        board[i][j] = self.EMPTY
                        min_eval = min(min_eval, eval)
                        beta = min(beta, eval)
                        if beta <= alpha:
                            break
            return min_eval

    def best_move(self, board: List[List[str]]) -> Tuple[int, int]:
        """Add board validation"""
        if len(board) != self.BOARD_SIZE or any(len(row) != self.BOARD_SIZE for row in board):
            raise ValueError("Invalid board dimensions")
            
        logging.info(f"Calculating best move for board size {self.BOARD_SIZE}")
        
        best_val = float('-inf')
        move = (-1, -1)
        moves_considered = 0
        
        for i in range(self.BOARD_SIZE):
            for j in range(self.BOARD_SIZE):
                if board[i][j] == self.EMPTY:
                    board[i][j] = self.PLAYER_X
                    move_val = self.minimax(board, 0, float('-inf'), float('inf'), False)
                    board[i][j] = self.EMPTY
                    
                    logging.debug(f"Move ({i},{j}) evaluated with value: {move_val}")
                    moves_considered += 1
                    
                    if move_val > best_val:
                        best_val = move_val
                        move = (i, j)
        
        logging.info(f"Total moves considered: {moves_considered}")
        
        if move == (-1, -1):
            logging.error("No valid move found!")
            return self.random_move(board)
        
        return move

    def gemini_move(self, board: List[List[str]]) -> Tuple[int, int]:
        """Gemini 2.0 Flash move generator with persistent retries"""
        if not os.getenv('GEMINI_API_KEY'):
            return self.random_move(board)

        # Configuration
        MAX_RETRIES = 3
        RETRY_DELAY = 60  # seconds
        current_delay = RETRY_DELAY

        # prompt for Gemini 2.0 Flash
        prompt = f"""Tic-Tac-Toe Move Selection (Board Size: {self.BOARD_SIZE}x{self.BOARD_SIZE})
    You are Player O. Select the best empty cell from the current board state.

    Current Board:
    {self._format_board_for_gemini(board)}

    Available Moves (row,col): {', '.join(f'({i},{j})' for i,j in self._get_empty_cells(board))}

    Respond ONLY with the coordinates in format: row,col
    Example: For top-left corner, respond: 0,0"""

        for attempt in range(MAX_RETRIES + 1):
            try:
                if attempt > 0:
                    wait_start = time.time()
                    logging.warning(f"Attempt {attempt + 1}, waiting {current_delay}s...")
                    time.sleep(current_delay)
                    self.api_wait_time += time.time() - wait_start  # Track actual wait time
                    current_delay *= 1.5  # Exponential backoff

                model = genai.GenerativeModel("gemini-1.5-flash")  # Old model for more tokens, less wait time
                response = model.generate_content(
                    prompt,
                    generation_config={
                        "max_output_tokens": 5,  # Only need "x,y"
                        "temperature": 0.1,      # Less random
                        "top_p": 0.3
                    }
                )

                # Robust parsing
                if match := re.fullmatch(r"\s*(\d+)\s*,\s*(\d+)\s*", response.text.strip()):
                    i, j = map(int, match.groups())
                    if (0 <= i < self.BOARD_SIZE and 
                        0 <= j < self.BOARD_SIZE and 
                        board[i][j] == self.EMPTY):
                        return (i, j)

                raise ValueError(f"Invalid response format: '{response.text}'")

            except Exception as e:
                if attempt == MAX_RETRIES:
                    logging.error(f"Gemini failed after {MAX_RETRIES} attempts: {str(e)[:200]}")
                    return self.random_move(board)
                elif "quota" in str(e).lower() or "rate limit" in str(e).lower():
                    continue  # Will retry
                else:
                    logging.warning(f"Gemini error (attempt {attempt + 1}): {str(e)[:200]}")
                    return self.random_move(board)

        return self.random_move(board)  # Final fallback


    def _format_board_for_gemini(self, board):
        """Formats board visually for Gemini"""
        border = "-" * (self.BOARD_SIZE * 4 + 1)
        rows = []
        for i, row in enumerate(board):
            cells = []
            for j, cell in enumerate(row):
                cells.append(f" {cell if cell != ' ' else f'({i},{j})'} ")
            rows.append("|".join(cells))
        return f"\n{border}\n" + f"\n{border}\n".join(rows) + f"\n{border}"

    def _get_empty_cells(self, board):
        """Returns list of available moves for the prompt"""
        return [(i,j) for i in range(self.BOARD_SIZE) 
                       for j in range(self.BOARD_SIZE) 
                       if board[i][j] == self.EMPTY]

    def random_move(self, board: List[List[str]]) -> Tuple[int, int]:
        """Selects a truly random empty cell"""
        empty_cells = [(i, j) for i in range(self.BOARD_SIZE)
                      for j in range(self.BOARD_SIZE) if board[i][j] == self.EMPTY]
        
        if not empty_cells:
            return (-1, -1)
        
        return random.choice(empty_cells)

    def plot_board(self, board: List[List[str]]) -> None:
        plt.figure(figsize=(8, 8))
        plt.title(f'{self.BOARD_SIZE}x{self.BOARD_SIZE} Tic-Tac-Toe', pad=20)
        plt.imshow([[0]*self.BOARD_SIZE for _ in range(self.BOARD_SIZE)], cmap='binary', alpha=0.1)
        
        for i in range(self.BOARD_SIZE):
            for j in range(self.BOARD_SIZE):
                color = 'red' if board[i][j] == self.PLAYER_X else 'blue' if board[i][j] == self.PLAYER_O else 'gray'
                plt.text(j, i, board[i][j],
                         horizontalalignment='center',
                         verticalalignment='center',
                         fontsize=20, color=color)
        
        plt.grid(color='black', linestyle='-', linewidth=2)
        plt.xticks(range(self.BOARD_SIZE))
        plt.yticks(range(self.BOARD_SIZE))
        plt.tight_layout()
        plt.savefig('game_board.png')
        plt.close()

    def play_game(self, player_x_strategy: str = 'minimax',
                 player_o_strategy: str = 'gemini') -> dict:
        """Reset counters before each game"""
        self.nodes_evaluated = 0
        self.start_time = time.time()
        self.api_wait_time = 0  # Reset API wait time
        
        self.board = [[self.EMPTY] * self.BOARD_SIZE for _ in range(self.BOARD_SIZE)]
        current_player = self.PLAYER_X
        
        game_result = {
            'winner': None,
            'result': 'Draw',
            'board_size': self.BOARD_SIZE,
            'x_strategy': player_x_strategy,
            'o_strategy': player_o_strategy,
            'duration': 0,
            'total_moves': 0,
            'nodes_evaluated': 0,
            'api_wait_time': 0  # Add API wait time to results
        }
        
        try:
            max_moves = self.BOARD_SIZE * self.BOARD_SIZE
            move_count = 0
            
            strategies = {
                'minimax': self.best_move,
                'random': self.random_move,
                'gemini': self.gemini_move
            }
            
            while move_count < max_moves:
                self.print_board(self.board)
                self.plot_board(self.board)
                
                if current_player == self.PLAYER_X:
                    move_func = strategies.get(player_x_strategy, self.best_move)
                    i, j = move_func(self.board)
                    self.board[i][j] = self.PLAYER_X
                    logging.info(f"Player X ({player_x_strategy}) chooses ({i+1}, {j+1})")
                else:
                    move_func = strategies.get(player_o_strategy, self.gemini_move)
                    i, j = move_func(self.board)
                    self.board[i][j] = self.PLAYER_O
                    logging.info(f"Player O ({player_o_strategy}) chooses ({i+1}, {j+1})")
                
                move_count += 1
                
                if self.check_win(self.board, self.PLAYER_X):
                    game_result.update({
                        'winner': 'X',
                        'result': 'X Wins',
                        'total_moves': move_count
                    })
                    break
                elif self.check_win(self.board, self.PLAYER_O):
                    game_result.update({
                        'winner': 'O',
                        'result': 'O Wins',
                        'total_moves': move_count
                    })
                    break
                elif self.is_board_full(self.board):
                    game_result['total_moves'] = move_count
                    break
                
                current_player = self.PLAYER_O if current_player == self.PLAYER_X else self.PLAYER_X
            
            game_result['duration'] = time.time() - self.start_time
            game_result['nodes_evaluated'] = self.nodes_evaluated
            game_result['api_wait_time'] = self.api_wait_time  # Record wait time
            
            self.print_board(self.board)
            logging.info(f"Game result: {game_result['result']}")
            
        except Exception as e:
            logging.error(f"Game error: {e}")
            game_result['result'] = 'Error'
        
        return game_result


class PerformanceAnalyzer:
    def __init__(self, game_results: List[Dict]):
        """
        Initialize performance analyzer with game results
        
        Args:
            game_results (List[Dict]): List of game result dictionaries
        """
        self.results_df = pd.DataFrame(game_results)
        self.results_df['game_id'] = range(1, len(self.results_df) + 1)

    def generate_comprehensive_report(self, output_file='performance_report.pdf'):
        """Generate PDF report with proper figure handling"""
        with PdfPages(output_file) as pdf:
            # Strategy Performance
            fig1 = self._plot_strategy_performance()
            pdf.savefig(fig1, bbox_inches='tight')
            plt.close(fig1)
            
            # Execution Times
            fig2 = self._plot_execution_times()
            pdf.savefig(fig2, bbox_inches='tight')
            plt.close(fig2)
            
            # Outcome Distribution
            fig3 = self._plot_outcome_distribution()
            pdf.savefig(fig3, bbox_inches='tight')
            plt.close(fig3)
            
            # API Wait Times
            fig4 = self._plot_api_wait_times()
            pdf.savefig(fig4, bbox_inches='tight')
            plt.close(fig4)

    def _plot_strategy_performance(self):
        possible_outcomes = ['X Wins', 'O Wins', 'Draw']
        strategy_results = self.results_df.groupby(['x_strategy', 'o_strategy'])['result'] \
            .value_counts(normalize=True).unstack()
        
        for outcome in possible_outcomes:
            if outcome not in strategy_results.columns:
                strategy_results[outcome] = 0
                
        strategy_results = strategy_results[possible_outcomes] * 100
        
        ax = strategy_results.plot(kind='bar', stacked=True, figsize=(12, 8),
                                 color=['#2ca02c', '#d62728', '#7f7f7f'])
        
        plt.title('Strategy Performance Across Game Outcomes', pad=20, fontsize=14)
        plt.xlabel('Strategy Combinations (X vs O)', labelpad=10)
        plt.ylabel('Outcome Percentage (%)', labelpad=10)
        plt.xticks(rotation=45, ha='right')
        
        for container in ax.containers:
            ax.bar_label(container, fmt='%.1f%%', label_type='center', padding=2)
        
        plt.legend(title='Result', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        return plt.gcf()

    def _plot_execution_times(self):
        plt.figure(figsize=(12, 8))
        
        # Calculate pure processing time (excluding API waits)
        self.results_df['pure_processing_time'] = self.results_df['duration'] - self.results_df['api_wait_time']
        
        # Create the boxplot using only pure processing time
        ax = sns.boxplot(
            x='board_size', 
            y='pure_processing_time', 
            hue='x_strategy',
            data=self.results_df,
            palette='Set2',
            width=0.6,
            showfliers=False
        )
        
        plt.title('Game Processing Time (Excluding API Waits)', pad=20, fontsize=14)
        plt.xlabel('Board Size', labelpad=10)
        plt.ylabel('Processing Time (seconds)', labelpad=10)
        
        # Add median values to the plot
        medians = self.results_df.groupby(['board_size', 'x_strategy'])['pure_processing_time'].median()
        for i, (x, y) in enumerate(medians.items()):
            ax.text(i, y, f'{y:.2f}s', ha='center', va='bottom', fontsize=10)
        
        plt.legend(title='X Strategy', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        return plt.gcf()

    def _plot_outcome_distribution(self):
        plt.figure(figsize=(12, 8))
        
        # Get all possible outcomes we want to show
        outcomes = ['X Wins', 'Draw']
        
        # Initialize a DataFrame to ensure all combinations exist
        all_combinations = pd.MultiIndex.from_product(
            [self.results_df['board_size'].unique(), outcomes],
            names=['board_size', 'result']
        )
        
        # Count occurrences of each outcome per board size
        outcome_counts = (
            self.results_df[self.results_df['result'].isin(outcomes)]
            .groupby(['board_size', 'result'])
            .size()
            .reindex(all_combinations, fill_value=0)
            .unstack()
        )
        
        # Convert board_size to string for categorical plotting
        outcome_counts.index = outcome_counts.index.astype(str)
        
        # Set up the positions for the bars
        bar_width = 0.35
        positions = np.arange(len(outcome_counts))
        
        # Create bars for each outcome
        bars = []
        for i, outcome in enumerate(outcomes):
            color = '#2ca02c' if outcome == 'X Wins' else '#7f7f7f'
            bars.append(plt.bar(
                positions + (i - 0.5) * bar_width,
                outcome_counts[outcome],
                width=bar_width,
                label=outcome,
                color=color
            ))
        
        plt.title('Game Outcomes by Board Size', pad=20, fontsize=14)
        plt.xlabel('Board Size', labelpad=10)
        plt.ylabel('Number of Games', labelpad=10)
        plt.xticks(positions, [f'{size}x{size}' for size in outcome_counts.index])
        
        # Add value labels only if height > 0
        for outcome_bars in bars:
            for bar in outcome_bars:
                height = bar.get_height()
                if height > 0:
                    plt.text(
                        bar.get_x() + bar.get_width()/2.,
                        height,
                        f'{int(height)}',
                        ha='center',
                        va='bottom'
                    )
        
        plt.legend(title='Outcome', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        return plt.gcf()

    def _plot_api_wait_times(self):
        """Plot the time spent waiting for API rate limits"""
        plt.figure(figsize=(12, 8))
        
        # Filter only games that used Gemini
        gemini_games = self.results_df[
            (self.results_df['x_strategy'] == 'gemini') | 
            (self.results_df['o_strategy'] == 'gemini')
        ]
        
        if not gemini_games.empty:
            ax = sns.barplot(
                x='board_size', 
                y='api_wait_time', 
                hue='o_strategy',
                data=gemini_games,
                estimator=sum,
                ci=None,
                palette='Set2'
            )
            
            plt.title('Total API Wait Time Due to Rate Limiting', pad=20, fontsize=14)
            plt.xlabel('Board Size', labelpad=10)
            plt.ylabel('Total Wait Time (seconds)', labelpad=10)
            
            # Add value labels
            for p in ax.patches:
                ax.annotate(f"{p.get_height():.1f}s", 
                           (p.get_x() + p.get_width() / 2., p.get_height()),
                           ha='center', va='center', 
                           xytext=(0, 10), 
                           textcoords='offset points')
            
            plt.legend(title='O Strategy', bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            plt.tight_layout()
        else:
            plt.text(0.5, 0.5, 'No Gemini API games in this dataset',
                   ha='center', va='center', fontsize=12)
            plt.title('API Wait Times (No Gemini Games)', pad=20, fontsize=14)
        
        return plt.gcf()

    def generate_statistical_summary(self):
        summary = "Performance Analysis Summary\n"
        summary += "=" * 40 + "\n\n"
        
        # Game outcomes
        outcome_counts = self.results_df['result'].value_counts()
        possible_outcomes = ['X Wins', 'O Wins', 'Draw', 'Error']
        for outcome in possible_outcomes:
            if outcome not in outcome_counts:
                outcome_counts[outcome] = 0
        summary += "Game Outcomes:\n" + outcome_counts.to_string() + "\n\n"
        
        # Strategy Performance
        summary += "Strategy Performance:\n"
        strategy_performance = self.results_df.groupby(['x_strategy', 'o_strategy'])['result'] \
            .value_counts().unstack(fill_value=0)
        for outcome in possible_outcomes:
            if outcome not in strategy_performance.columns:
                strategy_performance[outcome] = 0
        summary += strategy_performance[possible_outcomes].to_string() + "\n\n"
        
        # Execution Time Statistics
        summary += "Execution Time Statistics (seconds):\n"
        time_stats = self.results_df.groupby(['board_size', 'x_strategy'])['duration'] \
            .agg(['mean', 'median', 'std', 'min', 'max'])
        summary += time_stats.to_string() + "\n\n"
        
        # Nodes Evaluated Statistics
        summary += "Nodes Evaluated Statistics:\n"
        nodes_stats = self.results_df.groupby(['board_size', 'x_strategy'])['nodes_evaluated'] \
            .agg(['mean', 'median', 'std', 'min', 'max'])
        summary += nodes_stats.to_string() + "\n\n"
        
        # API Wait Time Statistics
        summary += "API Wait Time Statistics (seconds):\n"
        wait_stats = self.results_df.groupby(['board_size', 'o_strategy'])['api_wait_time'] \
            .agg(['sum', 'mean', 'max'])
        summary += wait_stats.to_string() + "\n\n"
        
        # Win Rates
        summary += "Win Rates:\n"
        win_rates = pd.crosstab(index=[self.results_df['x_strategy'], self.results_df['o_strategy']],
                               columns=self.results_df['result'], normalize='index') * 100
        for outcome in possible_outcomes:
            if outcome not in win_rates.columns:
                win_rates[outcome] = 0.0
        summary += win_rates[possible_outcomes].round(1).to_string() + "\n"
        
        return summary


def main():
    strategies = [
        ('minimax', 'random'),
        ('minimax', 'gemini')
    ]
    
    games_per_config = 10  # Run 10 games per configuration
    all_results = []
    
    for board_size in BOARD_SIZES:
        for x_strategy, o_strategy in strategies:
            print(f"\n--- Running {games_per_config} {board_size}x{board_size} Games: X={x_strategy}, O={o_strategy} ---")
            
            for game_num in range(1, games_per_config + 1):
                try:
                    game = TicTacToeAI(board_size)
                    game_result = game.play_game(
                        player_x_strategy=x_strategy,
                        player_o_strategy=o_strategy
                    )
                    game_result['game_num'] = game_num
                    all_results.append(game_result)
                    print(f"Game {game_num}: {game_result['result']}")
                except Exception as e:
                    logging.error(f"Game failed for {board_size}x{board_size}: {e}")
                    all_results.append({
                        'result': 'Error',
                        'board_size': board_size,
                        'x_strategy': x_strategy,
                        'o_strategy': o_strategy,
                        'error': str(e)[:200]
                    })
    
    # Performance Analysis
    analyzer = PerformanceAnalyzer(all_results)
    analyzer.generate_comprehensive_report()
    
    with open('performance_summary.txt', 'w') as f:
        f.write(analyzer.generate_statistical_summary())
    
    print("\n--- Final Results Summary ---")
    print(f"Total games played: {len(all_results)}")
    print("Outcome counts:")
    print(pd.DataFrame(all_results)['result'].value_counts().to_string())


if __name__ == "__main__":
    main()
