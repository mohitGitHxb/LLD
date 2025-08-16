/**
 * Snake and Food Game Implementation - TypeScript Version
 * A modern, type-safe implementation of the classic Snake game with growth/shrink mechanics
 *
 * @author Senior System Design Expert
 * @date August 2025
 */

// ========================= ENUMS & TYPES =========================

/**
 * Snake movement directions
 */
enum Direction {
  UP = "UP",
  DOWN = "DOWN",
  LEFT = "LEFT",
  RIGHT = "RIGHT",
}

/**
 * Different types of food items with varying effects
 */
enum FoodType {
  GROWTH = "GROWTH", // Increases snake length
  SHRINK = "SHRINK", // Decreases snake length
  BONUS = "BONUS", // Extra points, no length change
}

/**
 * Current state of the game
 */
enum GameState {
  PLAYING = "PLAYING",
  GAME_OVER = "GAME_OVER",
  PAUSED = "PAUSED",
}

// ========================= DATA MODELS =========================

/**
 * Immutable position class representing coordinates on the board
 */
class Position {
  constructor(public readonly x: number, public readonly y: number) {}

  /**
   * Add two positions together
   */
  add(other: Position): Position {
    return new Position(this.x + other.x, this.y + other.y);
  }

  /**
   * Check if position is within board boundaries
   */
  isValid(boardWidth: number, boardHeight: number): boolean {
    return (
      this.x >= 0 && this.x < boardWidth && this.y >= 0 && this.y < boardHeight
    );
  }

  /**
   * Check equality with another position
   */
  equals(other: Position): boolean {
    return this.x === other.x && this.y === other.y;
  }

  /**
   * Convert to string for Set operations
   */
  toString(): string {
    return `${this.x},${this.y}`;
  }
}

/**
 * Represents a food item on the board
 */
interface Food {
  readonly position: Position;
  readonly foodType: FoodType;
  readonly points: number;
  readonly lengthChange: number; // Positive for growth, negative for shrink
}

/**
 * Configuration for different food types
 */
interface FoodConfig {
  readonly points: number;
  readonly lengthChange: number;
  readonly weight: number; // Probability weight for generation
}

/**
 * Game statistics and metrics
 */
interface GameStats {
  readonly score: number;
  readonly moves: number;
  readonly snakeLength: number;
  readonly foodsConsumed: number;
  readonly gameState: GameState;
}

// ========================= INTERFACES =========================

/**
 * Abstract interface for game rendering
 */
interface IGameRenderer {
  /**
   * Render the current game state
   */
  render(
    board: GameBoard,
    snake: Snake,
    foods: readonly Food[],
    stats: GameStats
  ): void;
}

/**
 * Interface for game event handling
 */
interface IGameEventHandler {
  onFoodConsumed?(food: Food, newScore: number): void;
  onSnakeGrow?(newLength: number): void;
  onSnakeShrink?(newLength: number): void;
  onGameOver?(finalStats: GameStats): void;
}

// ========================= CORE GAME CLASSES =========================

/**
 * Represents the snake entity with movement and growth mechanics
 */
class Snake {
  private body: Position[];
  private direction: Direction = Direction.RIGHT;
  private readonly minLength: number = 1;

  constructor(initialPosition: Position, initialLength: number = 3) {
    this.body = [];

    // Initialize snake body segments
    for (let i = 0; i < initialLength; i++) {
      this.body.push(new Position(initialPosition.x - i, initialPosition.y));
    }
  }

  /**
   * Get the position of snake's head
   */
  getHead(): Position {
    return this.body[0];
  }

  /**
   * Get all body segments
   */
  getBody(): readonly Position[] {
    return [...this.body]; // Return defensive copy
  }

  /**
   * Get current snake length
   */
  getLength(): number {
    return this.body.length;
  }

  /**
   * Get current movement direction
   */
  getDirection(): Direction {
    return this.direction;
  }

