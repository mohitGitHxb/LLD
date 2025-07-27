/**
 * Tic Tac Toe Game Implementation in TypeScript
 * This module implements a simple Tic Tac Toe game with a command-line interface.
 * It includes classes for the game board, players, and the game logic.
 */

enum Symbol {
  X = "X",
  O = "O",
  EMPTY = " ",
}

abstract class Player {
  protected symbol: Symbol;

  constructor(symbol: Symbol) {
    this.symbol = symbol;
  }

  getSymbol(): Symbol {
    return this.symbol;
  }

  abstract makeMove(board: Board): Promise<void>;
}

class HumanPlayer extends Player {
  private readline: any;

  constructor(symbol: Symbol) {
    super(symbol);
    // In a real Node.js environment, you would import readline
    // const readline = require('readline');
    // For this example, we'll simulate user input
  }

  async makeMove(board: Board): Promise<void> {
    while (true) {
      try {
        // In a real implementation, you would use readline to get user input
        // For demonstration, we'll simulate random valid moves
        const availableMoves = this.getAvailableMoves(board);
        if (availableMoves.length === 0) {
          throw new Error("No available moves");
        }

        // Simulate user input (in real implementation, use readline)
        const randomMove =
          availableMoves[Math.floor(Math.random() * availableMoves.length)];
        const row = randomMove.row;
        const col = randomMove.col;

        console.log(`Player ${this.symbol} plays at (${row}, ${col})`);

        if (board.isValidMove(row, col)) {
          board.placeSymbol(row, col, this.symbol);
          break;
        } else {
          console.log("Invalid move. Try again.");
        }
      } catch (error) {
        console.log("Invalid input. Enter valid coordinates.");
      }
    }
  }

  private getAvailableMoves(board: Board): Array<{ row: number; col: number }> {
    const moves: Array<{ row: number; col: number }> = [];
    for (let i = 0; i < board.getSideLength(); i++) {
      for (let j = 0; j < board.getSideLength(); j++) {
        if (board.isValidMove(i, j)) {
          moves.push({ row: i, col: j });
        }
      }
    }
    return moves;
  }
}

class Board {
  private grid: Symbol[][];
  private sideLength: number;

  constructor(sideLength: number = 3) {
    if (sideLength < 3) {
      throw new Error("Board side length must be at least 3");
    }
    this.sideLength = sideLength;
    this.grid = Array(sideLength)
      .fill(null)
      .map(() => Array(sideLength).fill(Symbol.EMPTY));
  }

  getSideLength(): number {
    return this.sideLength;
  }

  display(): void {
    for (let i = 0; i < this.grid.length; i++) {
      console.log(this.grid[i].join("|"));
      if (i < this.sideLength - 1) {
        console.log("-".repeat(2 * this.sideLength - 1));
      }
    }
    console.log(); // Add blank line for better readability
  }

  isValidMove(row: number, col: number): boolean {
    return (
      row >= 0 &&
      row < this.sideLength &&
      col >= 0 &&
      col < this.sideLength &&
      this.grid[row][col] === Symbol.EMPTY
    );
  }

  placeSymbol(row: number, col: number, symbol: Symbol): void {
    if (!this.isValidMove(row, col)) {
      throw new Error(`Invalid move at position (${row}, ${col})`);
    }
    this.grid[row][col] = symbol;
  }

  checkWinner(symbol: Symbol): boolean {
    // Check rows
    for (let i = 0; i < this.sideLength; i++) {
      if (this.grid[i].every((cell) => cell === symbol)) {
        return true;
      }
    }

    // Check columns
    for (let j = 0; j < this.sideLength; j++) {
      if (this.grid.every((row) => row[j] === symbol)) {
        return true;
      }
    }

    // Check main diagonal
    if (this.grid.every((row, i) => row[i] === symbol)) {
      return true;
    }

    // Check anti-diagonal
    if (this.grid.every((row, i) => row[this.sideLength - 1 - i] === symbol)) {
      return true;
    }

    return false;
  }

  isFull(): boolean {
    return this.grid.every((row) => row.every((cell) => cell !== Symbol.EMPTY));
  }

  getWinner(): Symbol | null {
    for (const symbol of [Symbol.X, Symbol.O]) {
      if (this.checkWinner(symbol)) {
        return symbol;
      }
    }
    return null;
  }
}

class Game {
  private board: Board;
  private players: Player[];
  private currentPlayerIdx: number;

  constructor(player1: Player, player2: Player, boardSize: number = 3) {
    if (player1.getSymbol() === player2.getSymbol()) {
      throw new Error("Players must have different symbols");
    }
    this.board = new Board(boardSize);
    this.players = [player1, player2];
    this.currentPlayerIdx = 0;
  }

  private getCurrentPlayer(): Player {
    return this.players[this.currentPlayerIdx];
  }

  private switchPlayer(): void {
    this.currentPlayerIdx = 1 - this.currentPlayerIdx;
  }

  async play(): Promise<void> {
    console.log(
      `Welcome to Tic Tac Toe! Board size: ${this.board.getSideLength()}x${this.board.getSideLength()}`
    );
    console.log("Players take turns. Coordinates are 0-indexed.\n");

    while (true) {
      this.board.display();
      const currentPlayer = this.getCurrentPlayer();

      try {
        await currentPlayer.makeMove(this.board);
      } catch (error) {
        console.log(`Error: ${error}`);
        continue;
      }

      const winner = this.board.getWinner();
      if (winner) {
        this.board.display();
        console.log(`🎉 Player ${winner} wins!`);
        break;
      }

      if (this.board.isFull()) {
        this.board.display();
        console.log("🤝 It's a draw!");
        break;
      }

      this.switchPlayer();
    }
  }
}

// Factory pattern for player creation
class PlayerFactory {
  static createHumanPlayer(symbol: Symbol): HumanPlayer {
    return new HumanPlayer(symbol);
  }
}

// Main execution
async function main(): Promise<void> {
  try {
    const player1 = PlayerFactory.createHumanPlayer(Symbol.X);
    const player2 = PlayerFactory.createHumanPlayer(Symbol.O);
    const game = new Game(player1, player2);
    await game.play();
  } catch (error) {
    console.log(`Error initializing game: ${error}`);
  }
}

// Export for module usage
export { Symbol, Player, HumanPlayer, Board, Game, PlayerFactory };

// Run if this is the main module
// if (require.main === module) {
//   main().catch(console.error);
// }
