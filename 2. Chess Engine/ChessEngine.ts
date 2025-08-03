/**
 * Chess Game Implementation in TypeScript
 *
 * Design Patterns Used:
 * - Strategy Pattern: Each piece type implements its own movement strategy
 * - Factory Pattern: PieceFactory centralizes piece creation logic
 * - Template Method Pattern: Base Piece class defines common behavior
 * - Facade Pattern: ChessGame provides simplified interface
 * - Value Object Pattern: Position and Move are immutable objects
 * - State Pattern: GameState enum manages different game states
 */

// Enums
enum PieceType {
  PAWN = "Pawn",
  ROOK = "Rook",
  KNIGHT = "Knight",
  BISHOP = "Bishop",
  QUEEN = "Queen",
  KING = "King",
}

enum Color {
  WHITE = "White",
  BLACK = "Black",
}

enum GameState {
  ONGOING = "Ongoing",
  CHECK = "Check",
  CHECKMATE = "Checkmate",
  STALEMATE = "Stalemate",
  DRAW = "Draw",
}

// Value Objects
class Position {
  private readonly _row: number;
  private readonly _col: number;

  constructor(row: number, col: number) {
    if (row < 0 || row > 7 || col < 0 || col > 7) {
      throw new Error(
        `Invalid position: (${row}, ${col}). Must be between 0-7`
      );
    }
    this._row = row;
    this._col = col;
  }

  get row(): number {
    return this._row;
  }

  get col(): number {
    return this._col;
  }

  toAlgebraic(): string {
    return String.fromCharCode(97 + this._col) + (8 - this._row);
  }

  static fromAlgebraic(notation: string): Position {
    if (notation.length !== 2) {
      throw new Error(`Invalid algebraic notation: ${notation}`);
    }
    const col = notation.charCodeAt(0) - 97;
    const row = 8 - parseInt(notation[1], 10);
    return new Position(row, col);
  }

  equals(other: Position): boolean {
    return this._row === other._row && this._col === other._col;
  }

  toString(): string {
    return this.toAlgebraic();
  }
}

class Move {
  private readonly _fromPos: Position;
  private readonly _toPos: Position;
  private readonly _promotionPiece?: PieceType;
  private readonly _isCastling: boolean;
  private readonly _isEnPassant: boolean;

  constructor(
    fromPos: Position,
    toPos: Position,
    promotionPiece?: PieceType,
    isCastling: boolean = false,
    isEnPassant: boolean = false
  ) {
    this._fromPos = fromPos;
    this._toPos = toPos;
    this._promotionPiece = promotionPiece;
    this._isCastling = isCastling;
    this._isEnPassant = isEnPassant;
  }

  get fromPos(): Position {
    return this._fromPos;
  }

  get toPos(): Position {
    return this._toPos;
  }

  get promotionPiece(): PieceType | undefined {
    return this._promotionPiece;
  }

  get isCastling(): boolean {
    return this._isCastling;
  }

  get isEnPassant(): boolean {
    return this._isEnPassant;
  }

  equals(other: Move): boolean {
    return (
      this._fromPos.equals(other._fromPos) &&
      this._toPos.equals(other._toPos) &&
      this._promotionPiece === other._promotionPiece &&
      this._isCastling === other._isCastling &&
      this._isEnPassant === other._isEnPassant
    );
  }

  toString(): string {
    let moveStr = `${this._fromPos}${this._toPos}`;
    if (this._promotionPiece) {
      moveStr += `=${this._promotionPiece[0]}`;
    }
    return moveStr;
  }
}

// Abstract Base Piece Class
abstract class Piece {
  protected _color: Color;
  protected _pieceType: PieceType;
  protected _hasMoved: boolean = false;

  constructor(color: Color, pieceType: PieceType) {
    this._color = color;
    this._pieceType = pieceType;
  }

  get color(): Color {
    return this._color;
  }

  get pieceType(): PieceType {
    return this._pieceType;
  }

  get hasMoved(): boolean {
    return this._hasMoved;
  }

  markAsMoved(): void {
    this._hasMoved = true;
  }

  abstract getPossibleMoves(board: Board, currentPos: Position): Move[];

