# Generated Lexer from YALex file
import re

class Token:
    def __init__(self, type, value=None, position=None):
        self.type = type
        self.value = value
        self.position = position

    def __repr__(self):
        if self.value:
            return f"{self.type}({self.value})"
        return f"{self.type}"

class Lexer:
    def __init__(self, input_text):
        self.input = input_text
        self.position = 0
        self.line = 1
        self.column = 1

    def next_token(self):
        if self.position >= len(self.input):
            return Token('EOF')

        if self.position >= len(self.input):
            return Token('EOF')

        # Lista de DFAs (cada uno representa una regla)
        dfas = [
            {
                'start': 0,
                'accept': {1},
                'transitions': {
                    0: {
                        '\n': 1,
                        "'": 1,
                        ' ': 1,
                        '\t': 1,
                    },
                    1: {
                        '\n': 1,
                        "'": 1,
                        ' ': 1,
                        '\t': 1,
                    },
                },
                'action': 'return WHITESPACE'
            },
            {
                'start': 0,
                'accept': {},
                'transitions': {
                    0: {
                        'z': 1,
                        'Z': 1,
                        'a': 1,
                        "'": 1,
                        'A': 1,
                    },
                    1: {
                    },
                },
                'action': 'return ID'
            },
            {
                'start': 0,
                'accept': {6, 1, 4, 7},
                'transitions': {
                    0: {
                        '0': 1,
                        '9': 1,
                        "'": 1,
                    },
                    1: {
                        '.': 2,
                        'E': 3,
                        '0': 1,
                        '9': 1,
                        "'": 1,
                    },
                    2: {
                        '0': 4,
                        '9': 4,
                        "'": 4,
                    },
                    3: {
                        '+': 5,
                        '0': 6,
                        '9': 6,
                        "'": 7,
                    },
                    4: {
                        'E': 3,
                        '0': 4,
                        '9': 4,
                        "'": 4,
                    },
                    5: {
                        '0': 6,
                        '9': 6,
                        "'": 6,
                    },
                    6: {
                        '0': 6,
                        '9': 6,
                        "'": 6,
                    },
                    7: {
                        '0': 6,
                        '9': 6,
                        "'": 6,
                    },
                },
                'action': 'return NUMBER'
            },
            {
                'start': 0,
                'accept': {1},
                'transitions': {
                    0: {
                        ';': 1,
                    },
                    1: {
                    },
                },
                'action': 'return SEMICOLON'
            },
            {
                'start': 0,
                'accept': {2},
                'transitions': {
                    0: {
                        ':': 1,
                    },
                    1: {
                        '=': 2,
                    },
                    2: {
                    },
                },
                'action': 'return ASSIGNOP'
            },
            {
                'start': 0,
                'accept': {1},
                'transitions': {
                    0: {
                        '<': 1,
                    },
                    1: {
                    },
                },
                'action': 'return LT'
            },
            {
                'start': 0,
                'accept': {1},
                'transitions': {
                    0: {
                        '=': 1,
                    },
                    1: {
                    },
                },
                'action': 'return EQ'
            },
            {
                'start': 0,
                'accept': {1},
                'transitions': {
                    0: {
                        '+': 1,
                    },
                    1: {
                    },
                },
                'action': 'return PLUS'
            },
            {
                'start': 0,
                'accept': {1},
                'transitions': {
                    0: {
                        '-': 1,
                    },
                    1: {
                    },
                },
                'action': 'return MINUS'
            },
            {
                'start': 0,
                'accept': {1},
                'transitions': {
                    0: {
                        '*': 1,
                    },
                    1: {
                    },
                },
                'action': 'return TIMES'
            },
            {
                'start': 0,
                'accept': {1},
                'transitions': {
                    0: {
                        '/': 1,
                    },
                    1: {
                    },
                },
                'action': 'return DIV'
            },
            {
                'start': 0,
                'accept': {1},
                'transitions': {
                    0: {
                        '(': 1,
                    },
                    1: {
                    },
                },
                'action': 'return LPAREN'
            },
            {
                'start': 0,
                'accept': {1},
                'transitions': {
                    0: {
                        ')': 1,
                    },
                    1: {
                    },
                },
                'action': 'return RPAREN'
            },
        ]

        longest_match = None
        longest_length = 0
        token_type = None
        current_line = self.line
        current_column = self.column

        for dfa_info in dfas:
            current_state = dfa_info['start']
            current_length = 0
            temp_pos = self.position
            while temp_pos < len(self.input):
                char = self.input[temp_pos]
                transitions = dfa_info['transitions'].get(current_state, {})
                if char in transitions:
                    current_state = transitions[char]
                    current_length += 1
                    temp_pos += 1
                else:
                    break
            if current_state in dfa_info['accept']:
                if current_length > longest_length:
                    longest_length = current_length
                    token_type = dfa_info['action']

        if longest_length > 0:
            value = self.input[self.position:self.position + longest_length]
            self.position += longest_length
            self.column += longest_length
            return Token(token_type, value, (current_line, current_column))
        else:
            char = self.input[self.position]
            self.position += 1
            self.column += 1
            return Token('ERROR', char, (current_line, current_column))

