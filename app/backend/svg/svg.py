def piece_unicode(piece: str) -> str:
    mapping = {
        "K": "♔", "Q": "♕", "R": "♖", "B": "♗", "N": "♘", "P": "♙",
        "k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟"
    }
    return mapping.get(piece, "")

def piece_icon(piece: str) -> str:
    color = "w" if piece.isupper() else "b"
    name = piece.upper()
    return f"/static/pieces/{color}{name}.svg"

def generate_board_svg(fen: str) -> str:
    square_size = 52
    board_size = 8 * square_size
    light_color = "#f0d9b5"
    dark_color = "#b58863"

    rows = fen.split(" ")[0].split("/")
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{board_size}" height="{board_size}">']

    for rank_index, row in enumerate(rows):
        file_index = 0

        for char in row:
            if char.isdigit():
                for _ in range(int(char)):
                    x = file_index * square_size
                    y = rank_index * square_size
                    is_light = (rank_index + file_index) % 2 == 0
                    fill = light_color if is_light else dark_color
                    svg.append(f'<rect x="{x}" y="{y}" width="{square_size}" height="{square_size}" fill="{fill}"/>')
                    file_index += 1
            else:
                x = file_index * square_size
                y = rank_index * square_size
                is_light = (rank_index + file_index) % 2 == 0
                fill = light_color if is_light else dark_color
                svg.append(f'<rect x="{x}" y="{y}" width="{square_size}" height="{square_size}" fill="{fill}"/>')

                icon_path = piece_icon(char)
                svg.append(
                    f'<image href="{icon_path}" x="{x + 5}" y="{y + 5}" width="{square_size - 10}" height="{square_size - 10}"/>'
                )
                file_index += 1

    svg.append('</svg>')
    return "\n".join(svg)