  isMoveValid(board: Board, move: Move): boolean {
    const possibleMoves = this.getPossibleMoves(board, move.fromPos);
    return possibleMoves.some((m) => m.equals(move));
  }

  toString(): string {
    const colorPrefix = this._color === Color.WHITE ? "W" : "B";
    return `${colorPrefix}${this._pieceType[0]}`;
  }
}

// Piece Implementations
class Pawn extends Piece {
  constructor(color: Color) {
    super(color, PieceType.PAWN);
  }

  getPossibleMoves(board: Board, currentPos: Position): Move[] {
    const moves: Move[] = [];
    const direction = this._color === Color.WHITE ? -1 : 1;

    // Forward moves
    const newRow = currentPos.row + direction;
    if (newRow >= 0 && newRow <= 7) {
      const newPos = new Position(newRow, currentPos.col);

      // One square forward
      if (!board.getPiece(newPos)) {
        // Check for promotion
        if (newRow === 0 || newRow === 7) {
          const promotionPieces = [
            PieceType.QUEEN,
            PieceType.ROOK,
            PieceType.BISHOP,
            PieceType.KNIGHT,
          ];
          promotionPieces.forEach((pieceType) => {
            moves.push(new Move(currentPos, newPos, pieceType));
          });
        } else {
          moves.push(new Move(currentPos, newPos));
        }

        // Two squares forward (initial move)
        if (!this._hasMoved) {
          const twoForward = new Position(newRow + direction, currentPos.col);
          if (
            twoForward.row >= 0 &&
            twoForward.row <= 7 &&
            !board.getPiece(twoForward)
          ) {
            moves.push(new Move(currentPos, twoForward));
          }
        }
      }
    }

    // Diagonal captures
    [-1, 1].forEach((colOffset) => {
      const newCol = currentPos.col + colOffset;
      if (newCol >= 0 && newCol <= 7 && newRow >= 0 && newRow <= 7) {
        const capturePos = new Position(newRow, newCol);
        const targetPiece = board.getPiece(capturePos);

        // Regular capture
        if (targetPiece && targetPiece.color !== this._color) {
          if (newRow === 0 || newRow === 7) {
            // Promotion capture
            const promotionPieces = [
              PieceType.QUEEN,
              PieceType.ROOK,
              PieceType.BISHOP,
              PieceType.KNIGHT,
            ];
            promotionPieces.forEach((pieceType) => {
              moves.push(new Move(currentPos, capturePos, pieceType));
            });
          } else {
            moves.push(new Move(currentPos, capturePos));
          }
        }
        // En passant capture
        else if (board.canEnPassant(currentPos, capturePos)) {
          moves.push(new Move(currentPos, capturePos, undefined, false, true));
        }
      }
    });

    return moves;
  }
}

class Rook extends Piece {
  constructor(color: Color) {
    super(color, PieceType.ROOK);
  }

  getPossibleMoves(board: Board, currentPos: Position): Move[] {
    const moves: Move[] = [];
    const directions = [
      [0, 1],
      [0, -1],
      [1, 0],
      [-1, 0],
    ];

    directions.forEach(([dr, dc]) => {
      for (let distance = 1; distance < 8; distance++) {
        const newRow = currentPos.row + dr * distance;
        const newCol = currentPos.col + dc * distance;

        if (newRow < 0 || newRow > 7 || newCol < 0 || newCol > 7) {
          break;
        }

        const newPos = new Position(newRow, newCol);
        const targetPiece = board.getPiece(newPos);

        if (!targetPiece) {
          moves.push(new Move(currentPos, newPos));
        } else if (targetPiece.color !== this._color) {
          moves.push(new Move(currentPos, newPos)); // Capture
          break;
        } else {
          break; // Blocked by own piece
        }
      }
    });

    return moves;
  }
}

class Knight extends Piece {
  constructor(color: Color) {
    super(color, PieceType.KNIGHT);
  }

