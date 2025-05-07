# utils/table_formatter.py
def format_table(table_data: list) -> str:
    if not table_data:
        return ""

    col_widths = [max(len(str(cell)) for cell in col)
                  for col in zip(*table_data)]

    formatted_lines = []
    for row in table_data:
        formatted_row = [
            f"{row[i]:{col_widths[i]}}" if i < len(row) else ' ' * col_widths[i]
            for i in range(len(col_widths))
        ]
        formatted_lines.append(" | ".join(formatted_row))


    return "\n".join(formatted_lines)
