import re
import os
import sys
import graphviz
from collections import defaultdict

class Token:
    def __init__(self, type, value=None):
        self.type = type
        self.value = value
    
    def __repr__(self):
        if self.value:
            return f"{self.type}({self.value})"
        return f"{self.type}"

class YALexParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.content = None
        self.definitions = {}
        self.rules = []
        self.header = None
        self.trailer = None
    
    def parse(self):
        # Read the content of the file
        with open(self.file_path, 'r') as file:
            self.content = file.read()
        
        # Remove comments
        self.content = re.sub(r'\(\*.*?\*\)', '', self.content, flags=re.DOTALL)
        
        # Extract header
        header_match = re.search(r'^\s*{(.*?)}', self.content, re.DOTALL)
        if header_match:
            self.header = header_match.group(1).strip()
            self.content = self.content[header_match.end():].strip()
        
        # Extract trailer
        trailer_match = re.search(r'{(.*?)}$', self.content, re.DOTALL)
        if trailer_match:
            self.trailer = trailer_match.group(1).strip()
            self.content = self.content[:trailer_match.start()].strip()
        
        # Extract definitions
        while True:
            definition_match = re.search(r'let\s+(\w+)\s*=\s*(.+?)\s*(?=let|\n\s*rule)', self.content, re.DOTALL)
            if not definition_match:
                break
            
            ident = definition_match.group(1)
            regexp = definition_match.group(2).strip()
            self.definitions[ident] = regexp
            self.content = self.content[:definition_match.start()] + self.content[definition_match.end():]
        
        # Extract rules
        rule_section = re.search(r'rule\s+(\w+)(?:\s*\[\s*(.*?)\s*\])?\s*=\s*(.*?)(?=$)', self.content, re.DOTALL)
        if rule_section:
            entrypoint = rule_section.group(1)
            args = rule_section.group(2)
            rules_text = rule_section.group(3).strip()
            
            # Parse individual rules
            rule_pattern = r'\|\s*(.*?)\s*{\s*(.*?)\s*}|^\s*(.*?)\s*{\s*(.*?)\s*}'
            rule_matches = re.finditer(rule_pattern, rules_text, re.DOTALL)
            
            for match in rule_matches:
                if match.group(1) is not None:
                    regexp = match.group(1).strip()
                    action = match.group(2).strip()
                else:
                    regexp = match.group(3).strip()
                    action = match.group(4).strip()
                
                self.rules.append((regexp, action))
            
            return {
                'header': self.header,
                'trailer': self.trailer,
                'definitions': self.definitions,
                'entrypoint': entrypoint,
                'args': args,
                'rules': self.rules
            }
        
        return None

class RegexNode:
    def __init__(self, type, value=None, left=None, right=None):
        self.type = type
        self.value = value
        self.left = left
        self.right = right
    
    def __repr__(self):
        if self.type == 'CHAR' or self.type == 'RANGE' or self.type == 'CHARCLASS':
            return f"{self.type}({self.value})"
        elif self.type == 'CONCAT' or self.type == 'UNION' or self.type == 'DIFF':
            return f"{self.type}({self.left}, {self.right})"
        else:  # STAR, PLUS, OPTIONAL
            return f"{self.type}({self.left})"