  getPossibleMoves(board: Board, currentPos: Position): Move[] {
    const moves: Move[] = [];
    const knightMoves = [
      [-2, -1],
      [-2, 1],
      [-1, -2],
      [-1, 2],
      [1, -2],
      [1, 2],
      [2, -1],
      [2, 1],
    ];

    knightMoves.forEach(([dr, dc]) => {
      const newRow = currentPos.row + dr;
      const newCol = currentPos.col + dc;

      if (newRow >= 0 && newRow <= 7 && newCol >= 0 && newCol <= 7) {
        const newPos = new Position(newRow, newCol);
        const targetPiece = board.getPiece(newPos);

        if (!targetPiece || targetPiece.color !== this._color) {
          moves.push(new Move(currentPos, newPos));
        }
      }
    });

    return moves;
  }
}

class Bishop extends Piece {
  constructor(color: Color) {
    super(color, PieceType.BISHOP);
  }

  getPossibleMoves(board: Board, currentPos: Position): Move[] {
    const moves: Move[] = [];
    const directions = [
      [1, 1],
      [1, -1],
      [-1, 1],
      [-1, -1],
    ];

    directions.forEach(([dr, dc]) => {
      for (let distance = 1; distance < 8; distance++) {
        const newRow = currentPos.row + dr * distance;
        const newCol = currentPos.col + dc * distance;

        if (newRow < 0 || newRow > 7 || newCol < 0 || newCol > 7) {
          break;
        }

        const newPos = new Position(newRow, newCol);
        const targetPiece = board.getPiece(newPos);

        if (!targetPiece) {
          moves.push(new Move(currentPos, newPos));
        } else if (targetPiece.color !== this._color) {
          moves.push(new Move(currentPos, newPos)); // Capture
          break;
        } else {
          break; // Blocked by own piece
        }
      }
    });

    return moves;
  }
}

class Queen extends Piece {
  constructor(color: Color) {
    super(color, PieceType.QUEEN);
  }

  getPossibleMoves(board: Board, currentPos: Position): Move[] {
    const moves: Move[] = [];
    const directions = [
      [0, 1],
      [0, -1],
      [1, 0],
      [-1, 0],
      [1, 1],
      [1, -1],
      [-1, 1],
      [-1, -1],
    ];

    directions.forEach(([dr, dc]) => {
      for (let distance = 1; distance < 8; distance++) {
        const newRow = currentPos.row + dr * distance;
        const newCol = currentPos.col + dc * distance;

        if (newRow < 0 || newRow > 7 || newCol < 0 || newCol > 7) {
          break;
        }

        const newPos = new Position(newRow, newCol);
        const targetPiece = board.getPiece(newPos);

        if (!targetPiece) {
          moves.push(new Move(currentPos, newPos));
        } else if (targetPiece.color !== this._color) {
          moves.push(new Move(currentPos, newPos)); // Capture
          break;
        } else {
          break; // Blocked by own piece
        }
      }
    });

    return moves;
  }
}

class King extends Piece {
  constructor(color: Color) {
    super(color, PieceType.KING);
  }

  getPossibleMoves(board: Board, currentPos: Position): Move[] {
    const moves: Move[] = [];
    const directions = [
      [0, 1],
      [0, -1],
      [1, 0],
      [-1, 0],
      [1, 1],
      [1, -1],
      [-1, 1],
      [-1, -1],
    ];

    // Adjacent squares
    directions.forEach(([dr, dc]) => {
      const newRow = currentPos.row + dr;
      const newCol = currentPos.col + dc;

      if (newRow >= 0 && newRow <= 7 && newCol >= 0 && newCol <= 7) {
        const newPos = new Position(newRow, newCol);
        const targetPiece = board.getPiece(newPos);

        if (!targetPiece || targetPiece.color !== this._color) {
          moves.push(new Move(currentPos, newPos));
        }
      }
    });

    // Castling moves
    if (!this._hasMoved && !board.isInCheck(this._color)) {
      moves.push(...this.getCastlingMoves(board, currentPos));
    }

    return moves;
  }

