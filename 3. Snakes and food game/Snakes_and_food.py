"""
Snake and Food Game Implementation
A classic Snake game with growth/shrink food mechanics and simulation mode.
🏗️ System Design Highlights
1. Clean Architecture & Separation of Concerns

Domain Models: Snake, Food, GameBoard - Pure business logic
Game Engine: GameEngine - Orchestrates game flow and rules
Rendering Interface: IGameRenderer - Abstract rendering with ConsoleRenderer implementation
Managers: FoodManager - Handles food generation and consumption

2. SOLID Principles Implementation

Single Responsibility: Each class has one clear purpose
Open/Closed: Extensible through interfaces (renderer, food types)
Liskov Substitution: Renderer interface allows different implementations
Interface Segregation: Clean, focused interfaces
Dependency Inversion: Game engine depends on abstractions

3. Key Features
🐍 Snake Mechanics:

Collision detection (walls and self)
Growth/shrink functionality
Direction validation (prevents immediate reverse)
Minimum length enforcement

🍎 Food System:

Growth Food (+): Increases snake length, 10 points
Shrink Food (-): Decreases snake length, 5 points
Bonus Food (*): No length change, 20 points
Weighted random generation with configurable probabilities

🎮 Game Engine:

Automatic simulation with intelligent movement patterns
Configurable board dimensions
Score tracking and move counting
Multiple termination conditions

4. Code Quality Features

Type Safety: Full type hints throughout
Immutable Data: Position and Food dataclasses
Error Handling: Boundary validation and empty position checking
Documentation: Comprehensive docstrings and inline comments
Enum Usage: Type-safe constants for directions, food types, game states

5. Simulation Intelligence
The game includes a smart simulation that:

Follows predefined exploration patterns
Adds randomness to keep gameplay interesting
Automatically handles food consumption and scoring
Provides real-time visualization of game state

🚀 Usage
The game runs automatically in simulation mode, displaying:

Real-time board state with ASCII graphics
Current score, moves, and snake length
Different food types with distinct symbols
Game over conditions and final statistics

This implementation demonstrates production-ready code with clean architecture, proper error handling, extensibility, and maintainability. The modular design makes it easy to add new features like different game modes, AI players, or alternative rendering systems.
Author: Senior System Design Expert
Date: August 2025
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set
import random
import time
from abc import ABC, abstractmethod


class Direction(Enum):
    """Enumeration for snake movement directions."""
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class FoodType(Enum):
    """Enumeration for different types of food items."""
    GROWTH = auto()      # Increases snake length
    SHRINK = auto()      # Decreases snake length
    BONUS = auto()       # Extra points but no length change


@dataclass(frozen=True)
class Position:
    """Immutable position class representing coordinates on the board."""
    x: int
    y: int
    
    def __add__(self, other: 'Position') -> 'Position':
        """Add two positions together."""
        return Position(self.x + other.x, self.y + other.y)
    
    def is_valid(self, board_width: int, board_height: int) -> bool:
        """Check if position is within board boundaries."""
        return 0 <= self.x < board_width and 0 <= self.y < board_height


@dataclass
class Food:
    """Represents a food item on the board."""
    position: Position
    food_type: FoodType
    points: int
    length_change: int  # Positive for growth, negative for shrink


class GameState(Enum):
    """Enumeration for game states."""
    PLAYING = auto()
    GAME_OVER = auto()
    PAUSED = auto()


class IGameRenderer(ABC):
    """Abstract interface for game rendering."""
    
    @abstractmethod
    def render(self, board: 'GameBoard', snake: 'Snake', foods: List[Food], 
               score: int, moves: int) -> None:
        """Render the current game state."""
        pass


class ConsoleRenderer(IGameRenderer):
    """Console-based game renderer implementation."""
    
    def __init__(self):
        self.symbols = {
            'empty': '.',
            'snake_head': '@',
            'snake_body': '#',
            'growth_food': '+',
            'shrink_food': '-',
            'bonus_food': '*'
        }
    
    def render(self, board: 'GameBoard', snake: 'Snake', foods: List[Food], 
               score: int, moves: int) -> None:
        """Render game state to console."""
        print("\n" + "="*50)
        print(f"Score: {score} | Moves: {moves} | Length: {len(snake.body)}")
        print("="*50)
        
        # Create display grid
        grid = [[self.symbols['empty'] for _ in range(board.width)] 
                for _ in range(board.height)]
        
        # Place foods
        for food in foods:
            symbol = {
                FoodType.GROWTH: self.symbols['growth_food'],
                FoodType.SHRINK: self.symbols['shrink_food'],
                FoodType.BONUS: self.symbols['bonus_food']
            }[food.food_type]
            grid[food.position.y][food.position.x] = symbol
        
        # Place snake
        for i, segment in enumerate(snake.body):
            if i == 0:  # Head
                grid[segment.y][segment.x] = self.symbols['snake_head']
            else:  # Body
                grid[segment.y][segment.x] = self.symbols['snake_body']
        
        # Print grid
        for row in grid:
            print(' '.join(row))


class Snake:
    """Represents the snake entity with movement and growth mechanics."""
    
    def __init__(self, initial_position: Position, initial_length: int = 3):
        """
        Initialize snake with given starting position and length.
        
        Args:
            initial_position: Starting position of snake head
            initial_length: Initial length of the snake
        """
        self.body: List[Position] = []
        self.direction = Direction.RIGHT
        self.min_length = 1  # Snake cannot shrink below this
        
        # Initialize snake body
        for i in range(initial_length):
            self.body.append(Position(initial_position.x - i, initial_position.y))
    
    def get_head(self) -> Position:
        """Get the position of snake's head."""
        return self.body[0]
    
    def move(self, new_direction: Optional[Direction] = None) -> Position:
        """
        Move the snake in the current direction.
        
        Args:
            new_direction: Optional new direction to change to
            
        Returns:
            New head position after movement
        """
        if new_direction:
            self._change_direction(new_direction)
        
        # Calculate new head position
        direction_offsets = {
            Direction.UP: Position(0, -1),
            Direction.DOWN: Position(0, 1),
            Direction.LEFT: Position(-1, 0),
            Direction.RIGHT: Position(1, 0)
        }
        
        new_head = self.get_head() + direction_offsets[self.direction]
        return new_head
    
    def _change_direction(self, new_direction: Direction) -> None:
        """Change snake direction with validation to prevent reverse movement."""
        opposite_directions = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT
        }
        
        # Prevent immediate reverse direction if snake has more than one segment
        if len(self.body) > 1 and new_direction == opposite_directions[self.direction]:
            return
        
        self.direction = new_direction
    
    def grow(self, length_change: int) -> None:
        """
        Grow or shrink the snake by specified amount.
        
        Args:
            length_change: Positive to grow, negative to shrink
        """
        if length_change > 0:
            # Grow by duplicating tail segments
            tail = self.body[-1]
            for _ in range(length_change):
                self.body.append(tail)
        elif length_change < 0:
            # Shrink but maintain minimum length
            segments_to_remove = min(abs(length_change), 
                                   len(self.body) - self.min_length)
            for _ in range(segments_to_remove):
                if len(self.body) > self.min_length:
                    self.body.pop()
    
    def update_position(self, new_head: Position) -> None:
        """Update snake position by adding new head and removing tail."""
        self.body.insert(0, new_head)
        self.body.pop()  # Remove tail
    
    def check_self_collision(self, position: Position) -> bool:
        """Check if given position collides with snake body."""
        return position in self.body[1:]  # Exclude head from collision check