  /**
   * Move the snake in the current direction
   */
  move(newDirection?: Direction): Position {
    if (newDirection) {
      this.changeDirection(newDirection);
    }

    const directionOffsets: Record<Direction, Position> = {
      [Direction.UP]: new Position(0, -1),
      [Direction.DOWN]: new Position(0, 1),
      [Direction.LEFT]: new Position(-1, 0),
      [Direction.RIGHT]: new Position(1, 0),
    };

    return this.getHead().add(directionOffsets[this.direction]);
  }

  /**
   * Change snake direction with validation
   */
  private changeDirection(newDirection: Direction): void {
    const oppositeDirections: Record<Direction, Direction> = {
      [Direction.UP]: Direction.DOWN,
      [Direction.DOWN]: Direction.UP,
      [Direction.LEFT]: Direction.RIGHT,
      [Direction.RIGHT]: Direction.LEFT,
    };

    // Prevent immediate reverse direction if snake has more than one segment
    if (
      this.body.length > 1 &&
      newDirection === oppositeDirections[this.direction]
    ) {
      return;
    }

    this.direction = newDirection;
  }

  /**
   * Grow or shrink the snake by specified amount
   */
  grow(lengthChange: number): void {
    if (lengthChange > 0) {
      // Grow by duplicating tail segments
      const tail = this.body[this.body.length - 1];
      for (let i = 0; i < lengthChange; i++) {
        this.body.push(new Position(tail.x, tail.y));
      }
    } else if (lengthChange < 0) {
      // Shrink but maintain minimum length
      const segmentsToRemove = Math.min(
        Math.abs(lengthChange),
        this.body.length - this.minLength
      );

      for (let i = 0; i < segmentsToRemove; i++) {
        if (this.body.length > this.minLength) {
          this.body.pop();
        }
      }
    }
  }

  /**
   * Update snake position by adding new head and removing tail
   */
  updatePosition(newHead: Position): void {
    this.body.unshift(newHead);
    this.body.pop();
  }

  /**
   * Check if given position collides with snake body
   */
  checkSelfCollision(position: Position): boolean {
    // Exclude head from collision check
    return this.body.slice(1).some((segment) => segment.equals(position));
  }
}

/**
 * Represents the game board with boundary management
 */
class GameBoard {
  public readonly width: number;
  public readonly height: number;

  constructor(width: number, height: number) {
    // Ensure minimum viable board size
    this.width = Math.max(5, width);
    this.height = Math.max(5, height);
  }

  /**
   * Check if position is within board boundaries
   */
  isPositionValid(position: Position): boolean {
    return position.isValid(this.width, this.height);
  }

  /**
   * Generate a random empty position on the board
   */
  getRandomEmptyPosition(occupiedPositions: Set<string>): Position {
    const availablePositions: Position[] = [];

    for (let x = 0; x < this.width; x++) {
      for (let y = 0; y < this.height; y++) {
        const pos = new Position(x, y);
        if (!occupiedPositions.has(pos.toString())) {
          availablePositions.push(pos);
        }
      }
    }

    if (availablePositions.length === 0) {
      throw new Error("No empty positions available on board");
    }

    const randomIndex = Math.floor(Math.random() * availablePositions.length);
    return availablePositions[randomIndex];
  }

  /**
   * Get total number of positions on board
   */
  getTotalPositions(): number {
    return this.width * this.height;
  }
}

/**
 * Manages food generation, placement, and consumption logic
 */
class FoodManager {
  private foods: Food[] = [];
  private readonly maxFoods: number;
  private readonly foodConfigs: Record<FoodType, FoodConfig> = {
    [FoodType.GROWTH]: { points: 10, lengthChange: 1, weight: 0.6 },
    [FoodType.SHRINK]: { points: 5, lengthChange: -1, weight: 0.25 },
    [FoodType.BONUS]: { points: 20, lengthChange: 0, weight: 0.15 },
  };

  constructor(maxFoods: number = 3) {
    this.maxFoods = maxFoods;
  }

  /**
   * Get all current foods on the board
   */
  getFoods(): readonly Food[] {
    return [...this.foods]; // Return defensive copy
  }