  private getCastlingMoves(board: Board, currentPos: Position): Move[] {
    const castlingMoves: Move[] = [];
    const row = currentPos.row;

    // Kingside castling
    const kingsideRookPos = new Position(row, 7);
    const kingsideRook = board.getPiece(kingsideRookPos);
    if (
      kingsideRook instanceof Rook &&
      !kingsideRook.hasMoved &&
      this.canCastleThrough(
        board,
        currentPos,
        new Position(row, 6),
        new Position(row, 5)
      )
    ) {
      castlingMoves.push(
        new Move(currentPos, new Position(row, 6), undefined, true)
      );
    }

    // queenSide castling
    const queenSideRookPos = new Position(row, 0);
    const queenSideRook = board.getPiece(queenSideRookPos);
    if (
      queenSideRook instanceof Rook &&
      !queenSideRook.hasMoved &&
      this.canCastleThrough(
        board,
        currentPos,
        new Position(row, 2),
        new Position(row, 3),
        new Position(row, 1)
      )
    ) {
      castlingMoves.push(
        new Move(currentPos, new Position(row, 2), undefined, true)
      );
    }

    return castlingMoves;
  }

  private canCastleThrough(board: Board, ...positions: Position[]): boolean {
    return positions.every(
      (pos) =>
        !board.getPiece(pos) && !board.isPositionUnderAttack(pos, this._color)
    );
  }
}

// Factory Pattern
class PieceFactory {
  static createPiece(pieceType: PieceType, color: Color): Piece {
    switch (pieceType) {
      case PieceType.PAWN:
        return new Pawn(color);
      case PieceType.ROOK:
        return new Rook(color);
      case PieceType.KNIGHT:
        return new Knight(color);
      case PieceType.BISHOP:
        return new Bishop(color);
      case PieceType.QUEEN:
        return new Queen(color);
      case PieceType.KING:
        return new King(color);
      default:
        throw new Error(`Unknown piece type: ${pieceType}`);
    }
  }
}

// Board Class
class Board {
  private _board: (Piece | null)[][];
  private _moveHistory: Move[] = [];
  private _capturedPieces: Piece[] = [];
  private _enPassantTarget: Position | null = null;
  private _halfMoveClock: number = 0;
  private _fullMoveNumber: number = 1;

  constructor() {
    this._board = Array(8)
      .fill(null)
      .map(() => Array(8).fill(null));
    this.initializeBoard();
  }

  private initializeBoard(): void {
    // Place pawns
    for (let col = 0; col < 8; col++) {
      this._board[1][col] = PieceFactory.createPiece(
        PieceType.PAWN,
        Color.BLACK
      );
      this._board[6][col] = PieceFactory.createPiece(
        PieceType.PAWN,
        Color.WHITE
      );
    }

    // Place other pieces
    const pieceOrder = [
      PieceType.ROOK,
      PieceType.KNIGHT,
      PieceType.BISHOP,
      PieceType.QUEEN,
      PieceType.KING,
      PieceType.BISHOP,
      PieceType.KNIGHT,
      PieceType.ROOK,
    ];

    pieceOrder.forEach((pieceType, col) => {
      this._board[0][col] = PieceFactory.createPiece(pieceType, Color.BLACK);
      this._board[7][col] = PieceFactory.createPiece(pieceType, Color.WHITE);
    });
  }

  getPiece(position: Position): Piece | null {
    return this._board[position.row][position.col];
  }

  setPiece(position: Position, piece: Piece | null): void {
    this._board[position.row][position.col] = piece;
  }

  makeMove(move: Move): boolean {
    const piece = this.getPiece(move.fromPos);
    if (!piece) {
      return false;
    }

    // Validate the move
    if (!piece.isMoveValid(this, move)) {
      return false;
    }

    // Check if move would leave king in check
    if (this.wouldBeInCheckAfterMove(move, piece.color)) {
      return false;
    }

    // Execute the move
    this.executeMove(move);
    return true;
  }

  private executeMove(move: Move): void {
    const piece = this.getPiece(move.fromPos);
    const capturedPiece = this.getPiece(move.toPos);

    if (!piece) {
      throw new Error(
        "Attempted to execute move with no piece at source position"
      );
    }

    // Handle special moves
    if (move.isCastling) {
      this.executeCastling(move);
    } else if (move.isEnPassant) {
      this.executeEnPassant(move);
    } else if (move.promotionPiece) {
      // Pawn promotion
      const promotedPiece = PieceFactory.createPiece(
        move.promotionPiece,
        piece.color
      );
      this.setPiece(move.toPos, promotedPiece);
      this.setPiece(move.fromPos, null);
      promotedPiece.markAsMoved();
    } else {
      // Regular move
      this.setPiece(move.toPos, piece);
      this.setPiece(move.fromPos, null);
      piece.markAsMoved();
    }

    // Update game state
    if (capturedPiece) {
      this._capturedPieces.push(capturedPiece);
    }

    this._moveHistory.push(move);
    this.updateEnPassantTarget(move);
    this.updateMoveCounters(move, capturedPiece);
  }

