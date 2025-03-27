# -*- coding: utf-8 -*-
return ID

import re
from typing import List, Tuple

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.rules = [
            # (patrón, acción)
            (r'^'\+'', 'PLUS'),
            (r'^'\*'', 'TIMES'),
            (r'^'\('', 'LPAREN'),
            (r'^letter\(letter|digit\)\*', 'ID')
        ]
    
    def tokenize(self) -> List[Tuple[str, str]]:
        tokens = []
        while self.pos < len(self.text):
            self._skip_whitespace()
            if self.pos >= len(self.text):
                break
                
            token = self._match_next_token()
            if token:
                tokens.append(token)
            else:
                context = self.text[max(0, self.pos-5):self.pos+5]
                raise SyntaxError(
                    f"Error léxico en línea {self.line}, columna {self.column}\n"
                    f"Contexto: '...{context}...'\n"
                    f"Carácter no reconocido: '{self.text[self.pos]}'"
                )
        return tokens

    def _skip_whitespace(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            if self.text[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def _match_next_token(self):
        for pattern, action in self.rules:
            match = re.match(pattern, self.text[self.pos:])
            if match:
                value = match.group()
                self.column += len(value)
                self.pos += len(value)
                return (action, value)
        return None



if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Uso: python lexer.py <archivo_entrada>")
        sys.exit(1)
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        text = f.read()
    
    lexer = Lexer(text)
    try:
        for token in lexer.tokenize():
            print(token)
    except SyntaxError as e:
        print(f"Error léxico: {e}")