  /**
   * Generate new food items if below maximum limit
   */
  generateFood(board: GameBoard, occupiedPositions: Set<string>): void {
    while (this.foods.length < this.maxFoods) {
      try {
        const foodPositions = new Set(
          this.foods.map((f) => f.position.toString())
        );
        const allOccupied = new Set([...occupiedPositions, ...foodPositions]);

        const position = board.getRandomEmptyPosition(allOccupied);
        const foodType = this.selectRandomFoodType();
        const config = this.foodConfigs[foodType];

        const food: Food = {
          position,
          foodType,
          points: config.points,
          lengthChange: config.lengthChange,
        };

        this.foods.push(food);
      } catch (error) {
        // No more empty positions available
        break;
      }
    }
  }

  /**
   * Select random food type based on weighted probabilities
   */
  private selectRandomFoodType(): FoodType {
    const foodTypes = Object.keys(this.foodConfigs) as FoodType[];
    const totalWeight = foodTypes.reduce(
      (sum, type) => sum + this.foodConfigs[type].weight,
      0
    );

    let random = Math.random() * totalWeight;

    for (const foodType of foodTypes) {
      random -= this.foodConfigs[foodType].weight;
      if (random <= 0) {
        return foodType;
      }
    }

    return FoodType.GROWTH; // Fallback
  }

  /**
   * Consume food at given position if it exists
   */
  consumeFoodAtPosition(position: Position): Food | null {
    const foodIndex = this.foods.findIndex((food) =>
      food.position.equals(position)
    );

    if (foodIndex !== -1) {
      return this.foods.splice(foodIndex, 1)[0];
    }

    return null;
  }

  /**
   * Clear all foods from the board
   */
  clearAllFoods(): void {
    this.foods = [];
  }
}

/**
 * Console-based game renderer implementation
 */
class ConsoleRenderer implements IGameRenderer {
  private readonly symbols = {
    empty: ".",
    snakeHead: "@",
    snakeBody: "#",
    growthFood: "+",
    shrinkFood: "-",
    bonusFood: "*",
  } as const;

  /**
   * Render game state to console
   */
  render(
    board: GameBoard,
    snake: Snake,
    foods: readonly Food[],
    stats: GameStats
  ): void {
    console.log("\n" + "=".repeat(60));
    console.log(
      `Score: ${stats.score} | Moves: ${stats.moves} | Length: ${stats.snakeLength}`
    );
    console.log("=".repeat(60));

    // Create display grid
    const grid: string[][] = Array(board.height)
      .fill(null)
      .map(() => Array(board.width).fill(this.symbols.empty));

    // Place foods
    foods.forEach((food) => {
      const symbol = {
        [FoodType.GROWTH]: this.symbols.growthFood,
        [FoodType.SHRINK]: this.symbols.shrinkFood,
        [FoodType.BONUS]: this.symbols.bonusFood,
      }[food.foodType];

      grid[food.position.y][food.position.x] = symbol;
    });

    // Place snake
    snake.getBody().forEach((segment, index) => {
      const symbol =
        index === 0 ? this.symbols.snakeHead : this.symbols.snakeBody;
      grid[segment.y][segment.x] = symbol;
    });

    // Print grid
    grid.forEach((row) => console.log(" " + row.join(" ")));
  }
}

// ========================= GAME ENGINE =========================

/**
 * Main game engine managing game logic, state, and simulation
 */
class GameEngine {
  private readonly board: GameBoard;
  private readonly snake: Snake;
  private readonly foodManager: FoodManager;
  private readonly renderer: IGameRenderer;
  private readonly eventHandler?: IGameEventHandler;

  private gameState: GameState = GameState.PLAYING;
  private score: number = 0;
  private moves: number = 0;
  private foodsConsumed: number = 0;
  private readonly maxMoves: number;

  // Simulation properties
  private readonly directionSequence: Direction[];
  private sequenceIndex: number = 0;

  constructor(
    boardWidth: number = 15,
    boardHeight: number = 10,
    renderer?: IGameRenderer,
    eventHandler?: IGameEventHandler,
    maxMoves: number = 500
  ) {
    this.board = new GameBoard(boardWidth, boardHeight);
    this.snake = new Snake(
      new Position(Math.floor(boardWidth / 2), Math.floor(boardHeight / 2))
    );
    this.foodManager = new FoodManager();
    this.renderer = renderer ?? new ConsoleRenderer();
    this.eventHandler = eventHandler;
    this.maxMoves = maxMoves;

    this.directionSequence = this.generateDirectionSequence();
  }

