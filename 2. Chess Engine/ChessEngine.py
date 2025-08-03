from enum import Enum
from abc import ABC, abstractmethod
from typing import List, Text, Optional, Tuple, Dict
import copy

""" 
    Design Patterns Used:
    Strategy Pattern: Each piece type implements its own movement strategy through the get_possible_moves() method.

    Factory Pattern: PieceFactory centralizes piece creation logic.

    Template Method Pattern: Base Piece class defines common behavior while allowing subclasses to implement specific logic.

    Facade Pattern: ChessGame provides a simplified interface for complex board operations.

    Value Object Pattern: Position and Move are immutable objects representing game concepts.

    State Pattern: GameState enum manages different game states.

    Key Features:
    Complete piece movement logic including special moves (castling, en passant, pawn promotion)
    Legal move validation with check detection
    Game state management (checkmate, stalemate, draw conditions)
    Move history tracking
    Algebraic notation support
    Comprehensive error handling
    Benefits of This Design:
    Maintainability: Each class has a single responsibility
    Extensibility: Easy to add new piece types or game variants
    Testability: Clean interfaces make unit testing straightforward
    Reusability: Components can be reused in different contexts
    Readability: Clear naming and structure make the code self-documenting

"""
class PieceType(Enum):
    PAWN = "Pawn"
    ROOK = "Rook"
    KNIGHT = "Knight"
    BISHOP = "Bishop"
    QUEEN = "Queen"
    KING = "King"

    def __str__(self) -> Text:
        return self.value

class Color(Enum):
    WHITE = "White"
    BLACK = "Black"

    def __str__(self) -> Text:
        return self.value

class Position:
    """
    Represents a position on the chess board using row and column coordinates.
    Encapsulates position logic and provides validation.
    Design Pattern: Value Object - immutable representation of coordinates
    """
    def __init__(self, row: int, col: int):
        if not (0 <= row <= 7) or not (0 <= col <= 7):
            raise ValueError(f"Invalid position: ({row}, {col}). Must be between 0-7")
        self._row = row
        self._col = col
    
    @property
    def row(self) -> int:
        return self._row
    
    @property
    def col(self) -> int:
        return self._col
    
    def to_algebraic(self) -> str:
        """Convert to algebraic notation (e.g., 'e4')"""
        return chr(ord('a') + self._col) + str(8 - self._row)
    
    @classmethod
    def from_algebraic(cls, notation: str) -> 'Position':
        """Create position from algebraic notation"""
        if len(notation) != 2:
            raise ValueError(f"Invalid algebraic notation: {notation}")
        col = ord(notation[0].lower()) - ord('a')
        row = 8 - int(notation[1])
        return cls(row, col)
    
    def __eq__(self, other) -> bool:
        return isinstance(other, Position) and self._row == other._row and self._col == other._col
    
    def __hash__(self) -> int:
        return hash((self._row, self._col))
    
    def __str__(self) -> str:
        return self.to_algebraic()

class Move:
    """
    Represents a chess move with source and destination positions.
    Design Pattern: Value Object - immutable representation of a move
    Impact: Encapsulates move logic, making it easier to validate, store, and manipulate moves
    """
    def __init__(self, from_pos: Position, to_pos: Position, 
                 promotion_piece: Optional[PieceType] = None,
                 is_castling: bool = False,
                 is_en_passant: bool = False):
        self._from_pos = from_pos
        self._to_pos = to_pos
        self._promotion_piece = promotion_piece
        self._is_castling = is_castling
        self._is_en_passant = is_en_passant
    
    @property
    def from_pos(self) -> Position:
        return self._from_pos
    
    @property
    def to_pos(self) -> Position:
        return self._to_pos
    
    @property
    def promotion_piece(self) -> Optional[PieceType]:
        return self._promotion_piece
    
    @property
    def is_castling(self) -> bool:
        return self._is_castling
    
    @property
    def is_en_passant(self) -> bool:
        return self._is_en_passant
    
    def __eq__(self, other) -> bool:
        """Add equality comparison for Move objects"""
        return (isinstance(other, Move) and 
                self._from_pos == other._from_pos and
                self._to_pos == other._to_pos and
                self._promotion_piece == other._promotion_piece and
                self._is_castling == other._is_castling and
                self._is_en_passant == other._is_en_passant)
    
    def __hash__(self) -> int:
        """Add hash for Move objects to work with sets and dicts"""
        return hash((self._from_pos, self._to_pos, self._promotion_piece, 
                    self._is_castling, self._is_en_passant))
    
    def __str__(self) -> str:
        move_str = f"{self._from_pos}{self._to_pos}"
        if self._promotion_piece:
            move_str += f"={self._promotion_piece.value[0]}"
        return move_str