class GameBoard:
    """Represents the game board with boundary management."""
    
    def __init__(self, width: int, height: int):
        """
        Initialize game board with specified dimensions.
        
        Args:
            width: Board width
            height: Board height
        """
        self.width = max(5, width)    # Minimum viable board size
        self.height = max(5, height)
    
    def is_position_valid(self, position: Position) -> bool:
        """Check if position is within board boundaries."""
        return position.is_valid(self.width, self.height)
    
    def get_random_empty_position(self, occupied_positions: Set[Position]) -> Position:
        """
        Generate a random empty position on the board.
        
        Args:
            occupied_positions: Set of positions that are already occupied
            
        Returns:
            Random empty position
            
        Raises:
            ValueError: If no empty positions available
        """
        available_positions = []
        
        for x in range(self.width):
            for y in range(self.height):
                pos = Position(x, y)
                if pos not in occupied_positions:
                    available_positions.append(pos)
        
        if not available_positions:
            raise ValueError("No empty positions available on board")
        
        return random.choice(available_positions)


class FoodManager:
    """Manages food generation, placement, and consumption logic."""
    
    def __init__(self, max_foods: int = 3):
        """
        Initialize food manager.
        
        Args:
            max_foods: Maximum number of foods on board simultaneously
        """
        self.max_foods = max_foods
        self.foods: List[Food] = []
        self.food_configs = {
            FoodType.GROWTH: {'points': 10, 'length_change': 1, 'weight': 0.6},
            FoodType.SHRINK: {'points': 5, 'length_change': -1, 'weight': 0.25},
            FoodType.BONUS: {'points': 20, 'length_change': 0, 'weight': 0.15}
        }
    
    def generate_food(self, board: GameBoard, occupied_positions: Set[Position]) -> None:
        """Generate new food items if below maximum limit."""
        while len(self.foods) < self.max_foods:
            try:
                position = board.get_random_empty_position(
                    occupied_positions | {food.position for food in self.foods}
                )
                food_type = self._select_random_food_type()
                config = self.food_configs[food_type]
                
                food = Food(
                    position=position,
                    food_type=food_type,
                    points=config['points'],
                    length_change=config['length_change']
                )
                self.foods.append(food)
                
            except ValueError:
                break  # No more empty positions available
    
    def _select_random_food_type(self) -> FoodType:
        """Select random food type based on weighted probabilities."""
        food_types = list(self.food_configs.keys())
        weights = [self.food_configs[ft]['weight'] for ft in food_types]
        return random.choices(food_types, weights=weights)[0]
    
    def consume_food_at_position(self, position: Position) -> Optional[Food]:
        """
        Consume food at given position if it exists.
        
        Args:
            position: Position to check for food
            
        Returns:
            Consumed food item or None if no food at position
        """
        for i, food in enumerate(self.foods):
            if food.position == position:
                return self.foods.pop(i)
        return None


