# -*- coding: utf-8 -*-
# Lexer generado automáticamente - NO MODIFICAR DIRECTAMENTE

import re
from typing import List, Tuple, Optional

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.rules = [
            # (patrón, acción)
            (r'^(letter(letter|digit)*)', 'ID'),
            (r'^(delim*)', None),
            (r'^\+', 'PLUS'),
            (r'^\*', 'TIMES'),
            (r'^\(', 'LPAREN'),
            (r'^\)', None)
        ]
    
    def tokenize(self) -> List[Tuple[str, str]]:
        tokens = []
        while self.pos < len(self.text):
            self._skip_whitespace()
            if self.pos >= len(self.text):
                break
                
            match = self._match_next_token()
            if not match:
                self._report_lexical_error()
                break
            token_type, value = match
            if token_type:
                tokens.append((token_type, value))
        return tokens

    def _skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            if self.text[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def _match_next_token(self) -> Optional[Tuple[str, str]]:
        remaining_text = self.text[self.pos:]
        for pattern, action in self.rules:
            match = re.match(pattern, remaining_text)
            if match:
                value = match.group(0)
                self.pos += len(value)
                self.column += len(value)
                return (action, value) if action else (None, value)
        return None

    def _report_lexical_error(self):
        context = self.text[max(0, self.pos-5):self.pos+5]
        raise SyntaxError(
            f"Error léxico en línea {self.line}, columna {self.column}\n"
            f"Contexto: '...{context}...'\n"
            f"Carácter no reconocido: '{self.text[self.pos]}'"
        )



if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Uso: python lexer.py <archivo_entrada>", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            text = f.read()
        
        lexer = Lexer(text)
        for token in lexer.tokenize():
            if token[0]:  # Ignorar tokens None (como whitespace)
                print(token)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