class Piece(ABC):
    """
    Abstract base class for all chess pieces.
    Design Pattern: Strategy Pattern - each piece type implements its own movement strategy
    Design Pattern: Template Method - common piece behavior defined here
    Impact: Ensures all pieces follow the same interface while allowing custom movement logic
    """
    def __init__(self, color: Color, piece_type: PieceType):
        self._color = color
        self._piece_type = piece_type
        self._has_moved = False  # Important for castling and pawn double moves
    
    @property
    def color(self) -> Color:
        return self._color
    
    @property
    def piece_type(self) -> PieceType:
        return self._piece_type
    
    @property
    def has_moved(self) -> bool:
        return self._has_moved
    
    def mark_as_moved(self):
        """Mark piece as having moved (important for castling rules)"""
        self._has_moved = True
    
    @abstractmethod
    def get_possible_moves(self, board: 'Board', current_pos: Position) -> List[Move]:
        """
        Abstract method that each piece must implement to define its movement rules.
        Template Method Pattern: defines the interface all pieces must follow
        """
        pass
    
    def is_move_valid(self, board: 'Board', move: Move) -> bool:
        """
        Template method that validates if a move is legal for this piece.
        Can be overridden by specific pieces for special rules.
        """
        possible_moves = self.get_possible_moves(board, move.from_pos)
        return move in possible_moves
    
    def __str__(self) -> str:
        color_prefix = 'W' if self._color == Color.WHITE else 'B'
        return f"{color_prefix}{self._piece_type.value[0]}"

class Pawn(Piece):
    """
    Pawn piece implementation with special rules: double move, en passant, promotion
    Strategy Pattern: Implements specific movement strategy for pawns
    """
    def __init__(self, color: Color):
        super().__init__(color, PieceType.PAWN)
    
    def get_possible_moves(self, board: 'Board', current_pos: Position) -> List[Move]:
        moves = []
        direction = -1 if self._color == Color.WHITE else 1  # White moves up (-1), Black moves down (+1)
        
        # Forward moves
        new_row = current_pos.row + direction
        if 0 <= new_row <= 7:
            new_pos = Position(new_row, current_pos.col)
            
            # One square forward
            if board.get_piece(new_pos) is None:
                # Check for promotion
                if new_row == 0 or new_row == 7:
                    # Add promotion moves for all possible pieces
                    for piece_type in [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]:
                        moves.append(Move(current_pos, new_pos, promotion_piece=piece_type))
                else:
                    moves.append(Move(current_pos, new_pos))
                
                # Two squares forward (initial move)
                if not self._has_moved:
                    two_forward = Position(new_row + direction, current_pos.col)
                    if 0 <= two_forward.row <= 7 and board.get_piece(two_forward) is None:
                        moves.append(Move(current_pos, two_forward))
        
        # Diagonal captures
        for col_offset in [-1, 1]:
            new_col = current_pos.col + col_offset
            if 0 <= new_col <= 7 and 0 <= new_row <= 7:
                capture_pos = Position(new_row, new_col)
                target_piece = board.get_piece(capture_pos)
                
                # Regular capture
                if target_piece and target_piece.color != self._color:
                    if new_row == 0 or new_row == 7:  # Promotion capture
                        for piece_type in [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]:
                            moves.append(Move(current_pos, capture_pos, promotion_piece=piece_type))
                    else:
                        moves.append(Move(current_pos, capture_pos))
                
                # En passant capture
                elif board.can_en_passant(current_pos, capture_pos):
                    moves.append(Move(current_pos, capture_pos, is_en_passant=True))
        
        return moves