class RegexParser:
    def __init__(self, definitions=None):
        self.definitions = definitions or {}
        self.pos = 0
        self.input = ""
    
    def parse(self, regex):
        self.input = regex
        self.pos = 0
        result = self.parse_regex()
        # asegurarse que el resultado es un RegexNode
        if not isinstance(result, RegexNode):
            raise ValueError(f"Regex no parseado correctamente: {regex}. Se obtuvo el siguiente resultado: {result}")
        return result

    
    def parse_regex(self):
        left = self.parse_term()
        if self.pos < len(self.input) and self.input[self.pos] == '|':
            self.pos += 1
            right = self.parse_regex()
            return RegexNode('UNION', left=left, right=right)
        return left
    
    def parse_term(self):
        factors = []
        while self.pos < len(self.input) and self.input[self.pos] not in '|)':
            factors.append(self.parse_factor())
        
        if not factors:
            return RegexNode('CHAR', value='ε')  # Empty string
        
        if len(factors) == 1:
            return factors[0]
        
        # Build concatenation tree
        result = factors[0]
        for i in range(1, len(factors)):
            result = RegexNode('CONCAT', left=result, right=factors[i])
        
        return result
    
    def parse_factor(self):
        atom = self.parse_atom()
        
        if self.pos < len(self.input):
            if self.input[self.pos] == '*':
                self.pos += 1
                return RegexNode('STAR', left=atom)
            elif self.input[self.pos] == '+':
                self.pos += 1
                return RegexNode('PLUS', left=atom)
            elif self.input[self.pos] == '?':
                self.pos += 1
                return RegexNode('OPTIONAL', left=atom)
            elif self.input[self.pos] == '#' and self.pos + 1 < len(self.input):
                self.pos += 1
                right = self.parse_factor()
                return RegexNode('DIFF', left=atom, right=right)
        
        return atom
    
    def parse_atom(self):
        if self.pos >= len(self.input):
            return RegexNode('CHAR', value='ε')  # Empty string
        
        if self.input[self.pos] == '(':
            self.pos += 1
            regex = self.parse_regex()
            if self.pos < len(self.input) and self.input[self.pos] == ')':
                self.pos += 1
            return regex
        
        if self.input[self.pos] == '_':
            self.pos += 1
            return RegexNode('CHARCLASS', value='ANY')
        
        if self.input[self.pos] == '[':
            self.pos += 1
            negate = False
            if self.pos < len(self.input) and self.input[self.pos] == '^':
                negate = True
                self.pos += 1
            
            chars = set()
            while self.pos < len(self.input) and self.input[self.pos] != ']':
                if self.input[self.pos] == '\'':
                    self.pos += 1
                    if self.pos < len(self.input):
                        char = self.input[self.pos]
                        chars.add(char)
                        self.pos += 1
                        
                        # Check for range
                        if self.pos + 2 < len(self.input) and self.input[self.pos] == '-' and self.input[self.pos+1] == '\'':
                            self.pos += 2
                            end_char = self.input[self.pos]
                            self.pos += 1
                            for c in range(ord(char), ord(end_char) + 1):
                                chars.add(chr(c))
                    
                    # Skip the closing quote
                    if self.pos < len(self.input) and self.input[self.pos] == '\'':
                        self.pos += 1
                elif self.input[self.pos] == '"':
                    self.pos += 1
                    start = self.pos
                    while self.pos < len(self.input) and self.input[self.pos] != '"':
                        self.pos += 1
                    
                    if self.pos < len(self.input):
                        string_chars = self.input[start:self.pos]
                        for c in string_chars:
                            chars.add(c)
                        self.pos += 1
                else:
                    chars.add(self.input[self.pos])
                    self.pos += 1
            
            if self.pos < len(self.input) and self.input[self.pos] == ']':
                self.pos += 1
            
            if negate:
                return RegexNode('CHARCLASS', value=f"NOT({','.join(sorted(chars))})")
            return RegexNode('CHARCLASS', value=','.join(sorted(chars)))
        
        if self.input[self.pos] == '\'':
            self.pos += 1
            if self.pos < len(self.input):
                char = self.input[self.pos]
                self.pos += 1
                if self.pos < len(self.input) and self.input[self.pos] == '\'':
                    self.pos += 1
                return RegexNode('CHAR', value=char)
        
        if self.input[self.pos] == '"':
            self.pos += 1
            start = self.pos
            while self.pos < len(self.input) and self.input[self.pos] != '"':
                self.pos += 1
            
            if self.pos < len(self.input):
                string_chars = self.input[start:self.pos]
                self.pos += 1
                
                if len(string_chars) == 1:
                    return RegexNode('CHAR', value=string_chars)
                
                # Create a concatenation of characters
                result = RegexNode('CHAR', value=string_chars[0])
                for i in range(1, len(string_chars)):
                    char_node = RegexNode('CHAR', value=string_chars[i])
                    result = RegexNode('CONCAT', left=result, right=char_node)
                
                return result
        
        # Check for identifier (corregido para incluir '_' al inicio)
        if self.input[self.pos].isalpha() or self.input[self.pos] == '_':
            start = self.pos
            while self.pos < len(self.input) and (self.input[self.pos].isalnum() or self.input[self.pos] == '_'):
                self.pos += 1

            ident = self.input[start:self.pos]
            if ident in self.definitions:
                # Guardar estado actual del parser
                saved_pos = self.pos
                saved_input = self.input
                
                # Parsear la definición recursivamente
                self.input = self.definitions[ident]
                self.pos = 0
                parsed_node = self.parse_regex()  # <--- Debe devolver un RegexNode
                
                # Restaurar estado
                self.pos = saved_pos
                self.input = saved_input
                return parsed_node  # <--- Asegurar que es un RegexNode
        
        # Default to single character
        char = self.input[self.pos]
        self.pos += 1
        return RegexNode('CHAR', value=char)

