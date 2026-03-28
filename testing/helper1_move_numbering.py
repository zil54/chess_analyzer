# tests/helper1.py

def add_move_numbers(moves: str, starting_move: int = 1, black_to_move: bool = False) -> str:
    """
    Convert a space-separated move list into a numbered PGN-like string.

    Examples:
        add_move_numbers("e4 e5 Nf3 Nc6") -> "1. e4 e5 2. Nf3 Nc6"
        add_move_numbers("e5 Nf3 Nc6", black_to_move=True) -> "1... e5 2. Nf3 Nc6"
    """
    tokens = moves.strip().split()
    numbered = []
    move_num = starting_move

    i = 0
    if black_to_move:
        # First token is Black's move
        black = tokens[0]
        numbered.append(f"{move_num}... {black}")
        i = 1
        move_num += 1

    # Process remaining moves in White/Black pairs
    while i < len(tokens):
        white = tokens[i]
        black = tokens[i + 1] if i + 1 < len(tokens) else ""
        if black:
            numbered.append(f"{move_num}. {white} {black}")
        else:
            numbered.append(f"{move_num}. {white}")
        move_num += 1
        i += 2

    return " ".join(numbered)