  private executeCastling(move: Move): void {
    const king = this.getPiece(move.fromPos);
    if (!king) {
      throw new Error("No king found for castling move");
    }

    const row = move.fromPos.row;

    // Move king
    this.setPiece(move.toPos, king);
    this.setPiece(move.fromPos, null);
    king.markAsMoved();

    // Move rook
    if (move.toPos.col === 6) {
      // Kingside
      const rook = this.getPiece(new Position(row, 7));
      if (!rook) {
        throw new Error("No rook found for kingside castling");
      }
      this.setPiece(new Position(row, 5), rook);
      this.setPiece(new Position(row, 7), null);
      rook.markAsMoved();
    } else {
      // queenSide
      const rook = this.getPiece(new Position(row, 0));
      if (!rook) {
        throw new Error("No rook found for queenSide castling");
      }
      this.setPiece(new Position(row, 3), rook);
      this.setPiece(new Position(row, 0), null);
      rook.markAsMoved();
    }
  }

  private executeEnPassant(move: Move): void {
    const pawn = this.getPiece(move.fromPos);
    if (!pawn) {
      throw new Error("No pawn found for en passant move");
    }

    this.setPiece(move.toPos, pawn);
    this.setPiece(move.fromPos, null);
    pawn.markAsMoved();

    // Remove captured pawn
    const capturedPawnPos = new Position(move.fromPos.row, move.toPos.col);
    const capturedPawn = this.getPiece(capturedPawnPos);
    if (capturedPawn) {
      this._capturedPieces.push(capturedPawn);
    }
    this.setPiece(capturedPawnPos, null);
  }

  canEnPassant(fromPos: Position, toPos: Position): boolean {
    if (!this._enPassantTarget) {
      return false;
    }

    const piece = this.getPiece(fromPos);
    if (!piece) {
      return false;
    }

    return (
      toPos.equals(this._enPassantTarget) &&
      Math.abs(fromPos.col - toPos.col) === 1 &&
      fromPos.row === toPos.row + (piece.color === Color.WHITE ? 1 : -1)
    );
  }

  isInCheck(color: Color): boolean {
    const kingPos = this.findKing(color);
    if (!kingPos) {
      return false;
    }

    return this.isPositionUnderAttack(kingPos, color);
  }

  isPositionUnderAttack(position: Position, byColor: Color): boolean {
    const opponentColor = byColor === Color.WHITE ? Color.BLACK : Color.WHITE;

    for (let row = 0; row < 8; row++) {
      for (let col = 0; col < 8; col++) {
        const piece = this._board[row][col];
        if (piece && piece.color === opponentColor) {
          const possibleMoves = piece.getPossibleMoves(
            this,
            new Position(row, col)
          );
          if (possibleMoves.some((move) => move.toPos.equals(position))) {
            return true;
          }
        }
      }
    }

    return false;
  }

  private findKing(color: Color): Position | null {
    for (let row = 0; row < 8; row++) {
      for (let col = 0; col < 8; col++) {
        const piece = this._board[row][col];
        if (piece instanceof King && piece.color === color) {
          return new Position(row, col);
        }
      }
    }
    return null;
  }

  private wouldBeInCheckAfterMove(move: Move, color: Color): boolean {
    // Create a deep copy and simulate the move
    const boardCopy = this.deepCopy();
    boardCopy.executeMove(move);
    return boardCopy.isInCheck(color);
  }

  private deepCopy(): Board {
    const copy = new Board();
    copy._board = this._board.map((row) => [...row]);
    copy._moveHistory = [...this._moveHistory];
    copy._capturedPieces = [...this._capturedPieces];
    copy._enPassantTarget = this._enPassantTarget;
    copy._halfMoveClock = this._halfMoveClock;
    copy._fullMoveNumber = this._fullMoveNumber;
    return copy;
  }