class NFAState:
    def __init__(self, state_id):
        self.id = state_id
        self.transitions = defaultdict(set)
        self.epsilon_transitions = set()
        self.is_accepting = False
        self.token_action = None
    
    def add_transition(self, symbol, state):
        self.transitions[symbol].add(state)
    
    def add_epsilon_transition(self, state):
        self.epsilon_transitions.add(state)

class NFA:
    def __init__(self):
        self.states = []
        self.start_state = None
        self.accept_states = set()
    
    def create_state(self):
        state = NFAState(len(self.states))
        self.states.append(state)
        return state
    
    def epsilon_closure(self, states):
        if not isinstance(states, set):
            states = {states}
        
        closure = set(states)
        stack = list(states)
        
        while stack:
            state = stack.pop()
            for next_state in state.epsilon_transitions:
                if next_state not in closure:
                    closure.add(next_state)
                    stack.append(next_state)
        
        return closure

class NFABuilder:
    def __init__(self):
        self.state_counter = 0
    
    def build_from_regex(self, regex_node):
        nfa = NFA()
        start, end = self._build_node(regex_node, nfa)
        nfa.start_state = start
        end.is_accepting = True
        nfa.accept_states.add(end)
        return nfa
    
    def _build_node(self, node, nfa):
        if node.type == 'CHAR':
            start = nfa.create_state()
            end = nfa.create_state()
            start.add_transition(node.value, end)
            return start, end
        
        elif node.type == 'CONCAT':
            start_left, end_left = self._build_node(node.left, nfa)
            start_right, end_right = self._build_node(node.right, nfa)
            end_left.add_epsilon_transition(start_right)
            return start_left, end_right
        
        elif node.type == 'UNION':
            start = nfa.create_state()
            end = nfa.create_state()
            
            start_left, end_left = self._build_node(node.left, nfa)
            start_right, end_right = self._build_node(node.right, nfa)
            
            start.add_epsilon_transition(start_left)
            start.add_epsilon_transition(start_right)
            end_left.add_epsilon_transition(end)
            end_right.add_epsilon_transition(end)
            
            return start, end
        
        elif node.type == 'STAR':
            start = nfa.create_state()
            end = nfa.create_state()
            
            sub_start, sub_end = self._build_node(node.left, nfa)
            
            start.add_epsilon_transition(sub_start)
            start.add_epsilon_transition(end)
            sub_end.add_epsilon_transition(sub_start)
            sub_end.add_epsilon_transition(end)
            
            return start, end
        
        elif node.type == 'PLUS':
            start = nfa.create_state()
            end = nfa.create_state()
            
            sub_start, sub_end = self._build_node(node.left, nfa)
            
            start.add_epsilon_transition(sub_start)
            sub_end.add_epsilon_transition(sub_start)
            sub_end.add_epsilon_transition(end)
            
            return start, end
        
        elif node.type == 'OPTIONAL':
            start = nfa.create_state()
            end = nfa.create_state()
            
            sub_start, sub_end = self._build_node(node.left, nfa)
            
            start.add_epsilon_transition(sub_start)
            start.add_epsilon_transition(end)
            sub_end.add_epsilon_transition(end)
            
            return start, end
        
        elif node.type == 'CHARCLASS':
            start = nfa.create_state()
            end = nfa.create_state()
            
            if node.value == 'ANY':
                # Any character (except newline in some implementations)
                for i in range(256):
                    start.add_transition(chr(i), end)
            elif node.value.startswith('NOT('):
                # Negated character class
                chars = node.value[4:-1].split(',')
                for i in range(256):
                    char = chr(i)
                    if char not in chars:
                        start.add_transition(char, end)
            else:
                # Regular character class
                chars = node.value.split(',')
                for char in chars:
                    start.add_transition(char, end)
            
            return start, end
        
        elif node.type == 'DIFF':
            # Character class difference (A - B)
            # This is a simplified implementation
            start = nfa.create_state()
            end = nfa.create_state()
            
            # This is a naive implementation and might not handle all cases correctly
            if node.left.type == 'CHARCLASS' and node.right.type == 'CHARCLASS':
                left_chars = set(node.left.value.split(','))
                right_chars = set(node.right.value.split(','))
                diff_chars = left_chars - right_chars
                
                for char in diff_chars:
                    start.add_transition(char, end)
            
            return start, end
        
        # Default fallback
        start = nfa.create_state()
        end = nfa.create_state()
        start.add_epsilon_transition(end)
        return start, end

