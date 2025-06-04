from collections import defaultdict

class Token:
    def __init__(self, type, value=None, position=None):
        self.type = type
        self.value = value
        self.position = position

    def __repr__(self):
        if self.value:
            return f"{self.type}({self.value}) at {self.position}"
        return f"{self.type} at {self.position}"

class Lexer:
    def __init__(self, input_text):
        self.input = input_text
        self.position = 0
        self.line = 1
        self.column = 1

        # DFA transitions
        self.dfas = []
        # DFA 0
        dfa_0_states = []
        dfa_0_transitions = []
        # State 0
        dfa_0_transitions.append([(1, {"'", '\t', '\n', ' '})])
        dfa_0_states.append(False)
        # State 1
        dfa_0_transitions.append([(1, {"'", '\t', '\n', ' '})])
        dfa_0_states.append(True)
        self.dfas.append((dfa_0_states, dfa_0_transitions))

        # DFA 1
        dfa_1_states = []
        dfa_1_transitions = []
        # State 0
        dfa_1_transitions.append([(1, {'1', '5', '6', '8', '0', '"', '9', '3', '2', '4', '7'})])
        dfa_1_states.append(False)
        # State 1
        dfa_1_transitions.append([(1, {'1', '5', '6', '8', '0', '"', '9', '3', '2', '4', '7'}), (2, {'E'}), (3, {'.'})])
        dfa_1_states.append(True)
        # State 2
        dfa_1_transitions.append([(4, {'1', '5', '6', '8', '0', '"', '9', '3', '2', '4', '7'}), (5, {"'", '+'})])
        dfa_1_states.append(False)
        # State 3
        dfa_1_transitions.append([(6, {'1', '5', '6', '8', '0', '"', '9', '3', '2', '4', '7'})])
        dfa_1_states.append(False)
        # State 4
        dfa_1_transitions.append([(4, {'1', '5', '6', '8', '0', '"', '9', '3', '2', '4', '7'})])
        dfa_1_states.append(True)
        # State 5
        dfa_1_transitions.append([(4, {'1', '5', '6', '8', '0', '"', '9', '3', '2', '4', '7'})])
        dfa_1_states.append(False)
        # State 6
        dfa_1_transitions.append([(6, {'1', '5', '6', '8', '0', '"', '9', '3', '2', '4', '7'}), (2, {'E'})])
        dfa_1_states.append(True)
        self.dfas.append((dfa_1_states, dfa_1_transitions))

        # DFA 2
        dfa_2_states = []
        dfa_2_transitions = []
        # State 0
        dfa_2_transitions.append([(1, {'+'})])
        dfa_2_states.append(False)
        # State 1
        dfa_2_transitions.append([])
        dfa_2_states.append(True)
        self.dfas.append((dfa_2_states, dfa_2_transitions))

        # DFA 3
        dfa_3_states = []
        dfa_3_transitions = []
        # State 0
        dfa_3_transitions.append([(1, {'*'})])
        dfa_3_states.append(False)
        # State 1
        dfa_3_transitions.append([])
        dfa_3_states.append(True)
        self.dfas.append((dfa_3_states, dfa_3_transitions))

        # DFA 4
        dfa_4_states = []
        dfa_4_transitions = []
        # State 0
        dfa_4_transitions.append([(1, {'('})])
        dfa_4_states.append(False)
        # State 1
        dfa_4_transitions.append([])
        dfa_4_states.append(True)
        self.dfas.append((dfa_4_states, dfa_4_transitions))

        # Token actions
        self.actions = [
            'WHITESPACE',
            'NUMBER',
            'PLUS',
            'TIMES',
            'LPAREN',
        ]

    def next_token(self):
        if self.position >= len(self.input):
            return Token('EOF', position=(self.line, self.column))

        # Skip whitespace (but we actually tokenize it in this case)
        # while self.position < len(self.input) and self.input[self.position].isspace():
        #     if self.input[self.position] == '\n':
        #         self.line += 1
        #         self.column = 1
        #     else:
        #         self.column += 1
        #     self.position += 1

        if self.position >= len(self.input):
            return Token('EOF', position=(self.line, self.column))

        longest_match = None
        longest_length = 0
        matching_action = None

        # Try each DFA to find the longest match
        for i, (states, transitions) in enumerate(self.dfas):
            current_state = 0  # Start state
            current_length = 0
            last_accepting_state = None
            last_accepting_length = 0

            for j in range(self.position, len(self.input)):
                char = self.input[j]
                found = False
                for dest, symbols in transitions[current_state]:
                    if char in symbols:
                        current_state = dest
                        current_length += 1
                        found = True
                        if states[current_state]:
                            last_accepting_state = current_state
                            last_accepting_length = current_length
                        break
                if not found:
                    break

            # Use the last accepting state if we couldn't consume all characters
            if last_accepting_state is not None and last_accepting_length > longest_length:
                longest_match = self.input[self.position:self.position + last_accepting_length]
                longest_length = last_accepting_length
                matching_action = self.actions[i]

        if longest_match is not None:
            token_type = matching_action
            start_pos = (self.line, self.column)
            
            # Update position
            for char in longest_match:
                if char == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
            
            self.position += longest_length
            end_pos = (self.line, self.column)
            
            return Token(token_type, longest_match, (start_pos, end_pos))
        
        # No match found - return error token
        error_char = self.input[self.position]
        error_pos = (self.line, self.column)
        self.position += 1
        self.column += 1
        return Token('ERROR', error_char, error_pos)

    def tokenize(self):
        tokens = []
        while True:
            token = self.next_token()
            tokens.append(token)
            if token.type == 'EOF':
                break
        return tokens