  getAllLegalMoves(color: Color): Move[] {
    const legalMoves: Move[] = [];

    for (let row = 0; row < 8; row++) {
      for (let col = 0; col < 8; col++) {
        const piece = this._board[row][col];
        if (piece && piece.color === color) {
          const pos = new Position(row, col);
          const possibleMoves = piece.getPossibleMoves(this, pos);

          possibleMoves.forEach((move) => {
            if (!this.wouldBeInCheckAfterMove(move, color)) {
              legalMoves.push(move);
            }
          });
        }
      }
    }

    return legalMoves;
  }

  isCheckmate(color: Color): boolean {
    return this.isInCheck(color) && this.getAllLegalMoves(color).length === 0;
  }

  isStalemate(color: Color): boolean {
    return !this.isInCheck(color) && this.getAllLegalMoves(color).length === 0;
  }

  private updateEnPassantTarget(move: Move): void {
    const piece = this.getPiece(move.toPos);

    // Reset en passant target
    this._enPassantTarget = null;

    // Set en passant target if pawn moved two squares
    if (
      piece instanceof Pawn &&
      Math.abs(move.fromPos.row - move.toPos.row) === 2
    ) {
      const targetRow = Math.floor((move.fromPos.row + move.toPos.row) / 2);
      this._enPassantTarget = new Position(targetRow, move.toPos.col);
    }
  }

  private updateMoveCounters(move: Move, capturedPiece: Piece | null): void {
    const piece = this.getPiece(move.toPos);

    if (!piece) {
      return;
    }

    // Reset half-move clock on pawn move or capture
    if (piece instanceof Pawn || capturedPiece) {
      this._halfMoveClock = 0;
    } else {
      this._halfMoveClock += 1;
    }

    // Increment full-move number after Black's move
    if (piece.color === Color.BLACK) {
      this._fullMoveNumber += 1;
    }
  }

  get halfMoveClock(): number {
    return this._halfMoveClock;
  }

  display(): void {
    console.log("   a b c d e f g h");
    console.log("  +-+-+-+-+-+-+-+-+");

    for (let row = 0; row < 8; row++) {
      let rowStr = `${8 - row} |`;
      for (let col = 0; col < 8; col++) {
        const piece = this._board[row][col];
        rowStr += piece ? `${piece}|` : " |";
      }
      rowStr += ` ${8 - row}`;
      console.log(rowStr);
      console.log("  +-+-+-+-+-+-+-+-+");
    }

    console.log("   a b c d e f g h");
  }
}

// Main Game Controller
class ChessGame {
  private _board: Board;
  private _currentPlayer: Color;
  private _gameState: GameState;
  private _moveCount: number;

  constructor() {
    this._board = new Board();
    this._currentPlayer = Color.WHITE;
    this._gameState = GameState.ONGOING;
    this._moveCount = 0;
  }

  get currentPlayer(): Color {
    return this._currentPlayer;
  }

  get gameState(): GameState {
    return this._gameState;
  }

  get board(): Board {
    return this._board;
  }

  makeMove(move: Move): boolean {
    if (
      this._gameState !== GameState.ONGOING &&
      this._gameState !== GameState.CHECK
    ) {
      return false;
    }

    const piece = this._board.getPiece(move.fromPos);
    if (!piece || piece.color !== this._currentPlayer) {
      return false;
    }

    if (this._board.makeMove(move)) {
      this._moveCount += 1;
      this.switchPlayer();
      this.updateGameState();
      return true;
    }

    return false;
  }

  makeMoveFromAlgebraic(
    fromNotation: string,
    toNotation: string,
    promotion?: string
  ): boolean {
    try {
      const fromPos = Position.fromAlgebraic(fromNotation);
      const toPos = Position.fromAlgebraic(toNotation);

      let promotionPiece: PieceType | undefined;
      if (promotion) {
        const promotionMap: Record<string, PieceType> = {
          Q: PieceType.QUEEN,
          R: PieceType.ROOK,
          B: PieceType.BISHOP,
          N: PieceType.KNIGHT,
        };
        promotionPiece = promotionMap[promotion.toUpperCase()];
      }

      const move = new Move(fromPos, toPos, promotionPiece);
      return this.makeMove(move);
    } catch (error) {
      return false;
    }
  }