class DFAState:
    def __init__(self, state_id, nfa_states):
        self.id = state_id
        self.nfa_states = nfa_states
        self.transitions = {}
        self.is_accepting = any(state.is_accepting for state in nfa_states)
        self.token_action = None
        
        # Find token action from the accepting NFA state
        for state in nfa_states:
            if state.is_accepting and state.token_action:
                self.token_action = state.token_action
                break

class DFA:
    def __init__(self):
        self.states = []
        self.start_state = None
        self.accept_states = set()
    
    def create_state(self, nfa_states):
        state = DFAState(len(self.states), nfa_states)
        self.states.append(state)
        if state.is_accepting:
            self.accept_states.add(state)
        return state

class NFAToDFAConverter:
    def __init__(self):
        self.alphabet = set()
    
    def convert(self, nfa):
        # Extraer alfabeto del NFA excluyendo ε
        self.alphabet = set()
        for state in nfa.states:
            for symbol in state.transitions.keys():
                if symbol != 'ε':  # <--- Filtramos explícitamente ε
                    self.alphabet.add(symbol)
        
        dfa = DFA()
        
        # Cálculo de la clausura-épsilon inicial
        start_closure = nfa.epsilon_closure(nfa.start_state)
        
        # Crear estado inicial del DFA
        dfa.start_state = dfa.create_state(start_closure)
        
        # Lista de estados DFA por procesar
        unprocessed = [dfa.start_state]
        state_map = {frozenset(start_closure): dfa.start_state}
        
        # Construcción de transiciones DFA
        while unprocessed:
            current = unprocessed.pop(0)
            
            for symbol in self.alphabet:  # <--- Solo símbolos válidos (sin ε)
                next_nfa_states = set()
                
                # Calcular transiciones para el símbolo actual
                for nfa_state in current.nfa_states:
                    if symbol in nfa_state.transitions:
                        next_nfa_states.update(nfa_state.transitions[symbol])
                
                # Clausura-épsilon de los estados alcanzados
                epsilon_closure = set()
                for state in next_nfa_states:
                    epsilon_closure.update(nfa.epsilon_closure(state))
                
                if not epsilon_closure:
                    continue
                
                frozen_closure = frozenset(epsilon_closure)
                
                # Crear nuevo estado DFA si no existe
                if frozen_closure not in state_map:
                    new_state = dfa.create_state(epsilon_closure)
                    state_map[frozen_closure] = new_state
                    unprocessed.append(new_state)
                
                # Añadir transición
                current.transitions[symbol] = state_map[frozen_closure]
        
        # Asignar acciones de token a estados de aceptación
        for dfa_state in dfa.accept_states:
            for nfa_state in dfa_state.nfa_states:
                if nfa_state.is_accepting and nfa_state.token_action:
                    dfa_state.token_action = nfa_state.token_action
                    break
        
        return dfa