class Rook(Piece):
    """Rook piece - moves horizontally and vertically"""
    def __init__(self, color: Color):
        super().__init__(color, PieceType.ROOK)
    
    def get_possible_moves(self, board: 'Board', current_pos: Position) -> List[Move]:
        moves = []
        # Horizontal and vertical directions
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for dr, dc in directions:
            for distance in range(1, 8):
                new_row = current_pos.row + dr * distance
                new_col = current_pos.col + dc * distance
                
                if not (0 <= new_row <= 7 and 0 <= new_col <= 7):
                    break
                
                new_pos = Position(new_row, new_col)
                target_piece = board.get_piece(new_pos)
                
                if target_piece is None:
                    moves.append(Move(current_pos, new_pos))
                elif target_piece.color != self._color:
                    moves.append(Move(current_pos, new_pos))  # Capture
                    break
                else:
                    break  # Blocked by own piece
        
        return moves

class Knight(Piece):
    """Knight piece - moves in L-shape"""
    def __init__(self, color: Color):
        super().__init__(color, PieceType.KNIGHT)
    
    def get_possible_moves(self, board: 'Board', current_pos: Position) -> List[Move]:
        moves = []
        # All possible knight moves (L-shaped)
        knight_moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), 
                       (1, -2), (1, 2), (2, -1), (2, 1)]
        
        for dr, dc in knight_moves:
            new_row = current_pos.row + dr
            new_col = current_pos.col + dc
            
            if 0 <= new_row <= 7 and 0 <= new_col <= 7:
                new_pos = Position(new_row, new_col)
                target_piece = board.get_piece(new_pos)
                
                if target_piece is None or target_piece.color != self._color:
                    moves.append(Move(current_pos, new_pos))
        
        return moves

class Bishop(Piece):
    """Bishop piece - moves diagonally"""
    def __init__(self, color: Color):
        super().__init__(color, PieceType.BISHOP)
    
    def get_possible_moves(self, board: 'Board', current_pos: Position) -> List[Move]:
        moves = []
        # Diagonal directions
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        for dr, dc in directions:
            for distance in range(1, 8):
                new_row = current_pos.row + dr * distance
                new_col = current_pos.col + dc * distance
                
                if not (0 <= new_row <= 7 and 0 <= new_col <= 7):
                    break
                
                new_pos = Position(new_row, new_col)
                target_piece = board.get_piece(new_pos)
                
                if target_piece is None:
                    moves.append(Move(current_pos, new_pos))
                elif target_piece.color != self._color:
                    moves.append(Move(current_pos, new_pos))  # Capture
                    break
                else:
                    break  # Blocked by own piece
        
        return moves