class GameEngine:
    """Main game engine managing game logic, state, and simulation."""
    
    def __init__(self, board_width: int = 15, board_height: int = 10,
                 renderer: Optional[IGameRenderer] = None):
        """
        Initialize game engine.
        
        Args:
            board_width: Width of game board
            board_height: Height of game board
            renderer: Game renderer implementation
        """
        self.board = GameBoard(board_width, board_height)
        self.snake = Snake(Position(board_width // 2, board_height // 2))
        self.food_manager = FoodManager()
        self.renderer = renderer or ConsoleRenderer()
        
        # Game state
        self.state = GameState.PLAYING
        self.score = 0
        self.moves = 0
        self.max_moves = 500  # Simulation limit
        
        # Direction sequence for simulation
        self.direction_sequence = self._generate_direction_sequence()
        self.sequence_index = 0
    
    def _generate_direction_sequence(self) -> List[Direction]:
        """Generate a sequence of directions for simulation."""
        directions = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        sequence = []
        
        # Create a pattern that explores the board
        for _ in range(50):
            sequence.extend([
                Direction.RIGHT, Direction.RIGHT, Direction.DOWN,
                Direction.LEFT, Direction.LEFT, Direction.UP
            ])
        
        # Add some randomness
        for _ in range(100):
            sequence.append(random.choice(directions))
        
        return sequence
    
    def get_occupied_positions(self) -> Set[Position]:
        """Get all positions occupied by the snake."""
        return set(self.snake.body)
    
    def step(self) -> bool:
        """
        Execute one game step.
        
        Returns:
            True if game continues, False if game over
        """
        if self.state != GameState.PLAYING:
            return False
        
        # Get next direction from simulation sequence
        if self.sequence_index < len(self.direction_sequence):
            next_direction = self.direction_sequence[self.sequence_index]
            self.sequence_index += 1
        else:
            next_direction = random.choice(list(Direction))
        
        # Move snake
        new_head = self.snake.move(next_direction)
        
        # Check collisions
        if not self.board.is_position_valid(new_head):
            self.state = GameState.GAME_OVER
            return False
        
        if self.snake.check_self_collision(new_head):
            self.state = GameState.GAME_OVER
            return False
        
        # Check food consumption
        consumed_food = self.food_manager.consume_food_at_position(new_head)
        
        if consumed_food:
            # Update score and snake length
            self.score += consumed_food.points
            self.snake.grow(consumed_food.length_change)
        
        # Update snake position
        self.snake.update_position(new_head)
        
        # Generate new food
        self.food_manager.generate_food(self.board, self.get_occupied_positions())
        
        # Update game state
        self.moves += 1
        
        # Check termination conditions
        if self.moves >= self.max_moves:
            self.state = GameState.GAME_OVER
            return False
        
        return True
    
    def run_simulation(self, steps_per_second: float = 2.0, 
                      render_every_n_steps: int = 1) -> None:
        """
        Run the game simulation.
        
        Args:
            steps_per_second: Simulation speed
            render_every_n_steps: Render frequency (1 = every step)
        """
        print("🐍 Starting Snake Game Simulation...")
        print(f"Board Size: {self.board.width}x{self.board.height}")
        print(f"Simulation Speed: {steps_per_second} steps/second")
        print("\nLegend:")
        print("@ = Snake Head, # = Snake Body")
        print("+ = Growth Food (+1 length), - = Shrink Food (-1 length)")
        print("* = Bonus Food (+20 points, no length change)")
        print("\nPress Ctrl+C to stop simulation\n")
        
        step_delay = 1.0 / steps_per_second
        step_count = 0
        
        # Generate initial foods
        self.food_manager.generate_food(self.board, self.get_occupied_positions())
        
        try:
            while self.step():
                step_count += 1
                
                if step_count % render_every_n_steps == 0:
                    self.renderer.render(
                        self.board, self.snake, self.food_manager.foods,
                        self.score, self.moves
                    )
                    time.sleep(step_delay)
                    
        except KeyboardInterrupt:
            print("\n⏹️ Simulation stopped by user")
        
        # Final render
        self.renderer.render(
            self.board, self.snake, self.food_manager.foods,
            self.score, self.moves
        )
        
        # Game over summary
        print(f"\n🎮 Game Over!")
        print(f"Final Score: {self.score}")
        print(f"Final Snake Length: {len(self.snake.body)}")
        print(f"Total Moves: {self.moves}")
        print(f"Reason: {'Max moves reached' if self.moves >= self.max_moves else 'Collision'}")


def main():
    """Main function to run the Snake game simulation."""
    # Create and run the game
    game = GameEngine(
        board_width=20,
        board_height=15,
        renderer=ConsoleRenderer()
    )
    
    game.run_simulation(
        steps_per_second=3.0,
        render_every_n_steps=1
    )


if __name__ == "__main__":
    main()