  /**
   * Generate a sequence of directions for simulation
   */
  private generateDirectionSequence(): Direction[] {
    const directions = [
      Direction.UP,
      Direction.DOWN,
      Direction.LEFT,
      Direction.RIGHT,
    ];
    const sequence: Direction[] = [];

    // Create exploration patterns
    for (let i = 0; i < 50; i++) {
      sequence.push(
        Direction.RIGHT,
        Direction.RIGHT,
        Direction.DOWN,
        Direction.LEFT,
        Direction.LEFT,
        Direction.UP
      );
    }

    // Add randomness
    for (let i = 0; i < 100; i++) {
      const randomDirection =
        directions[Math.floor(Math.random() * directions.length)];
      sequence.push(randomDirection);
    }

    return sequence;
  }

  /**
   * Get all positions occupied by the snake
   */
  private getOccupiedPositions(): Set<string> {
    return new Set(this.snake.getBody().map((pos) => pos.toString()));
  }

  /**
   * Get current game statistics
   */
  getStats(): GameStats {
    return {
      score: this.score,
      moves: this.moves,
      snakeLength: this.snake.getLength(),
      foodsConsumed: this.foodsConsumed,
      gameState: this.gameState,
    };
  }

  /**
   * Execute one game step
   */
  step(): boolean {
    if (this.gameState !== GameState.PLAYING) {
      return false;
    }

    // Get next direction from simulation sequence
    const nextDirection =
      this.sequenceIndex < this.directionSequence.length
        ? this.directionSequence[this.sequenceIndex++]
        : [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT][
            Math.floor(Math.random() * 4)
          ];

    // Move snake
    const newHead = this.snake.move(nextDirection);

    // Check boundary collision
    if (!this.board.isPositionValid(newHead)) {
      this.gameState = GameState.GAME_OVER;
      this.eventHandler?.onGameOver?.(this.getStats());
      return false;
    }

    // Check self collision
    if (this.snake.checkSelfCollision(newHead)) {
      this.gameState = GameState.GAME_OVER;
      this.eventHandler?.onGameOver?.(this.getStats());
      return false;
    }

    // Check food consumption
    const consumedFood = this.foodManager.consumeFoodAtPosition(newHead);
    const previousLength = this.snake.getLength();

    if (consumedFood) {
      // Update score and snake length
      this.score += consumedFood.points;
      this.foodsConsumed++;
      this.snake.grow(consumedFood.lengthChange);

      // Trigger events
      this.eventHandler?.onFoodConsumed?.(consumedFood, this.score);

      const newLength = this.snake.getLength();
      if (newLength > previousLength) {
        this.eventHandler?.onSnakeGrow?.(newLength);
      } else if (newLength < previousLength) {
        this.eventHandler?.onSnakeShrink?.(newLength);
      }
    }

    // Update snake position
    this.snake.updatePosition(newHead);

    // Generate new food
    this.foodManager.generateFood(this.board, this.getOccupiedPositions());

    // Update moves counter
    this.moves++;

    // Check termination condition
    if (this.moves >= this.maxMoves) {
      this.gameState = GameState.GAME_OVER;
      this.eventHandler?.onGameOver?.(this.getStats());
      return false;
    }

    return true;
  }

