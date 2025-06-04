import os
import sys
import graphviz
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

class YALexParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.content = None
        self.definitions = {}
        self.rules = []
        self.header = None
        self.trailer = None
    
    def parse(self):
        with open(self.file_path, 'r') as file:
            self.content = file.read()
        
        self.remove_comments()
        self.extract_header()
        self.extract_trailer()
        self.extract_definitions()
        
        rule_section = self.extract_rule_section()
        if rule_section:
            entrypoint, args, rules_text = rule_section
            self.extract_rules(rules_text)
            
            return {
                'header': self.header,
                'trailer': self.trailer,
                'definitions': self.definitions,
                'entrypoint': entrypoint,
                'args': args,
                'rules': self.rules
            }
        
        return None
    
    def remove_comments(self):
        result = []
        i = 0
        n = len(self.content)
        
        while i < n:
            if i + 1 < n and self.content[i] == '(' and self.content[i+1] == '*':
                i += 2
                while i < n and not (self.content[i] == '*' and i+1 < n and self.content[i+1] == ')'):
                    i += 1
                i += 2
            else:
                result.append(self.content[i])
                i += 1
        
        self.content = ''.join(result)
    
    def extract_header(self):
        i = 0
        n = len(self.content)
        
        while i < n and self.content[i].isspace():
            i += 1
        
        if i < n and self.content[i] == '{':
            i += 1
            start = i
            while i < n and self.content[i] != '}':
                i += 1
            
            if i < n:
                self.header = self.content[start:i].strip()
                self.content = self.content[i+1:].strip()
    
    def extract_trailer(self):
        i = len(self.content) - 1
        
        while i >= 0 and self.content[i].isspace():
            i -= 1
        
        if i >= 0 and self.content[i] == '}':
            end = i
            i -= 1
            while i >= 0 and self.content[i] != '{':
                i -= 1
            
            if i >= 0:
                self.trailer = self.content[i+1:end].strip()
                self.content = self.content[:i].strip()
    
    def extract_definitions(self):
        content = self.content
        i = 0
        n = len(content)
        
        while i < n:
            if i + 3 < n and content[i:i+3] == "let" and (i == 0 or content[i-1].isspace()):
                i += 3
                while i < n and content[i].isspace():
                    i += 1
                
                start_ident = i
                while i < n and (content[i].isalnum() or content[i] == '_'):
                    i += 1
                ident = content[start_ident:i].strip()
                
                while i < n and content[i].isspace():
                    i += 1
                
                if i < n and content[i] == '=':
                    i += 1
                    while i < n and content[i].isspace():
                        i += 1
                    
                    start_def = i
                    while i < n:
                        if (i + 3 < n and content[i:i+3] == "let" and content[i-1].isspace()) or \
                           (i + 4 < n and content[i:i+4] == "rule" and content[i-1].isspace()):
                            break
                        i += 1
                    
                    regexp = content[start_def:i].strip()
                    self.definitions[ident] = regexp
            else:
                i += 1
        
        remaining_content = ""
        i = 0
        while i < n:
            if i + 4 < n and content[i:i+4] == "rule" and (i == 0 or content[i-1].isspace()):
                remaining_content = content[i:]
                break
            i += 1
        
        self.content = remaining_content
    
    def extract_rule_section(self):
        content = self.content
        i = 0
        n = len(content)
        
        if i + 4 < n and content[i:i+4] == "rule":
            i += 4
            while i < n and content[i].isspace():
                i += 1
            
            start_entry = i
            while i < n and (content[i].isalnum() or content[i] == '_'):
                i += 1
            entrypoint = content[start_entry:i].strip()
            
            args = None
            if i < n and content[i] == '[':
                i += 1
                start_args = i
                while i < n and content[i] != ']':
                    i += 1
                if i < n:
                    args = content[start_args:i].strip()
                    i += 1
            
            while i < n and content[i].isspace():
                i += 1
            
            if i < n and content[i] == '=':
                i += 1
                rules_text = content[i:].strip()
                return entrypoint, args, rules_text
        
        return None
    
    def extract_rules(self, rules_text):
        lines = rules_text.split('\n')
        current_rule = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith(('|', '')) and '{' in line and '}' in line:
                if line.startswith('|'):
                    line = line[1:].strip()
                
                # Buscar donde empieza la acción
                brace_start = line.find('{')
                brace_end = line.find('}')
                
                if brace_start != -1 and brace_end != -1:
                    regexp = line[:brace_start].strip()
                    action = line[brace_start+1:brace_end].strip()
                    self.rules.append((regexp, action))

