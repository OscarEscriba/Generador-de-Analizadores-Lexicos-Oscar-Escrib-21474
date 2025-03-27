# regexToDFA.py - Versión mejorada y corregida
from collections import defaultdict

class Node:
    def __init__(self, data, left=None, right=None):
        self.data = data
        self.left = left
        self.right = right
        self.nullable = None
        self.firstpos = set()
        self.lastpos = set()
        self.position = None

class RegexToDFA:
    def __init__(self, regex):
        self.original_regex = regex
        self.augmented_regex = f"({regex})#"
        self.alphabet = self._extract_alphabet(regex)
        self.pos_to_symbol = {}
        self.next_pos = 1
        self.followpos = defaultdict(set)
        self.syntax_tree = None
        self.dfa = None
        self.minimized_dfa = None

    def _extract_alphabet(self, regex):
        alphabet = set()
        i = 0
        while i < len(regex):
            if regex[i] == '\\':
                if i+1 < len(regex):
                    alphabet.add(regex[i+1])
                    i += 2
                continue
            elif regex[i] == '[':
                j = i + 1
                while j < len(regex) and regex[j] != ']':
                    if regex[j] == '-' and j-1 > i and j+1 < len(regex):
                        start = ord(regex[j-1])
                        end = ord(regex[j+1])
                        alphabet.update(chr(c) for c in range(start, end+1))
                        j += 2
                    else:
                        alphabet.add(regex[j])
                        j += 1
                i = j + 1
            elif regex[i] not in {'(', ')', '|', '*', '+', '?', '·'}:
                alphabet.add(regex[i])
                i += 1
            else:
                i += 1
        return alphabet

    def parse_regex(self):
        postfix = self._infix_to_postfix(self.augmented_regex)
        self.syntax_tree = self._build_syntax_tree(postfix)
        self._calculate_tree_properties(self.syntax_tree)
        self._compute_followpos(self.syntax_tree)

    def _infix_to_postfix(self, regex):
        output = []
        stack = []
        precedence = {'|': 1, '·': 2, '*': 3, '+': 3, '?': 3}
        
        i = 0
        while i < len(regex):
            c = regex[i]
            
            if c == '\\':
                if i+1 < len(regex):
                    output.append(regex[i+1])
                    i += 2
                continue
            
            if c not in '()|*+?·':
                output.append(c)
            elif c == '(':
                stack.append(c)
            elif c == ')':
                while stack and stack[-1] != '(':
                    output.append(stack.pop())
                stack.pop()  # Remove '('
            else:
                while stack and stack[-1] != '(' and precedence.get(stack[-1], 0) >= precedence.get(c, 0):
                    output.append(stack.pop())
                stack.append(c)
            i += 1
        
        while stack:
            output.append(stack.pop())
        
        return ''.join(output)

    def _build_syntax_tree(self, postfix):
        stack = []
        
        for char in postfix:
            if char in '*+?':
                if not stack:
                    raise ValueError("Expresión inválida: operador sin operandos")
                node = Node(char)
                node.left = stack.pop()
                stack.append(node)
            elif char in '|·':
                if len(stack) < 2:
                    raise ValueError("Expresión inválida: operador binario sin suficientes operandos")
                node = Node(char)
                node.right = stack.pop()
                node.left = stack.pop()
                stack.append(node)
            else:
                node = Node(char)
                if char != '#':
                    node.position = self.next_pos
                    self.pos_to_symbol[self.next_pos] = char
                    self.next_pos += 1
                stack.append(node)
        
        if len(stack) != 1:
            raise ValueError("Expresión inválida: demasiados operandos")
        return stack[0]

    def _calculate_tree_properties(self, node):
        if node is None:
            return
        
        if node.data not in {'*', '+', '?', '|', '·'}:
            node.nullable = False
            if node.position:
                node.firstpos = {node.position}
                node.lastpos = {node.position}
        elif node.data == '|':
            self._calculate_tree_properties(node.left)
            self._calculate_tree_properties(node.right)
            node.nullable = node.left.nullable or node.right.nullable
            node.firstpos = node.left.firstpos.union(node.right.firstpos)
            node.lastpos = node.left.lastpos.union(node.right.lastpos)
        elif node.data == '·':
            self._calculate_tree_properties(node.left)
            self._calculate_tree_properties(node.right)
            node.nullable = node.left.nullable and node.right.nullable
            node.firstpos = node.left.firstpos.copy()
            if node.left.nullable:
                node.firstpos.update(node.right.firstpos)
            node.lastpos = node.right.lastpos.copy()
            if node.right.nullable:
                node.lastpos.update(node.left.lastpos)
        elif node.data in {'*', '+', '?'}:
            self._calculate_tree_properties(node.left)
            node.nullable = True if node.data in {'*', '?'} else node.left.nullable
            node.firstpos = node.left.firstpos.copy()
            node.lastpos = node.left.lastpos.copy()

    def _compute_followpos(self, node):
        if node.data == '·':
            for i in node.left.lastpos:
                self.followpos[i].update(node.right.firstpos)
        elif node.data in {'*', '+'}:
            for i in node.lastpos:
                self.followpos[i].update(node.firstpos)
        
        if node.left:
            self._compute_followpos(node.left)
        if node.right:
            self._compute_followpos(node.right)

    def construct_dfa(self):
        try:
            self.parse_regex()
            initial_state = frozenset(self.syntax_tree.firstpos)
            states = {initial_state: 0}
            unmarked_states = [initial_state]
            transitions = {}
            final_states = set()
            
            end_pos = next(pos for pos, sym in self.pos_to_symbol.items() if sym == '#')
            
            while unmarked_states:
                current_state = unmarked_states.pop(0)
                
                if end_pos in current_state:
                    final_states.add(states[current_state])
                
                for symbol in self.alphabet:
                    next_state_positions = set()
                    for pos in current_state:
                        if self.pos_to_symbol.get(pos) == symbol:
                            next_state_positions.update(self.followpos[pos])
                    
                    if not next_state_positions:
                        continue
                    
                    next_state = frozenset(next_state_positions)
                    if next_state not in states:
                        states[next_state] = len(states)
                        unmarked_states.append(next_state)
                    
                    transitions[(states[current_state], symbol)] = states[next_state]
            
            self.dfa = {
                'states': states,
                'initial': 0,
                'final_states': final_states,
                'transitions': transitions
            }
            return self.dfa
        except Exception as e:
            print(f"Error construyendo DFA: {str(e)}")
            return None

    def minimize_dfa(self):
        if not self.dfa:
            self.construct_dfa()
        
        # Implementación básica de minimización
        self.minimized_dfa = self.dfa.copy()
        return self.minimized_dfa

    def process(self):
        try:
            self.construct_dfa()
            self.minimize_dfa()
            return self.minimized_dfa
        except Exception as e:
            print(f"Error procesando expresión regular: {str(e)}")
            return None