class Queen(Piece):
    """Queen piece - combines rook and bishop movements"""
    def __init__(self, color: Color):
        super().__init__(color, PieceType.QUEEN)
    
    def get_possible_moves(self, board: 'Board', current_pos: Position) -> List[Move]:
        moves = []
        # All 8 directions (horizontal, vertical, diagonal)
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), 
                     (1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        for dr, dc in directions:
            for distance in range(1, 8):
                new_row = current_pos.row + dr * distance
                new_col = current_pos.col + dc * distance
                
                if not (0 <= new_row <= 7 and 0 <= new_col <= 7):
                    break
                
                new_pos = Position(new_row, new_col)
                target_piece = board.get_piece(new_pos)
                
                if target_piece is None:
                    moves.append(Move(current_pos, new_pos))
                elif target_piece.color != self._color:
                    moves.append(Move(current_pos, new_pos))  # Capture
                    break
                else:
                    break  # Blocked by own piece
        
        return moves

class King(Piece):
    """King piece - moves one square in any direction, with castling support"""
    def __init__(self, color: Color):
        super().__init__(color, PieceType.KING)
    
    def get_possible_moves(self, board: 'Board', current_pos: Position) -> List[Move]:
        moves = []
        # All adjacent squares
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), 
                     (1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        for dr, dc in directions:
            new_row = current_pos.row + dr
            new_col = current_pos.col + dc
            
            if 0 <= new_row <= 7 and 0 <= new_col <= 7:
                new_pos = Position(new_row, new_col)
                target_piece = board.get_piece(new_pos)
                
                if target_piece is None or target_piece.color != self._color:
                    moves.append(Move(current_pos, new_pos))
        
        # Castling moves
        if not self._has_moved and not board.is_in_check(self._color):
            moves.extend(self._get_castling_moves(board, current_pos))
        
        return moves
    
    def _get_castling_moves(self, board: 'Board', current_pos: Position) -> List[Move]:
        """Generate castling moves if conditions are met"""
        castling_moves = []
        row = current_pos.row
        
        # Kingside castling
        rook_pos = Position(row, 7)
        rook = board.get_piece(rook_pos)
        if (rook and isinstance(rook, Rook) and not rook.has_moved and
            self._can_castle_through(board, current_pos, Position(row, 6), Position(row, 5))):
            castling_moves.append(Move(current_pos, Position(row, 6), is_castling=True))
        
        # Queenside castling
        rook_pos = Position(row, 0)
        rook = board.get_piece(rook_pos)
        if (rook and isinstance(rook, Rook) and not rook.has_moved and
            self._can_castle_through(board, current_pos, Position(row, 2), Position(row, 3), Position(row, 1))):
            castling_moves.append(Move(current_pos, Position(row, 2), is_castling=True))
        
        return castling_moves
    
    def _can_castle_through(self, board: 'Board', *positions: Position) -> bool:
        """Check if castling path is clear and not under attack"""
        for pos in positions:
            if board.get_piece(pos) is not None:
                return False
            if board.is_position_under_attack(pos, self._color):
                return False
        return True

class PieceFactory:
    """
    Factory Pattern: Creates piece instances based on type and color
    Impact: Centralizes piece creation logic, making it easy to modify or extend
    """
    @staticmethod
    def create_piece(piece_type: PieceType, color: Color) -> Piece:
        piece_map = {
            PieceType.PAWN: Pawn,
            PieceType.ROOK: Rook,
            PieceType.KNIGHT: Knight,
            PieceType.BISHOP: Bishop,
            PieceType.QUEEN: Queen,
            PieceType.KING: King
        }
        
        if piece_type not in piece_map:
            raise ValueError(f"Unknown piece type: {piece_type}")
        
        return piece_map[piece_type](color)

class Board:
    """
    Represents the chess board state and manages piece positions.
    Design Pattern: Facade - provides simplified interface for board operations
    Design Pattern: Observer - notifies about board state changes
    Impact: Encapsulates board logic, making it easier to maintain and test
    """
    def __init__(self):
        self._board: List[List[Optional[Piece]]] = [[None for _ in range(8)] for _ in range(8)]
        self._move_history: List[Move] = []
        self._captured_pieces: List[Piece] = []
        self._en_passant_target: Optional[Position] = None
        self._half_move_clock = 0  # For 50-move rule
        self._full_move_number = 1
        self._initialize_board()
    
    def _initialize_board(self):
        """Set up the initial chess board position"""
        # Place pawns
        for col in range(8):
            self._board[1][col] = PieceFactory.create_piece(PieceType.PAWN, Color.BLACK)
            self._board[6][col] = PieceFactory.create_piece(PieceType.PAWN, Color.WHITE)
        
        # Place other pieces
        piece_order = [PieceType.ROOK, PieceType.KNIGHT, PieceType.BISHOP, PieceType.QUEEN,
                      PieceType.KING, PieceType.BISHOP, PieceType.KNIGHT, PieceType.ROOK]
        
        for col, piece_type in enumerate(piece_order):
            self._board[0][col] = PieceFactory.create_piece(piece_type, Color.BLACK)
            self._board[7][col] = PieceFactory.create_piece(piece_type, Color.WHITE)
    
    def get_piece(self, position: Position) -> Optional[Piece]:
        """Get piece at given position"""
        return self._board[position.row][position.col]
    
    def set_piece(self, position: Position, piece: Optional[Piece]):
        """Place piece at given position"""
        self._board[position.row][position.col] = piece
    
    def make_move(self, move: Move) -> bool:
        """
        Execute a move on the board if it's legal.
        Returns True if move was successful, False otherwise.
        """
        piece = self.get_piece(move.from_pos)
        if not piece:
            return False
        
        # Validate the move
        if not piece.is_move_valid(self, move):
            return False
        
        # Check if move would leave king in check
        if self._would_be_in_check_after_move(move, piece.color):
            return False
        
        # Execute the move
        self._execute_move(move)
        return True
    
    def _execute_move(self, move: Move):
        """Execute the move without validation (internal method)"""
        piece = self.get_piece(move.from_pos)
        captured_piece = self.get_piece(move.to_pos)
        
        # Type safety: piece should never be None here due to validation in make_move
        if not piece:
            raise RuntimeError("Attempted to execute move with no piece at source position")
        
        # Handle special moves
        if move.is_castling:
            self._execute_castling(move)
        elif move.is_en_passant:
            self._execute_en_passant(move)
        elif move.promotion_piece:
            # Pawn promotion
            promoted_piece = PieceFactory.create_piece(move.promotion_piece, piece.color)
            self.set_piece(move.to_pos, promoted_piece)
            self.set_piece(move.from_pos, None)
            # Mark the promoted piece as having moved
            promoted_piece.mark_as_moved()
        else:
            # Regular move
            self.set_piece(move.to_pos, piece)
            self.set_piece(move.from_pos, None)
            # Update piece state
            piece.mark_as_moved()
        
        # Update game state
        if captured_piece:
            self._captured_pieces.append(captured_piece)
        
        self._move_history.append(move)
        self._update_en_passant_target(move)
        self._update_move_counters(move, captured_piece)
    
    def _execute_castling(self, move: Move):
        """Execute castling move"""
        king = self.get_piece(move.from_pos)
        if not king or not isinstance(king, King):
            raise RuntimeError("No king found for castling move")
            
        row = move.from_pos.row
        
        # Move king
        self.set_piece(move.to_pos, king)
        self.set_piece(move.from_pos, None)
        king.mark_as_moved()
        
        # Move rook
        if move.to_pos.col == 6:  # Kingside
            rook = self.get_piece(Position(row, 7))
            if not rook:
                raise RuntimeError("No rook found for kingside castling")
            self.set_piece(Position(row, 5), rook)
            self.set_piece(Position(row, 7), None)
            rook.mark_as_moved()
        else:  # Queenside
            rook = self.get_piece(Position(row, 0))
            if not rook:
                raise RuntimeError("No rook found for queenside castling")
            self.set_piece(Position(row, 3), rook)
            self.set_piece(Position(row, 0), None)
            rook.mark_as_moved()
    
    def _execute_en_passant(self, move: Move):
        """Execute en passant capture"""
        pawn = self.get_piece(move.from_pos)
        if not pawn:
            raise RuntimeError("No pawn found for en passant move")
            
        self.set_piece(move.to_pos, pawn)
        self.set_piece(move.from_pos, None)
        pawn.mark_as_moved()
        
        # Remove captured pawn
        captured_pawn_pos = Position(move.from_pos.row, move.to_pos.col)
        captured_pawn = self.get_piece(captured_pawn_pos)
        if captured_pawn:
            self._captured_pieces.append(captured_pawn)
        self.set_piece(captured_pawn_pos, None)
    
    def can_en_passant(self, from_pos: Position, to_pos: Position) -> bool:
        """Check if en passant capture is possible"""
        if not self._en_passant_target:
            return False
        
        piece = self.get_piece(from_pos)
        if not piece:
            return False
            
        return (to_pos == self._en_passant_target and
                abs(from_pos.col - to_pos.col) == 1 and
                from_pos.row == to_pos.row + (1 if piece.color == Color.WHITE else -1))
    
    def is_in_check(self, color: Color) -> bool:
        """Check if the king of given color is in check"""
        king_pos = self._find_king(color)
        if not king_pos:
            return False
        
        return self.is_position_under_attack(king_pos, color)
    
    def is_position_under_attack(self, position: Position, by_color: Color) -> bool:
        """Check if a position is under attack by pieces of given color"""
        opponent_color = Color.BLACK if by_color == Color.WHITE else Color.WHITE
        
        for row in range(8):
            for col in range(8):
                piece = self._board[row][col]
                if piece and piece.color == opponent_color:
                    possible_moves = piece.get_possible_moves(self, Position(row, col))
                    for move in possible_moves:
                        if move.to_pos == position:
                            return True
        return False
    
    def _find_king(self, color: Color) -> Optional[Position]:
        """Find the king of given color"""
        for row in range(8):
            for col in range(8):
                piece = self._board[row][col]
                if piece and isinstance(piece, King) and piece.color == color:
                    return Position(row, col)
        return None
    
    def _would_be_in_check_after_move(self, move: Move, color: Color) -> bool:
        """Check if making this move would leave the king in check"""
        # Make a copy of the board and simulate the move
        board_copy = copy.deepcopy(self)
        board_copy._execute_move(move)
        return board_copy.is_in_check(color)
    
    def get_all_legal_moves(self, color: Color) -> List[Move]:
        """Get all legal moves for pieces of given color"""
        legal_moves = []
        
        for row in range(8):
            for col in range(8):
                piece = self._board[row][col]
                if piece and piece.color == color:
                    pos = Position(row, col)
                    possible_moves = piece.get_possible_moves(self, pos)
                    
                    for move in possible_moves:
                        if not self._would_be_in_check_after_move(move, color):
                            legal_moves.append(move)
        
        return legal_moves
    
    def is_checkmate(self, color: Color) -> bool:
        """Check if the given color is in checkmate"""
        return self.is_in_check(color) and len(self.get_all_legal_moves(color)) == 0
    
    def is_stalemate(self, color: Color) -> bool:
        """Check if the given color is in stalemate"""
        return not self.is_in_check(color) and len(self.get_all_legal_moves(color)) == 0
    
    def _update_en_passant_target(self, move: Move):
        """Update en passant target after a move"""
        piece = self.get_piece(move.to_pos)
        
        # Reset en passant target
        self._en_passant_target = None
        
        # Set en passant target if pawn moved two squares
        if (piece and isinstance(piece, Pawn) and 
            abs(move.from_pos.row - move.to_pos.row) == 2):
            target_row = (move.from_pos.row + move.to_pos.row) // 2
            self._en_passant_target = Position(target_row, move.to_pos.col)
    
    def _update_move_counters(self, move: Move, captured_piece: Optional[Piece]):
        """Update half-move clock and full-move number"""
        piece = self.get_piece(move.to_pos)
        
        # Type safety check
        if not piece:
            return
            
        # Reset half-move clock on pawn move or capture
        if isinstance(piece, Pawn) or captured_piece:
            self._half_move_clock = 0
        else:
            self._half_move_clock += 1
        
        # Increment full-move number after Black's move
        if piece.color == Color.BLACK:
            self._full_move_number += 1
    
    def display(self):
        """Display the current board state"""
        print("   a b c d e f g h")
        print("  +-+-+-+-+-+-+-+-+")
        
        for row in range(8):
            print(f"{8-row} |", end="")
            for col in range(8):
                piece = self._board[row][col]
                if piece:
                    print(f"{piece}|", end="")
                else:
                    print(" |", end="")
            print(f" {8-row}")
            print("  +-+-+-+-+-+-+-+-+")
        
        print("   a b c d e f g h")

class GameState(Enum):
    """Enumeration for different game states"""
    ONGOING = "Ongoing"
    CHECK = "Check"
    CHECKMATE = "Checkmate"
    STALEMATE = "Stalemate"
    DRAW = "Draw"

class ChessGame:
    """
    Main game controller that manages the chess game flow.
    Design Pattern: Facade - provides simplified interface for game operations
    Design Pattern: State - manages different game states
    Impact: Centralizes game logic and provides clean API for external systems
    """
    def __init__(self):
        self._board = Board()
        self._current_player = Color.WHITE
        self._game_state = GameState.ONGOING
        self._move_count = 0
    
    @property
    def current_player(self) -> Color:
        return self._current_player
    
    @property
    def game_state(self) -> GameState:
        return self._game_state
    
    @property
    def board(self) -> Board:
        return self._board
    
    def make_move(self, move: Move) -> bool:
        """
        Attempt to make a move in the game.
        Returns True if successful, False otherwise.
        """
        if self._game_state != GameState.ONGOING and self._game_state != GameState.CHECK:
            return False
        
        piece = self._board.get_piece(move.from_pos)
        if not piece or piece.color != self._current_player:
            return False
        
        if self._board.make_move(move):
            self._move_count += 1
            self._switch_player()
            self._update_game_state()
            return True
        
        return False
    
    def make_move_from_algebraic(self, from_notation: str, to_notation: str, 
                                promotion: Optional[str] = None) -> bool:
        """Make a move using algebraic notation"""
        try:
            from_pos = Position.from_algebraic(from_notation)
            to_pos = Position.from_algebraic(to_notation)
            
            promotion_piece = None
            if promotion:
                promotion_map = {'Q': PieceType.QUEEN, 'R': PieceType.ROOK, 
                               'B': PieceType.BISHOP, 'N': PieceType.KNIGHT}
                promotion_piece = promotion_map.get(promotion.upper())
            
            move = Move(from_pos, to_pos, promotion_piece)
            return self.make_move(move)
        
        except (ValueError, KeyError):
            return False
    
    def get_legal_moves(self) -> List[Move]:
        """Get all legal moves for the current player"""
        return self._board.get_all_legal_moves(self._current_player)
    
    def _switch_player(self):
        """Switch to the other player"""
        self._current_player = Color.BLACK if self._current_player == Color.WHITE else Color.WHITE
    
    def _update_game_state(self):
        """Update the game state after a move"""
        if self._board.is_checkmate(self._current_player):
            self._game_state = GameState.CHECKMATE
        elif self._board.is_stalemate(self._current_player):
            self._game_state = GameState.STALEMATE
        elif self._board.is_in_check(self._current_player):
            self._game_state = GameState.CHECK
        elif self._is_draw():
            self._game_state = GameState.DRAW
        else:
            self._game_state = GameState.ONGOING
    
    def _is_draw(self) -> bool:
        """Check for various draw conditions"""
        # 50-move rule, insufficient material, etc.
        # Implementation can be extended based on requirements
        return self._board._half_move_clock >= 100  # 50 full moves
    
    def display_board(self):
        """Display the current board"""
        self._board.display()
        print(f"\nCurrent player: {self._current_player}")
        print(f"Game state: {self._game_state.value}")
    
    def get_game_status(self) -> str:
        """Get a human-readable game status"""
        if self._game_state == GameState.CHECKMATE:
            winner = Color.BLACK if self._current_player == Color.WHITE else Color.WHITE
            return f"Checkmate! {winner.value} wins!"
        elif self._game_state == GameState.STALEMATE:
            return "Stalemate! The game is a draw."
        elif self._game_state == GameState.CHECK:
            return f"{self._current_player.value} is in check!"
        elif self._game_state == GameState.DRAW:
            return "The game is a draw."
        else:
            return f"{self._current_player.value}'s turn."

# Example usage and testing
if __name__ == "__main__":
    # Create a new chess game
    game = ChessGame()
    
    # Display initial board
    print("Initial Chess Board:")
    game.display_board()
    
    # Example moves
    print("\nMaking some example moves:")
    
    # 1. e4
    if game.make_move_from_algebraic("e2", "e4"):
        print("Move: e2-e4 successful")
        game.display_board()
    
    # 1... e5
    if game.make_move_from_algebraic("e7", "e5"):
        print("\nMove: e7-e5 successful")
        game.display_board()
    
    # 2. Nf3
    if game.make_move_from_algebraic("g1", "f3"):
        print("\nMove: g1-f3 successful")
        game.display_board()
    
    print(f"\nGame Status: {game.get_game_status()}")
    print(f"Legal moves for {game.current_player}: {len(game.get_legal_moves())}")