class RegexNode:
    def __init__(self, type, value=None, left=None, right=None):
        self.type = type
        self.value = value
        self.left = left
        self.right = right
    
    def __repr__(self):
        if self.type in ('CHAR', 'RANGE', 'CHARCLASS'):
            return f"{self.type}({self.value})"
        elif self.type in ('CONCAT', 'UNION', 'DIFF'):
            return f"{self.type}({self.left}, {self.right})"
        else:
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
        if not isinstance(result, RegexNode):
            raise ValueError(f"Invalid regex: {regex}. Result: {result}")
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
            return RegexNode('CHAR', value='ε')

        if len(factors) == 1:
            return factors[0]

        result = factors[0]
        for factor in factors[1:]:
            result = RegexNode('CONCAT', left=result, right=factor)
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
            elif self.input[self.pos] == '#':
                self.pos += 1
                right = self.parse_factor()
                return RegexNode('DIFF', left=atom, right=right)

        return atom

    def parse_atom(self):
        if self.pos >= len(self.input):
            return RegexNode('CHAR', value='ε')

        char = self.input[self.pos]

        if char == '(':
            self.pos += 1
            node = self.parse_regex()
            if self.pos < len(self.input) and self.input[self.pos] == ')':
                self.pos += 1
            return node

        if char == '_':
            self.pos += 1
            return RegexNode('CHARCLASS', value='ANY')

        if char == '[':
            self.pos += 1
            negate = False
            if self.pos < len(self.input) and self.input[self.pos] == '^':
                negate = True
                self.pos += 1

            chars = set()
            while self.pos < len(self.input) and self.input[self.pos] != ']':
                if self.input[self.pos] == '\\':
                    self.pos += 1
                    if self.pos < len(self.input):
                        escaped = self.input[self.pos]
                        if escaped == 't':
                            chars.add('\t')
                        elif escaped == 'n':
                            chars.add('\n')
                        elif escaped == 's':
                            chars.add(' ')
                        else:
                            chars.add(escaped)
                        self.pos += 1
                    continue

                start = self.input[self.pos]
                self.pos += 1

                if self.pos < len(self.input) and self.input[self.pos] == '-':
                    self.pos += 1
                    if self.pos < len(self.input) and self.input[self.pos] != ']':
                        end = self.input[self.pos]
                        self.pos += 1
                        for c in range(ord(start), ord(end) + 1):
                            chars.add(chr(c))
                    else:
                        chars.add(start)
                        chars.add('-')
                else:
                    chars.add(start)

            if self.pos < len(self.input) and self.input[self.pos] == ']':
                self.pos += 1

            if not chars:
                return RegexNode('CHAR', value='ε')

            if negate:
                all_chars = set(chr(i) for i in range(32, 127))
                chars = all_chars - chars

            return RegexNode('CHARCLASS', value=chars)

        if char == "'":
            self.pos += 1
            if self.pos < len(self.input):
                char_value = self.input[self.pos]
                self.pos += 1
                if self.pos < len(self.input) and self.input[self.pos] == "'":
                    self.pos += 1
                return RegexNode('CHAR', value=char_value)
            return RegexNode('CHAR', value="'")

        if char == '"':
            self.pos += 1
            chars = []
            while self.pos < len(self.input) and self.input[self.pos] != '"':
                if self.input[self.pos] == '\\':
                    self.pos += 1
                    if self.pos < len(self.input):
                        escaped = self.input[self.pos]
                        if escaped == 't':
                            chars.append('\t')
                        elif escaped == 'n':
                            chars.append('\n')
                        elif escaped == 's':
                            chars.append(' ')
                        else:
                            chars.append(escaped)
                else:
                    chars.append(self.input[self.pos])
                self.pos += 1
            
            if self.pos < len(self.input):
                self.pos += 1
            
            if not chars:
                return RegexNode('CHAR', value='ε')
            
            if len(chars) == 1:
                return RegexNode('CHAR', value=chars[0])
            
            result = RegexNode('CHAR', value=chars[0])
            for char in chars[1:]:
                result = RegexNode('CONCAT', left=result, right=RegexNode('CHAR', value=char))
            return result

        if char.isalnum() or char == '_':
            start = self.pos
            while self.pos < len(self.input) and (self.input[self.pos].isalnum() or self.input[self.pos] == '_'):
                self.pos += 1

            ident = self.input[start:self.pos]
            if ident in self.definitions:
                subparser = RegexParser(self.definitions)
                return subparser.parse(self.definitions[ident])
            else:
                return RegexNode('CHAR', value=ident)

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
            if node.value != 'ε':
                start.add_transition(node.value, end)
            else:
                start.add_epsilon_transition(end)
            return start, end

        elif node.type == 'CONCAT':
            left_start, left_end = self._build_node(node.left, nfa)
            right_start, right_end = self._build_node(node.right, nfa)
            left_end.add_epsilon_transition(right_start)
            return left_start, right_end

        elif node.type == 'UNION':
            start = nfa.create_state()
            end = nfa.create_state()
            left_start, left_end = self._build_node(node.left, nfa)
            right_start, right_end = self._build_node(node.right, nfa)
            start.add_epsilon_transition(left_start)
            start.add_epsilon_transition(right_start)
            left_end.add_epsilon_transition(end)
            right_end.add_epsilon_transition(end)
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
            
            if isinstance(node.value, set):
                for char in node.value:
                    start.add_transition(char, end)
            elif node.value == 'ANY':
                for i in range(32, 127):
                    start.add_transition(chr(i), end)
            
            return start, end

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
        self.alphabet = set()
        for state in nfa.states:
            for symbol in state.transitions.keys():
                if symbol != 'ε':
                    self.alphabet.add(symbol)
        
        dfa = DFA()
        start_closure = nfa.epsilon_closure(nfa.start_state)
        dfa.start_state = dfa.create_state(start_closure)
        
        unprocessed = [dfa.start_state]
        state_map = {frozenset(start_closure): dfa.start_state}
        
        while unprocessed:
            current = unprocessed.pop(0)
            
            for symbol in self.alphabet:
                next_nfa_states = set()
                
                for nfa_state in current.nfa_states:
                    if symbol in nfa_state.transitions:
                        next_nfa_states.update(nfa_state.transitions[symbol])
                
                epsilon_closure = set()
                for state in next_nfa_states:
                    epsilon_closure.update(nfa.epsilon_closure(state))
                
                if not epsilon_closure:
                    continue
                
                frozen_closure = frozenset(epsilon_closure)
                
                if frozen_closure not in state_map:
                    new_state = dfa.create_state(epsilon_closure)
                    state_map[frozen_closure] = new_state
                    unprocessed.append(new_state)
                
                current.transitions[symbol] = state_map[frozen_closure]
        
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
            return None
        
        node_id = f"node_{self.counter}"
        self.counter += 1
        
        if node.type in ('CHAR', 'RANGE', 'CHARCLASS'):
            dot.node(node_id, f"{node.type}\\n{node.value}")
        elif node.type in ('CONCAT', 'UNION', 'DIFF'):
            dot.node(node_id, node.type)
            left_id = self._build_graph(dot, node.left)
            right_id = self._build_graph(dot, node.right)
            if left_id:
                dot.edge(node_id, left_id)
            if right_id:
                dot.edge(node_id, right_id)
        else:
            dot.node(node_id, node.type)
            child_id = self._build_graph(dot, node.left)
            if child_id:
                dot.edge(node_id, child_id)
        
        return node_id