  getLegalMoves(): Move[] {
    return this._board.getAllLegalMoves(this._currentPlayer);
  }

  private switchPlayer(): void {
    this._currentPlayer =
      this._currentPlayer === Color.WHITE ? Color.BLACK : Color.WHITE;
  }

  private updateGameState(): void {
    if (this._board.isCheckmate(this._currentPlayer)) {
      this._gameState = GameState.CHECKMATE;
    } else if (this._board.isStalemate(this._currentPlayer)) {
      this._gameState = GameState.STALEMATE;
    } else if (this._board.isInCheck(this._currentPlayer)) {
      this._gameState = GameState.CHECK;
    } else if (this.isDraw()) {
      this._gameState = GameState.DRAW;
    } else {
      this._gameState = GameState.ONGOING;
    }
  }

  private isDraw(): boolean {
    // 50-move rule, insufficient material, etc.
    // Implementation can be extended based on requirements
    return this._board.halfMoveClock >= 100; // 50 full moves
  }

  displayBoard(): void {
    this._board.display();
    console.log(`\nCurrent player: ${this._currentPlayer}`);
    console.log(`Game state: ${this._gameState}`);
  }

  getGameStatus(): string {
    switch (this._gameState) {
      case GameState.CHECKMATE:
        const winner =
          this._currentPlayer === Color.WHITE ? Color.BLACK : Color.WHITE;
        return `Checkmate! ${winner} wins!`;
      case GameState.STALEMATE:
        return "Stalemate! The game is a draw.";
      case GameState.CHECK:
        return `${this._currentPlayer} is in check!`;
      case GameState.DRAW:
        return "The game is a draw.";
      default:
        return `${this._currentPlayer}'s turn.`;
    }
  }
}

// Example usage and testing
function runChessGameExample(): void {
  // Create a new chess game
  const game = new ChessGame();

  // Display initial board
  console.log("Initial Chess Board:");
  game.displayBoard();

  // Example moves
  console.log("\nMaking some example moves:");

  // 1. e4
  if (game.makeMoveFromAlgebraic("e2", "e4")) {
    console.log("Move: e2-e4 successful");
    game.displayBoard();
  }

  // 1... e5
  if (game.makeMoveFromAlgebraic("e7", "e5")) {
    console.log("\nMove: e7-e5 successful");
    game.displayBoard();
  }

  // 2. Nf3
  if (game.makeMoveFromAlgebraic("g1", "f3")) {
    console.log("\nMove: g1-f3 successful");
    game.displayBoard();
  }

  console.log(`\nGame Status: ${game.getGameStatus()}`);
  console.log(
    `Legal moves for ${game.currentPlayer}: ${game.getLegalMoves().length}`
  );
}

// Type definitions for better IntelliSense and type safety
interface ChessGameInterface {
  readonly currentPlayer: Color;
  readonly gameState: GameState;
  readonly board: Board;
  makeMove(move: Move): boolean;
  makeMoveFromAlgebraic(from: string, to: string, promotion?: string): boolean;
  getLegalMoves(): Move[];
  displayBoard(): void;
  getGameStatus(): string;
}

interface BoardInterface {
  getPiece(position: Position): Piece | null;
  setPiece(position: Position, piece: Piece | null): void;
  makeMove(move: Move): boolean;
  getAllLegalMoves(color: Color): Move[];
  isInCheck(color: Color): boolean;
  isCheckmate(color: Color): boolean;
  isStalemate(color: Color): boolean;
  isPositionUnderAttack(position: Position, byColor: Color): boolean;
  canEnPassant(fromPos: Position, toPos: Position): boolean;
  display(): void;
}

// Export main classes for use in other modules
export {
  ChessGame,
  Board,
  Piece,
  Pawn,
  Rook,
  Knight,
  Bishop,
  Queen,
  King,
  Position,
  Move,
  PieceFactory,
  PieceType,
  Color,
  GameState,
  ChessGameInterface,
  BoardInterface,
  runChessGameExample,
};
// Run the example game
