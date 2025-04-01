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
                        ' ': 1,
                        "'": 1,
                        '\t': 1,
                    },
                    1: {
                        '\n': 1,
                        ' ': 1,
                        "'": 1,
                        '\t': 1,
                    },
                },
                'action': 'return WHITESPACE'
            },
            {
                'start': 0,
                'accept': {6, 1, 4},
                'transitions': {
                    0: {
                        '5': 1,
                        '8': 1,
                        '3': 1,
                        '"': 1,
                        '4': 1,
                        '0': 1,
                        '9': 1,
                        '2': 1,
                        '6': 1,
                        '7': 1,
                        '1': 1,
                    },
                    1: {
                        '5': 1,
                        '8': 1,
                        '.': 2,
                        '3': 1,
                        '"': 1,
                        '4': 1,
                        '0': 1,
                        'E': 3,
                        '9': 1,
                        '2': 1,
                        '6': 1,
                        '7': 1,
                        '1': 1,
                    },
                    2: {
                        '5': 4,
                        '8': 4,
                        '3': 4,
                        '"': 4,
                        '4': 4,
                        '0': 4,
                        '9': 4,
                        '2': 4,
                        '6': 4,
                        '7': 4,
                        '1': 4,
                    },
                    3: {
                        "'": 5,
                        '5': 6,
                        '8': 6,
                        '+': 5,
                        '3': 6,
                        '"': 6,
                        '4': 6,
                        '0': 6,
                        '9': 6,
                        '2': 6,
                        '6': 6,
                        '7': 6,
                        '1': 6,
                    },
                    4: {
                        '5': 4,
                        '8': 4,
                        '3': 4,
                        '"': 4,
                        '4': 4,
                        '0': 4,
                        'E': 3,
                        '9': 4,
                        '2': 4,
                        '6': 4,
                        '7': 4,
                        '1': 4,
                    },
                    5: {
                        '5': 6,
                        '8': 6,
                        '3': 6,
                        '"': 6,
                        '4': 6,
                        '0': 6,
                        '9': 6,
                        '2': 6,
                        '6': 6,
                        '7': 6,
                        '1': 6,
                    },
                    6: {
                        '5': 6,
                        '8': 6,
                        '3': 6,
                        '"': 6,
                        '4': 6,
                        '0': 6,
                        '9': 6,
                        '2': 6,
                        '6': 6,
                        '7': 6,
                        '1': 6,
                    },
                },
                'action': 'return NUMBER'
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