class NFAVisualizer:
    def visualize(self, nfa, name="nfa"):
        dot = graphviz.Digraph(name)
        
        for state in nfa.states:
            if state.is_accepting:
                dot.node(str(state.id), shape="doublecircle")
            else:
                dot.node(str(state.id), shape="circle")
            
            for symbol, destinations in state.transitions.items():
                escaped = symbol.replace('\\', '\\\\').replace('"', '\\"')
                for dest in destinations:
                    dot.edge(str(state.id), str(dest.id), label=escaped)
            
            for dest in state.epsilon_transitions:
                dot.edge(str(state.id), str(dest.id), label="ε")
        
        if nfa.start_state:
            dot.node("start", shape="point")
            dot.edge("start", str(nfa.start_state.id))
        
        return dot

class DFAVisualizer:
    def visualize(self, dfa, name="dfa"):
        dot = graphviz.Digraph(name)
        
        for state in dfa.states:
            label = f"{state.id}"
            if state.token_action:
                label += f"\\n{state.token_action}"
            
            if state in dfa.accept_states:
                dot.node(str(state.id), label=label, shape="doublecircle")
            else:
                dot.node(str(state.id), label=label, shape="circle")
            
            for symbol, dest in state.transitions.items():
                escaped_symbol = symbol.replace('\\', '\\\\').replace('"', '\\"')
                dot.edge(str(state.id), str(dest.id), label=escaped_symbol)
        
        if dfa.start_state:
            dot.node("start", shape="point")
            dot.edge("start", str(dfa.start_state.id))
        
        return dot

