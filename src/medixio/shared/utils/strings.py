def capitalize(text: str) -> str:
    first_letter = text[0].upper()
    return f"{first_letter}{text[1:].lower()}"