  /**
   * Run the game simulation
   */
  async runSimulation(
    stepsPerSecond: number = 2.0,
    renderEveryNSteps: number = 1
  ): Promise<GameStats> {
    console.log("🐍 Starting Snake Game Simulation...");
    console.log(`Board Size: ${this.board.width}x${this.board.height}`);
    console.log(`Simulation Speed: ${stepsPerSecond} steps/second`);
    console.log("\nLegend:");
    console.log("@ = Snake Head, # = Snake Body");
    console.log("+ = Growth Food (+1 length), - = Shrink Food (-1 length)");
    console.log("* = Bonus Food (+20 points, no length change)");
    console.log("\nSimulation running...\n");

    const stepDelay = 1000 / stepsPerSecond; // Convert to milliseconds
    let stepCount = 0;

    // Generate initial foods
    this.foodManager.generateFood(this.board, this.getOccupiedPositions());

    return new Promise((resolve) => {
      const gameLoop = () => {
        if (!this.step()) {
          // Game over - final render and resolve
          this.renderer.render(
            this.board,
            this.snake,
            this.foodManager.getFoods(),
            this.getStats()
          );
          this.printGameSummary();
          resolve(this.getStats());
          return;
        }

        stepCount++;

        if (stepCount % renderEveryNSteps === 0) {
          this.renderer.render(
            this.board,
            this.snake,
            this.foodManager.getFoods(),
            this.getStats()
          );
        }

        setTimeout(gameLoop, stepDelay);
      };

      gameLoop();
    });
  }

  /**
   * Print final game summary
   */
  private printGameSummary(): void {
    const stats = this.getStats();
    console.log("\n🎮 Game Over!");
    console.log(`Final Score: ${stats.score}`);
    console.log(`Final Snake Length: ${stats.snakeLength}`);
    console.log(`Total Moves: ${stats.moves}`);
    console.log(`Foods Consumed: ${stats.foodsConsumed}`);
    console.log(
      `Reason: ${
        stats.moves >= this.maxMoves ? "Max moves reached" : "Collision"
      }`
    );
  }

  /**
   * Pause the game
   */
  pause(): void {
    if (this.gameState === GameState.PLAYING) {
      this.gameState = GameState.PAUSED;
    }
  }

  /**
   * Resume the game
   */
  resume(): void {
    if (this.gameState === GameState.PAUSED) {
      this.gameState = GameState.PLAYING;
    }
  }

  /**
   * Reset the game to initial state
   */
  reset(): void {
    this.gameState = GameState.PLAYING;
    this.score = 0;
    this.moves = 0;
    this.foodsConsumed = 0;
    this.sequenceIndex = 0;
    this.foodManager.clearAllFoods();

    // Reset snake position
    const centerPos = new Position(
      Math.floor(this.board.width / 2),
      Math.floor(this.board.height / 2)
    );
    // Note: In a full implementation, we'd need to reinitialize the snake
    // For now, this demonstrates the reset pattern
  }
}

// ========================= MAIN EXECUTION =========================

/**
 * Event handler for game events
 */
class GameEventHandler implements IGameEventHandler {
  onFoodConsumed(food: Food, newScore: number): void {
    const foodName = {
      [FoodType.GROWTH]: "Growth Food",
      [FoodType.SHRINK]: "Shrink Food",
      [FoodType.BONUS]: "Bonus Food",
    }[food.foodType];

    // Could log to console or trigger UI updates
    // console.log(`🍎 ${foodName} consumed! Score: ${newScore}`);
  }

  onSnakeGrow(newLength: number): void {
    // console.log(`📈 Snake grew to length ${newLength}`);
  }

  onSnakeShrink(newLength: number): void {
    // console.log(`📉 Snake shrunk to length ${newLength}`);
  }

  onGameOver(finalStats: GameStats): void {
    console.log(`💀 Game Over! Final score: ${finalStats.score}`);
  }
}

/**
 * Main function to run the Snake game simulation
 */
async function main(): Promise<void> {
  const eventHandler = new GameEventHandler();
  const renderer = new ConsoleRenderer();

  const game = new GameEngine(
    20, // board width
    15, // board height
    renderer,
    eventHandler,
    500 // max moves
  );

  try {
    await game.runSimulation(3.0, 1); // 3 steps per second, render every step
  } catch (error) {
    console.error("Error running simulation:", error);
  }
}

// Export classes for potential module usage
export {
  Direction,
  FoodType,
  GameState,
  Position,
  Food,
  GameStats,
  IGameRenderer,
  IGameEventHandler,
  Snake,
  GameBoard,
  FoodManager,
  ConsoleRenderer,
  GameEngine,
};

// // Run the game if this is the main module
// if (typeof require !== "undefined" && require.main === module) {
//   main().catch(console.error);
// }
