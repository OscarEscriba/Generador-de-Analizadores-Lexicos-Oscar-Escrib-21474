# -*- coding: utf-8 -*-
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
            (r'^(delim+)', 'WHITESPACE'),
            (r'^(letter(letter|digit)*)', 'ID'),
            (r'^(digits(\.digits)?(E(\+|-)?digits)?)', 'NUMBER'),
            (r'^\+', 'PLUS'),
            (r'^-', 'MINUS'),
            (r'^\*', 'TIMES'),
            (r'^/', 'DIV'),
            (r'^\(', 'LPAREN'),
        ]
        
    
    def tokenize(self) -> List[Tuple[str, str]]:
        tokens = []
        while self.pos < len(self.text):
            if self._skip_whitespace():
                continue
                
            token = self._match_next_token()
            if token:
                tokens.append(token)
            else:
                raise SyntaxError(
                    f"Carácter inesperado '{self.text[self.pos]}' "
                    f"en línea {self.line}, columna {self.column}"
                )
        return tokens

    def _skip_whitespace(self) -> bool:
        '''Omite espacios en blanco y actualiza posición'''
        match = re.match(r'[ ]+', self.text[self.pos:])
        if match:
            self.line += match.group().count('\n')
            self.column = match.end() - match.start() + 1 if '\n' not in match.group() else 1
            self.pos += match.end()
            return True
        return False

    def _match_next_token(self):
        '''Intenta hacer match con la siguiente regla'''
        for pattern, action in self.rules:
            regex = re.compile(pattern)
            match = regex.match(self.text, self.pos)
            if match:
                value = match.group()
                self.column += len(value)
                self.pos = match.end()
                return (action, value)
        return None



if __name__ == '__main__':
    # Ejemplo de uso
    text = '''
    id + 123 * (var - 5)
    '''
    lexer = Lexer(text)
    try:
        for token in lexer.tokenize():
            print(token)
    except SyntaxError as e:
        print(f"Error léxico: {e}")