class LexerGenerator:
    def __init__(self, yalex_file):
        self.yalex_file = yalex_file
        self.yalex_data = None
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
                print(f"Successfully parsed rule: '{regexp}' -> {action}")
            except Exception as e:
                print(f"Error parsing rule: '{regexp}'. Action: {action}. Error: {e}")
                raise e

        return self.regex_trees

    def build_nfas(self):
        if not self.regex_trees:
            raise ValueError("Regex trees not built yet")

        self.nfas = []
        for regex_tree, action in self.regex_trees:
            nfa = self.nfa_builder.build_from_regex(regex_tree)
            for state in nfa.accept_states:
                state.token_action = action
                state.is_accepting = True
            self.nfas.append(nfa)
        return self.nfas

    def build_dfas(self):
        if not self.nfas:
            raise ValueError("NFAs not built yet")

        converter = NFAToDFAConverter()
        self.dfas = []

        for nfa in self.nfas:
            dfa = converter.convert(nfa)
            for state in dfa.accept_states:
                for nfa_state in state.nfa_states:
                    if nfa_state.is_accepting and nfa_state.token_action:
                        state.token_action = nfa_state.token_action
                        break
            self.dfas.append(dfa)
        return self.dfas
    
    def visualize_regex_trees(self, output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)
        visualizer = RegexVisualizer()
        
        for i, (regex_tree, _) in enumerate(self.regex_trees):
            dot = visualizer.visualize(regex_tree, f"regex_tree_{i}")
            dot.render(f"{output_dir}/regex_tree_{i}", format="png", cleanup=True)
    
    def visualize_nfas(self, output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)
        visualizer = NFAVisualizer()
        
        for i, nfa in enumerate(self.nfas):
            dot = visualizer.visualize(nfa, f"nfa_{i}")
            dot.render(f"{output_dir}/nfa_{i}", format="png", cleanup=True)
    
    def visualize_dfas(self, output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)
        visualizer = DFAVisualizer()
        
        for i, dfa in enumerate(self.dfas):
            dot = visualizer.visualize(dfa, f"dfa_{i}")
            dot.render(f"{output_dir}/dfa_{i}", format="png", cleanup=True)
    
    def generate_lexer(self, output_file=None):
        if not output_file:
            output_file = os.path.splitext(self.yalex_file)[0] + ".py"
        
        self.parse_yalex()
        self.build_regex_trees()
        self.build_nfas()
        self.build_dfas()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            if self.yalex_data['header']:
                f.write(f"{self.yalex_data['header']}\n\n")
            
            f.write("from collections import defaultdict\n\n")
            f.write("class Token:\n")
            f.write("    def __init__(self, type, value=None, position=None):\n")
            f.write("        self.type = type\n")
            f.write("        self.value = value\n")
            f.write("        self.position = position\n\n")
            f.write("    def __repr__(self):\n")
            f.write("        if self.value:\n")
            f.write("            return f\"{self.type}({self.value}) at {self.position}\"\n")
            f.write("        return f\"{self.type} at {self.position}\"\n\n")
            
            f.write("class Lexer:\n")
            f.write("    def __init__(self, input_text):\n")
            f.write("        self.input = input_text\n")
            f.write("        self.position = 0\n")
            f.write("        self.line = 1\n")
            f.write("        self.column = 1\n")
            
            # Write the DFA transitions
            f.write("\n        # DFA transitions\n")
            f.write("        self.dfas = []\n")
            for i, dfa in enumerate(self.dfas):
                f.write(f"        # DFA {i}\n")
                f.write(f"        dfa_{i}_states = []\n")
                f.write(f"        dfa_{i}_transitions = []\n")
                
                for state in dfa.states:
                    f.write(f"        # State {state.id}\n")
                    transitions = defaultdict(list)
                    for symbol, dest in state.transitions.items():
                        # Handle special characters properly
                        if symbol == '\n':
                            symbol_repr = "'\\n'"
                        elif symbol == '\t':
                            symbol_repr = "'\\t'"
                        elif symbol == ' ':
                            symbol_repr = "' '"
                        elif symbol == "'":
                            symbol_repr = '"\'"'
                        elif symbol == '"':
                            symbol_repr = "'\"'"
                        elif symbol == '\\':
                            symbol_repr = "'\\\\'"
                        else:
                            symbol_repr = f"'{symbol}'"
                        transitions[dest.id].append(symbol_repr)
                    
                    transition_code = []
                    for dest_id, symbols in transitions.items():
                        transition_code.append(f"({dest_id}, {{{', '.join(symbols)}}})")
                    
                    transition_str = ', '.join(transition_code)
                    f.write(f"        dfa_{i}_transitions.append([{transition_str}])\n")
                    f.write(f"        dfa_{i}_states.append({'True' if state.is_accepting else 'False'})\n")
                
                f.write(f"        self.dfas.append((dfa_{i}_states, dfa_{i}_transitions))\n\n")
            
            # Write the actions
            f.write("        # Token actions\n")
            f.write("        self.actions = [\n")
            for _, action in self.yalex_data['rules']:
                # Extract just the return value without 'return '
                action_value = action.split('return ')[1].strip() if 'return' in action else action
                f.write(f"            '{action_value}',\n")
            f.write("        ]\n\n")
            
            # Write the next_token method
            f.write("    def next_token(self):\n")
            f.write("        if self.position >= len(self.input):\n")
            f.write("            return Token('EOF', position=(self.line, self.column))\n\n")
            
            f.write("        # Skip whitespace (but we actually tokenize it in this case)\n")
            f.write("        # while self.position < len(self.input) and self.input[self.position].isspace():\n")
            f.write("        #     if self.input[self.position] == '\\n':\n")
            f.write("        #         self.line += 1\n")
            f.write("        #         self.column = 1\n")
            f.write("        #     else:\n")
            f.write("        #         self.column += 1\n")
            f.write("        #     self.position += 1\n\n")
            
            f.write("        if self.position >= len(self.input):\n")
            f.write("            return Token('EOF', position=(self.line, self.column))\n\n")
            
            f.write("        longest_match = None\n")
            f.write("        longest_length = 0\n")
            f.write("        matching_action = None\n\n")
            
            f.write("        # Try each DFA to find the longest match\n")
            f.write("        for i, (states, transitions) in enumerate(self.dfas):\n")
            f.write("            current_state = 0  # Start state\n")
            f.write("            current_length = 0\n")
            f.write("            last_accepting_state = None\n")
            f.write("            last_accepting_length = 0\n\n")
            
            f.write("            for j in range(self.position, len(self.input)):\n")
            f.write("                char = self.input[j]\n")
            f.write("                found = False\n")
            f.write("                for dest, symbols in transitions[current_state]:\n")
            f.write("                    if char in symbols:\n")
            f.write("                        current_state = dest\n")
            f.write("                        current_length += 1\n")
            f.write("                        found = True\n")
            f.write("                        if states[current_state]:\n")
            f.write("                            last_accepting_state = current_state\n")
            f.write("                            last_accepting_length = current_length\n")
            f.write("                        break\n")
            f.write("                if not found:\n")
            f.write("                    break\n\n")
            
            f.write("            # Use the last accepting state if we couldn't consume all characters\n")
            f.write("            if last_accepting_state is not None and last_accepting_length > longest_length:\n")
            f.write("                longest_match = self.input[self.position:self.position + last_accepting_length]\n")
            f.write("                longest_length = last_accepting_length\n")
            f.write("                matching_action = self.actions[i]\n\n")
            
            f.write("        if longest_match is not None:\n")
            f.write("            token_type = matching_action\n")
            f.write("            start_pos = (self.line, self.column)\n")
            f.write("            \n")
            f.write("            # Update position\n")
            f.write("            for char in longest_match:\n")
            f.write("                if char == '\\n':\n")
            f.write("                    self.line += 1\n")
            f.write("                    self.column = 1\n")
            f.write("                else:\n")
            f.write("                    self.column += 1\n")
            f.write("            \n")
            f.write("            self.position += longest_length\n")
            f.write("            end_pos = (self.line, self.column)\n")
            f.write("            \n")
            f.write("            return Token(token_type, longest_match, (start_pos, end_pos))\n")
            f.write("        \n")
            f.write("        # No match found - return error token\n")
            f.write("        error_char = self.input[self.position]\n")
            f.write("        error_pos = (self.line, self.column)\n")
            f.write("        self.position += 1\n")
            f.write("        self.column += 1\n")
            f.write("        return Token('ERROR', error_char, error_pos)\n\n")
            
            f.write("    def tokenize(self):\n")
            f.write("        tokens = []\n")
            f.write("        while True:\n")
            f.write("            token = self.next_token()\n")
            f.write("            tokens.append(token)\n")
            f.write("            if token.type == 'EOF':\n")
            f.write("                break\n")
            f.write("        return tokens\n")
            
            if self.yalex_data['trailer']:
                f.write(f"\n{self.yalex_data['trailer']}\n")
        
        print(f"Lexer generated successfully at {output_file}")

# Example usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python yalex_generator.py <input.yal> [output.py]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    generator = LexerGenerator(input_file)
    generator.generate_lexer(output_file)