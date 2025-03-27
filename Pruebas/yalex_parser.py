import re
from typing import Dict, List, Tuple

class YalexParser:
    def __init__(self):
        self.definitions: Dict[str, str] = {}
        self.rules: List[Dict[str, str]] = []
        self.header = ""
        self.trailer = ""

    def parse_file(self, file_path: str) -> None:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self._parse_content(content)

    def _parse_content(self, content: str) -> None:
        content = re.sub(r'\(\*.*?\*\)', '', content, flags=re.DOTALL)
        self._extract_header_trailer(content)
        self._extract_definitions(content)
        self._extract_rules(content)

    def _extract_header_trailer(self, content: str) -> None:
        header_match = re.search(r'\{([^}]*)\}', content)
        trailer_match = re.search(r'\}\s*\{([^}]*)\}', content)
        if header_match:
            self.header = header_match.group(1).strip()
        if trailer_match:
            self.trailer = trailer_match.group(1).strip()

    def _extract_definitions(self, content: str) -> None:
        for match in re.finditer(r'let\s+(\w+)\s*=\s*([^;]+?)\s*(?=let\s|rule\s|\})', content, re.DOTALL):
            name, regex = match.groups()
            self.definitions[name.strip()] = self._normalize_regex(regex.strip())

    def _extract_rules(self, content: str) -> None:
        rule_match = re.search(r'rule\s+tokens\s*=\s*\|?(.*?)(?=\s*\{[^}]*\}\s*$)', content, re.DOTALL)
        if not rule_match:
            return
            
        for line in rule_match.group(1).split('|'):
            line = line.strip()
            if not line:
                continue
                
            parts = re.split(r'\s*\{', line, maxsplit=1)
            if len(parts) == 2:
                pattern = parts[0].strip()
                action = parts[1].replace('}', '').replace('return', '').strip()
                self.rules.append({
                    'pattern': self._expand_pattern(pattern),
                    'action': f"'{action}'"  # Asegurar que sea string
                })

    def _normalize_regex(self, regex: str) -> str:
        regex = re.sub(r'\[([^\]]+)\]', self._expand_character_class, regex)
        regex = re.sub(r"'([^']*)'", r'\1', regex)
        regex = regex.replace(r'\s', r'[ \t\n]')
        regex = regex.replace('_', r'\_')  # Escapar guion bajo
        return regex

    def _expand_character_class(self, match: re.Match) -> str:
        chars = match.group(1)
        elements = []
        i = 0
        while i < len(chars):
            if i+2 < len(chars) and chars[i+1] == '-':
                start, end = ord(chars[i]), ord(chars[i+2])
                elements.extend([chr(c) for c in range(start, end+1)])
                i += 3
            else:
                elements.append(chars[i])
                i += 1
        return f"({'|'.join(map(re.escape, elements))})"

    def _expand_pattern(self, pattern: str) -> str:
        # Primero expandir definiciones
        for name, regex in self.definitions.items():
            pattern = pattern.replace(name, regex)
        
        # Manejar caracteres especiales
        special_chars = {'+': r'\+', '*': r'\*', '(': r'\(', ')': r'\)'}
        for char, escaped in special_chars.items():
            pattern = pattern.replace(char, escaped)
        
        return pattern

    def generate_lexer(self, output_file: str = 'lexer.py') -> None:
        if not self.rules:
            raise ValueError("No se encontraron reglas léxicas válidas")

        # Ordenar reglas: tokens simples primero
        simple_tokens = [r for r in self.rules if len(r['pattern']) <= 2]
        complex_tokens = [r for r in self.rules if len(r['pattern']) > 2]
        # Ordenar reglas por longitud (más cortas primero)
        ordered_rules = sorted(self.rules, key=lambda x: len(x['pattern']))

        lexer_code = f"""# -*- coding: utf-8 -*-
{self.header}

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
{self._generate_rule_definitions(ordered_rules)}
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
                    f"Error léxico en línea {{self.line}}, columna {{self.column}}\\n"
                    f"Contexto: '...{{context}}...'\\n"
                    f"Carácter no reconocido: '{{self.text[self.pos]}}'"
                )
        return tokens

    def _skip_whitespace(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            if self.text[self.pos] == '\\n':
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

{self.trailer}

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
        print(f"Error léxico: {{e}}")
"""

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(lexer_code)
        print(f"Lexer generado exitosamente en: {output_file}")

    def _generate_rule_definitions(self, rules: List[Dict[str, str]]) -> str:
        rule_lines = []
        for rule in rules:
            pattern = rule['pattern']
            action = rule['action']
            
            # Asegurar que el patrón sea un regex válido
            if not pattern.startswith('^'):
                pattern = '^' + pattern  # Forzar match desde inicio
                
            rule_lines.append(f"            (r'{pattern}', {action})")
        return ',\n'.join(rule_lines)

def main():
    parser = YalexParser()
    yalex_file = input("Ingrese la ruta del archivo YALex: ").strip()
    try:
        parser.parse_file(yalex_file)
        output_file = input("Ingrese el archivo de salida (opcional): ").strip() or 'lexer.py'
        parser.generate_lexer(output_file)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()