class RegexVisualizer:
    def __init__(self):
        self.counter = 0
    
    def visualize(self, node, name="regex_tree"):
        dot = graphviz.Digraph(name)
        self.counter = 0
        self._build_graph(dot, node)
        return dot
    
    def _build_graph(self, dot, node):
        if not node:
            return
        
        node_id = f"node_{self.counter}"
        self.counter += 1
        
        if node.type == 'CHAR' or node.type == 'RANGE' or node.type == 'CHARCLASS':
            label = f"{node.type}\\n{node.value}"
            dot.node(node_id, label)
        elif node.type == 'CONCAT' or node.type == 'UNION' or node.type == 'DIFF':
            dot.node(node_id, node.type)
            
            left_id = self._build_graph(dot, node.left)
            right_id = self._build_graph(dot, node.right)
            
            if left_id:
                dot.edge(node_id, left_id)
            if right_id:
                dot.edge(node_id, right_id)
        else:  # STAR, PLUS, OPTIONAL
            dot.node(node_id, node.type)
            
            child_id = self._build_graph(dot, node.left)
            if child_id:
                dot.edge(node_id, child_id)
        
        return node_id

class NFAVisualizer:
    def visualize(self, nfa, name="nfa"):
        dot = graphviz.Digraph(name)
        
        # Add states
        for state in nfa.states:
            if state.is_accepting:
                dot.node(str(state.id), shape="doublecircle")
            else:
                dot.node(str(state.id), shape="circle")
            
            # Add transitions (corregir caracteres especiales)
            for symbol, destinations in state.transitions.items():
                # Escapar caracteres especiales: \ -> \\, " -> \", | -> \|
                escaped_symbol = symbol.replace('\\', '\\\\').replace('"', '\\"').replace('|', '\\|')
                for dest in destinations:
                    dot.edge(str(state.id), str(dest.id), label=escaped_symbol)
            
            # Add epsilon transitions (manejar ε)
            for dest in state.epsilon_transitions:
                dot.edge(str(state.id), str(dest.id), label="ε")
        
        # Mark start state
        if nfa.start_state:
            dot.node("start", shape="point")
            dot.edge("start", str(nfa.start_state.id))
        
        return dot

class DFAVisualizer:
    def visualize(self, dfa, name="dfa"):
        dot = graphviz.Digraph(name)
        
        # Add states
        for state in dfa.states:
            label = f"{state.id}"
            if state.token_action:
                label += f"\\n{state.token_action}"
            
            if state in dfa.accept_states:
                dot.node(str(state.id), label=label, shape="doublecircle")
            else:
                dot.node(str(state.id), label=label, shape="circle")
            
            # Add transitions
            for symbol, dest in state.transitions.items():
                dot.edge(str(state.id), str(dest.id), label=symbol)
        
        # Mark start state
        if dfa.start_state:
            dot.node("start", shape="point")
            dot.edge("start", str(dfa.start_state.id))
        
        return dot

