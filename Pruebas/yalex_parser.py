import re
from typing import Dict, List, Tuple, Optional
import sys
from graphviz import Digraph  # Para generar el árbol de expresión

class ExpressionTreeNode:
    def __init__(self, value: str, left: Optional['ExpressionTreeNode'] = None, right: Optional['ExpressionTreeNode'] = None):
        self.value = value
        self.left = left
        self.right = right

class YalexParser:
    def __init__(self, debug: bool = True):
        self.definitions: Dict[str, str] = {}
        self.rules: List[Dict[str, str]] = []
        self.header = ""
        self.trailer = ""
        self.debug = debug

    def parse_file(self, file_path: str) -> None:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self._parse_content(content)
            if self.debug:
                self._debug_print_parsed_data()
        except Exception as e:
            print(f"Error al parsear archivo: {str(e)}", file=sys.stderr)
            raise

    def _parse_content(self, content: str) -> None:
        content = self._remove_comments(content)
        self._extract_sections(content)
        self._extract_definitions(content)
        self._extract_rules(content)

    def _remove_comments(self, content: str) -> str:
        return re.sub(r'\(\*.*?\*\)', '', content, flags=re.DOTALL)

    def _extract_sections(self, content: str) -> None:
        header_match = re.search(r'\{([^}]*)\}', content)
        trailer_match = re.search(r'\}\s*\{([^}]*)\}', content)
        
        self.header = header_match.group(1).strip() if header_match else ""
        self.trailer = trailer_match.group(1).strip() if trailer_match else ""

    def _extract_definitions(self, content: str) -> None:
        def_matches = re.finditer(r'let\s+(\w+)\s*=\s*([^;]+?)\s*(?=let\s|rule\s|\})', content, re.DOTALL)
        for match in def_matches:
            name, regex = match.groups()
            normalized = self._normalize_regex(regex.strip())
            self.definitions[name.strip()] = normalized

    def _normalize_regex(self, regex: str) -> str:
        regex = regex.replace(r"'\t'", r'\t')
        regex = regex.replace(r"'\n'", r'\n')
        regex = regex.replace(r"' '", ' ')
        regex = re.sub(r'\[([^\]]+)\]', self._expand_character_class, regex)
        regex = regex.replace('+', '*')
        regex = regex.replace("'", "")
        return regex

    def _expand_character_class(self, match: re.Match) -> str:
        chars = match.group(1)
        elements = []
        i = 0
        while i < len(chars):
            if i + 2 < len(chars) and chars[i+1] == '-':
                start, end = chars[i], chars[i+2]
                elements.append(f"{start}-{end}")
                i += 3
            else:
                elements.append(re.escape(chars[i]))
                i += 1
        return f"[{''.join(elements)}]"

    def _extract_rules(self, content: str) -> None:
        rule_match = re.search(r'rule\s+tokens\s*=\s*\|?(.*?)(?=\s*\{[^}]*\}\s*$)', content, re.DOTALL)
        if not rule_match:
            raise ValueError("No se encontró la sección 'rule tokens'")
        
        for line in rule_match.group(1).split('|'):
            line = line.strip()
            if not line:
                continue

            action = 'None'
            if '{' in line:
                parts = re.split(r'\s*\{', line, maxsplit=1)
                pattern = parts[0].strip()
                action = parts[1].split('}')[0].replace('return', '').strip()
            else:
                pattern = line.strip()
            
            expanded = self._expand_pattern(pattern)
            self.rules.append({
                'original': pattern,
                'pattern': expanded,
                'action': action if action != 'None' else None
            })

    def _expand_pattern(self, pattern: str) -> str:
        definitions_copy = self.definitions.copy()
        
        for name, value in sorted(definitions_copy.items(), key=lambda x: len(x[0]), reverse=True):
            if name in pattern:
                pattern = pattern.replace(name, f"({value})")
        
        if pattern.startswith("'") and pattern.endswith("'"):
            pattern = re.escape(pattern.strip("'"))
        
        if not pattern.startswith('^'):
            pattern = '^' + pattern
        
        return pattern

    def generate_lexer(self, output_file: str = 'lexer.py') -> None:
        if not self.rules:
            raise ValueError("No hay reglas para generar el lexer")
        
        ordered_rules = sorted(self.rules, key=lambda x: len(x['pattern']), reverse=True)
        rules_code = self._generate_rule_definitions(ordered_rules)
        
        lexer_code = self._generate_lexer_code(rules_code)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(lexer_code)
        print(f"Lexer generado exitosamente en {output_file}")

    def _generate_rule_definitions(self, rules: List[Dict[str, str]]) -> str:
        rule_lines = []
        for rule in rules:
            pattern = rule['pattern']
            action = rule['action']
            
            try:
                re.compile(pattern)
                if action:
                    rule_lines.append(f"            (r'{pattern}', '{action}')")
                else:
                    rule_lines.append(f"            (r'{pattern}', None)")
            except re.error as e:
                print(f"[WARN] Patrón inválido: {pattern} - {e}", file=sys.stderr)
        
        return ',\n'.join(rule_lines)

    def _generate_lexer_code(self, rules_code: str) -> str:
        return f"""# -*- coding: utf-8 -*-
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
{rules_code}
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
            if self.text[self.pos] == '\\n':
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
            f"Error léxico en línea {{self.line}}, columna {{self.column}}\\n"
            f"Contexto: '...{{context}}...'\\n"
            f"Carácter no reconocido: '{{self.text[self.pos]}}'"
        )

{self.trailer}

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
        print(f"Error: {{str(e)}}", file=sys.stderr)
        sys.exit(1)
"""

    def _debug_print_parsed_data(self) -> None:
        print("\n[DEBUG] Definiciones:")
        for name, regex in self.definitions.items():
            print(f"  {name}: {regex}")
        
        print("\n[DEBUG] Reglas:")
        for i, rule in enumerate(self.rules, 1):
            print(f"  {i}. {rule['original']} -> {rule['pattern']} | {rule['action']}")
        
        print("\n[DEBUG] Header:", self.header[:50] + "..." if len(self.header) > 50 else self.header)
        print("[DEBUG] Trailer:", self.trailer[:50] + "..." if len(self.trailer) > 50 else self.trailer)

    def generate_and_visualize_global_expression_tree(self) -> None:
        """
        Genera y visualiza un único árbol de expresión combinando todas las definiciones del archivo YALex.
        Cada definición será combinada con el operador '|' para formar una expresión global.
        """
        # Combinar todas las expresiones con el operador '|', para formar una expresión global
        global_regex = '|'.join(self.definitions.values())  # Unir todas las expresiones con '|' (OR)
        print(f"Generando árbol de expresión global: {global_regex}")
        
        # Generar el árbol para la expresión global
        tree = self.generate_expression_tree(global_regex)  # Generar árbol de la expresión global
        self.visualize_expression_tree(tree)  # Visualizar el árbol

    def generate_expression_tree(self, regex: str) -> ExpressionTreeNode:
        """
        Genera un árbol de expresión a partir de una expresión regular en notación postfix.
        """
        stack = []
        for char in regex:
            if char in '()*|':
                # Manejo de operadores: 
                if char in '|*+':  # En caso de que sea un operador de uno de los lados
                    right = stack.pop() if char in '|*+' else None
                    left = stack.pop() if char not in '|*+' else None
                    node = ExpressionTreeNode(value=char, left=left, right=right)
                else:  # En caso de que sea un operador binario
                    node = ExpressionTreeNode(value=char, left=stack.pop(), right=stack.pop())
                stack.append(node)
            else:
                stack.append(ExpressionTreeNode(value=char))
        
        return stack[-1] if stack else None

    def visualize_expression_tree(self, root: ExpressionTreeNode) -> None:
        """
        Visualiza el árbol de expresión utilizando graphviz.
        """
        dot = Digraph(comment='Árbol de Expresión Regular')
        self._add_nodes(dot, root)
        dot.render('expression_tree', format='png', view=True)

    def _add_nodes(self, dot: Digraph, node: ExpressionTreeNode, parent=None) -> None:
        """
        Agrega los nodos y las conexiones al gráfico recursivamente.
        """
        if node:
            dot.node(str(id(node)), node.value)
            if parent:
                dot.edge(str(id(parent)), str(id(node)))
            if node.left:
                self._add_nodes(dot, node.left, node)
            if node.right:
                self._add_nodes(dot, node.right, node)
                
if __name__ == '__main__':
    try:
        parser = YalexParser(debug=True)
        yalex_file = input("Ingrese la ruta del archivo YALex: ").strip()
        parser.parse_file(yalex_file)  # Analiza el archivo YALex
        
        # Genera y visualiza el árbol de expresión global
        parser.generate_and_visualize_global_expression_tree()
        
        output_file = input("Ingrese el archivo de salida [lexer.py]: ").strip()
        output_file = output_file if output_file else 'lexer.py'
        
        parser.generate_lexer(output_file)
    except Exception as e:
        print(f"\nError fatal: {str(e)}", file=sys.stderr)
        sys.exit(1)

