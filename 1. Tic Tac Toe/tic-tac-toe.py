from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional

"""Tic Tac Toe Game Implementation
This module implements a simple Tic Tac Toe game with a command-line interface.
It includes classes for the game board, players, and the game logic.
"""

class Symbol(Enum):
    X = 'X'
    O = 'O'
    EMPTY = ' '
    
    def __str__(self):
        return self.value

class Player(ABC):
    def __init__(self, symbol: Symbol):
        self.symbol = symbol

    @abstractmethod
    def make_move(self, board: 'Board') -> None:
        pass

class HumanPlayer(Player):
    def make_move(self, board: 'Board') -> None:
        while True:
            try:
                row = int(input(f"Player {self.symbol}, enter row (0-{board.side_length - 1}): "))
                col = int(input(f"Player {self.symbol}, enter col (0-{board.side_length - 1}): "))
                if board.is_valid_move(row, col):
                    board.place_symbol(row, col, self.symbol)
                    break
                else:
                    print("Invalid move. Try again.")
            except ValueError:
                print(f"Invalid input. Enter numbers 0-{board.side_length - 1}.")

class Board:
    def __init__(self, side_length: int = 3):
        if side_length < 3:
            raise ValueError("Board side length must be at least 3")
        self.side_length = side_length
        self.grid = [[Symbol.EMPTY for _ in range(side_length)] for _ in range(side_length)]

    def display(self) -> None:
        for i, row in enumerate(self.grid):
            print('|'.join(str(cell) for cell in row))
            if i < self.side_length - 1:  # Don't print separator after last row
                print('-' * (2 * self.side_length - 1))
        print()  # Add blank line for better readability

    def is_valid_move(self, row: int, col: int) -> bool:
        return (0 <= row < self.side_length and 
                0 <= col < self.side_length and 
                self.grid[row][col] == Symbol.EMPTY)

    def place_symbol(self, row: int, col: int, symbol: Symbol) -> None:
        if not self.is_valid_move(row, col):
            raise ValueError(f"Invalid move at position ({row}, {col})")
        self.grid[row][col] = symbol

    def check_winner(self, symbol: Symbol) -> bool:
        # Check rows
        for i in range(self.side_length):
            if all(self.grid[i][j] == symbol for j in range(self.side_length)):
                return True
        
        # Check columns
        for j in range(self.side_length):
            if all(self.grid[i][j] == symbol for i in range(self.side_length)):
                return True
        
        # Check main diagonal
        if all(self.grid[i][i] == symbol for i in range(self.side_length)):
            return True
        
        # Check anti-diagonal
        if all(self.grid[i][self.side_length - 1 - i] == symbol for i in range(self.side_length)):
            return True
        
        return False

    def is_full(self) -> bool:
        return all(self.grid[i][j] != Symbol.EMPTY 
                  for i in range(self.side_length) 
                  for j in range(self.side_length))

    def get_winner(self) -> Optional[Symbol]:
        """Check if there's a winner and return the winning symbol."""
        for symbol in [Symbol.X, Symbol.O]:
            if self.check_winner(symbol):
                return symbol
        return None

class Game:
    def __init__(self, player1: Player, player2: Player, board_size: int = 3):
        if player1.symbol == player2.symbol:
            raise ValueError("Players must have different symbols")
        self.board = Board(board_size)
        self.players = [player1, player2]
        self.current_player_idx = 0

    def get_current_player(self) -> Player:
        return self.players[self.current_player_idx]

    def switch_player(self) -> None:
        self.current_player_idx = 1 - self.current_player_idx

    def play(self) -> None:
        print(f"Welcome to Tic Tac Toe! Board size: {self.board.side_length}x{self.board.side_length}")
        print("Players take turns. Enter row and column coordinates (0-indexed).\n")
        
        while True:
            self.board.display()
            current_player = self.get_current_player()
            
            try:
                current_player.make_move(self.board)
            except ValueError as e:
                print(f"Error: {e}")
                continue
            
            winner = self.board.get_winner()
            if winner:
                self.board.display()
                print(f"🎉 Player {winner} wins!")
                break
                
            if self.board.is_full():
                self.board.display()
                print("🤝 It's a draw!")
                break
                
            self.switch_player()

# Factory pattern for player creation
class PlayerFactory:
    @staticmethod
    def create_human_player(symbol: Symbol) -> HumanPlayer:
        return HumanPlayer(symbol)

if __name__ == "__main__":
    try:
        player1 = PlayerFactory.create_human_player(Symbol.X)
        player2 = PlayerFactory.create_human_player(Symbol.O)
        game = Game(player1, player2)
        game.play()
    except ValueError as e:
        print(f"Error initializing game: {e}")
    except KeyboardInterrupt:
        print("\nGame interrupted. Thanks for playing!")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")