class LexerGenerator:
    def __init__(self, yalex_file):
        self.yalex_file = yalex_file
        self.yalex_data = None
        self.lexer_name = "lexer"
        self.regex_trees = []
        self.nfas = []
        self.dfas = []
        self.nfa_builder = NFABuilder()
    
    def parse_yalex(self):
        parser = YALexParser(self.yalex_file)
        self.yalex_data = parser.parse()
        if not self.yalex_data:
            raise ValueError("Failed to parse YALex file")
        
        return self.yalex_data
    
    def build_regex_trees(self):
        if not self.yalex_data:
            raise ValueError("YALex file not parsed yet")
        
        regex_parser = RegexParser(self.yalex_data['definitions'])
        self.regex_trees = []
        
        for regexp, action in self.yalex_data['rules']:
            try:
                regex_tree = regex_parser.parse(regexp)
                self.regex_trees.append((regex_tree, action))
            except Exception as e:
                print(f"Error al parsear la regla: '{regexp}'. Acción: {action}")
                raise e
        
        return self.regex_trees
    
    def build_nfas(self):
        if not self.regex_trees:
            raise ValueError("Regex trees not built yet")
        
        self.nfas = []
        for regex_tree, action in self.regex_trees:
            nfa = self.nfa_builder.build_from_regex(regex_tree)  # Usar self.nfa_builder
            for state in nfa.accept_states:
                state.token_action = action
            self.nfas.append(nfa)
        return self.nfas
    
    def build_dfas(self):
        if not self.nfas:
            raise ValueError("NFAs not built yet")
        
        converter = NFAToDFAConverter()
        self.dfas = []
        
        for regex_tree, _ in self.regex_trees:
            nfa = self.nfa_builder.build_from_regex(regex_tree)  # Acceso correcto
            dfa = converter.convert(nfa)
            self.dfas.append(dfa)
        return self.dfas
    
    def visualize_regex_trees(self, output_dir="output"):
        if not self.regex_trees:
            raise ValueError("Regex trees not built yet")
        
        os.makedirs(output_dir, exist_ok=True)
        visualizer = RegexVisualizer()
        
        for i, (regex_tree, _) in enumerate(self.regex_trees):
            dot = visualizer.visualize(regex_tree, f"regex_tree_{i}")
            dot.render(f"{output_dir}/regex_tree_{i}", format="png", cleanup=True)
    
    def visualize_nfas(self, output_dir="output"):
        if not self.nfas:
            raise ValueError("NFAs not built yet")
        
        os.makedirs(output_dir, exist_ok=True)
        visualizer = NFAVisualizer()
        
        for i, nfa in enumerate(self.nfas):
            dot = visualizer.visualize(nfa, f"nfa_{i}")
            dot.render(f"{output_dir}/nfa_{i}", format="png", cleanup=True)
    
    def visualize_dfas(self, output_dir="output"):
        if not self.dfas:
            raise ValueError("DFAs not built yet")
        
        os.makedirs(output_dir, exist_ok=True)
        visualizer = DFAVisualizer()
        
        for i, dfa in enumerate(self.dfas):
            dot = visualizer.visualize(dfa, f"dfa_{i}")
            dot.render(f"{output_dir}/dfa_{i}", format="png", cleanup=True)
    
    def generate_combined_dfa(self):
        if not self.dfas:
            raise ValueError("DFAs not built yet")
        
        # This is a simplified approach to combine DFAs
        # A proper implementation would build a single DFA from all regex patterns
        
        # For now, we'll just use the DFAs as they are
        return self.dfas
    
    def generate_lexer(self, output_file=None):
        if not self.yalex_data:
            raise ValueError("YALex file not parsed yet")
        
        if not output_file:
            output_file = os.path.splitext(self.yalex_file)[0] + ".py"
        
        self.build_regex_trees()
        self.build_nfas()
        self.build_dfas()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Escribir el encabezado
            f.write("# Generated Lexer from YALex file\n")
            if self.yalex_data['header']:
                f.write(f"{self.yalex_data['header']}\n\n")
            
            # Escribir imports y clase Token
            f.write("import re\n\n")
            f.write("class Token:\n")
            f.write("    def __init__(self, type, value=None, position=None):\n")
            f.write("        self.type = type\n")
            f.write("        self.value = value\n")
            f.write("        self.position = position\n\n")
            f.write("    def __repr__(self):\n")
            f.write("        if self.value:\n")
            f.write("            return f\"{self.type}({self.value})\"\n")
            f.write("        return f\"{self.type}\"\n\n")
            
            # Escribir clase Lexer
            f.write("class Lexer:\n")
            f.write("    def __init__(self, input_text):\n")
            f.write("        self.input = input_text\n")
            f.write("        self.position = 0\n")
            f.write("        self.line = 1\n")
            f.write("        self.column = 1\n\n")
            
            # Método next_token
            f.write("    def next_token(self):\n")
            f.write("        if self.position >= len(self.input):\n")
            f.write("            return Token('EOF')\n\n")
            f.write("        # Saltar espacios en blanco\n")
            f.write("        while self.position < len(self.input) and self.input[self.position].isspace():\n")
            f.write("            if self.input[self.position] == '\\n':\n")
            f.write("                self.line += 1\n")
            f.write("                self.column = 1\n")
            f.write("            else:\n")
            f.write("                self.column += 1\n")
            f.write("            self.position += 1\n\n")
            f.write("        if self.position >= len(self.input):\n")
            f.write("            return Token('EOF')\n\n")
            
            # Lista de DFAs
            f.write("        # Lista de DFAs (cada uno representa una regla)\n")
            f.write("        dfas = [\n")
            for dfa, (_, action) in zip(self.dfas, self.yalex_data['rules']):
                f.write("            {\n")
                f.write(f"                'start': {dfa.start_state.id},\n")
                f.write(f"                'accept': {{{', '.join(str(s.id) for s in dfa.accept_states)}}},\n")
                f.write("                'transitions': {\n")
                for state in dfa.states:
                    f.write(f"                    {state.id}: {{\n")
                    for symbol, dest in state.transitions.items():
                        f.write(f"                        {repr(symbol)}: {dest.id},\n")
                    f.write("                    },\n")
                f.write("                },\n")
                f.write(f"                'action': {repr(action)}\n")  # Acción desde YALex
                f.write("            },\n")
            f.write("        ]\n\n")
            
            # Lógica de coincidencia de tokens
            f.write("        longest_match = None\n")
            f.write("        longest_length = 0\n")
            f.write("        token_type = None\n")
            f.write("        current_line = self.line\n")
            f.write("        current_column = self.column\n\n")
            f.write("        for dfa_info in dfas:\n")
            f.write("            current_state = dfa_info['start']\n")
            f.write("            current_length = 0\n")
            f.write("            temp_pos = self.position\n")
            f.write("            while temp_pos < len(self.input):\n")
            f.write("                char = self.input[temp_pos]\n")
            f.write("                transitions = dfa_info['transitions'].get(current_state, {})\n")
            f.write("                if char in transitions:\n")
            f.write("                    current_state = transitions[char]\n")
            f.write("                    current_length += 1\n")
            f.write("                    temp_pos += 1\n")
            f.write("                else:\n")
            f.write("                    break\n")
            f.write("            if current_state in dfa_info['accept']:\n")
            f.write("                if current_length > longest_length:\n")
            f.write("                    longest_length = current_length\n")
            f.write("                    token_type = dfa_info['action']\n\n")
            f.write("        if longest_length > 0:\n")
            f.write("            value = self.input[self.position:self.position + longest_length]\n")
            f.write("            self.position += longest_length\n")
            f.write("            self.column += longest_length\n")
            f.write("            return Token(token_type, value, (current_line, current_column))\n")
            f.write("        else:\n")
            f.write("            char = self.input[self.position]\n")
            f.write("            self.position += 1\n")
            f.write("            self.column += 1\n")
            f.write("            return Token('ERROR', char, (current_line, current_column))\n\n")
            
            # Trailer
            if self.yalex_data['trailer']:
                f.write("\n# Trailer\n")
                f.write(self.yalex_data['trailer'])
                f.write("\n")