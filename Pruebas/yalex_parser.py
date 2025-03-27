import re
from typing import Dict, List, Tuple, Optional
import sys

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
        try:
            header_match = re.search(r'\{([^}]*)\}', content)
            trailer_match = re.search(r'\}\s*\{([^}]*)\}', content)
            
            self.header = header_match.group(1).strip() if header_match else ""
            self.trailer = trailer_match.group(1).strip() if trailer_match else ""
        except Exception as e:
            print("Error extrayendo secciones:", str(e), file=sys.stderr)
            raise

    def _extract_definitions(self, content: str) -> None:
        try:
            for match in re.finditer(r'let\s+(\w+)\s*=\s*([^;]+?)\s*(?=let\s|rule\s|\})', content, re.DOTALL):
                name, regex = match.groups()
                normalized = self._normalize_regex(regex.strip())
                if self.debug:
                    print(f"[DEBUG] Definición: {name} = {normalized}")
                self.definitions[name.strip()] = normalized
        except Exception as e:
            print("Error procesando definiciones:", str(e), file=sys.stderr)
            raise

    def _extract_rules(self, content: str) -> None:
        try:
            rule_match = re.search(r'rule\s+tokens\s*=\s*\|?(.*?)(?=\s*\{[^}]*\}\s*$)', content, re.DOTALL)
            if not rule_match:
                raise ValueError("No se encontró la sección 'rule tokens'")
            
            for line in rule_match.group(1).split('|'):
                line = line.strip()
                if not line:
                    continue
                    
                if '{' in line:
                    parts = re.split(r'\s*\{', line, maxsplit=1)
                    pattern = parts[0].strip()
                    action = parts[1].replace('}', '').replace('return', '').strip()
                else:
                    pattern = line.strip()
                    action = 'None'
                
                expanded = self._expand_pattern(pattern)
                
                if self.debug:
                    print(f"[DEBUG] Regla: {pattern} -> {expanded} | Acción: {action}")
                
                self.rules.append({
                    'original': pattern,
                    'pattern': expanded,
                    'action': f"'{action}'" if action != 'None' else action
                })
        except Exception as e:
            print("Error procesando reglas:", str(e), file=sys.stderr)
            raise

    def _normalize_regex(self, regex: str) -> str:
        try:
            regex = regex.replace(r'\s', r'[ \t\n]')
            regex = regex.replace(r'\t', r'\t')
            regex = regex.replace(r'\n', r'\n')
            regex = re.sub(r'\[([^\]]+)\]', self._expand_character_class, regex)
            regex = re.sub(r"'([^']*)'", r'\1', regex)
            return regex
        except Exception as e:
            print(f"Error normalizando regex '{regex}': {str(e)}", file=sys.stderr)
            raise

    def _expand_character_class(self, match: re.Match) -> str:
        chars = match.group(1)
        elements = []
        i = 0
        while i < len(chars):
            if i+2 < len(chars) and chars[i+1] == '-':
                start, end = chars[i], chars[i+2]
                if ord(start) > ord(end):
                    raise ValueError(f"Rango inválido: {start}-{end}")
                elements.extend([chr(c) for c in range(ord(start), ord(end)+1)])
                i += 3
            else:
                elements.append(chars[i])
                i += 1
        return f"({'|'.join(map(re.escape, elements))})"

    def _expand_pattern(self, pattern: str) -> str:
        try:
            for name, regex in self.definitions.items():
                pattern = pattern.replace(name, regex)
            
            special_chars = r'\+*?|()[]{}^$.'
            for char in special_chars:
                pattern = pattern.replace(char, f'\\{char}')
                
            return pattern
        except Exception as e:
            print(f"Error expandiendo patrón '{pattern}': {str(e)}", file=sys.stderr)
            raise

    def generate_lexer(self, output_file: str = 'lexer.py') -> None:
        if not self.rules:
            raise ValueError("No hay reglas para generar el lexer")
        
        try:
            ordered_rules = sorted(self.rules, key=lambda x: len(x['pattern']))
            rules_code = self._generate_rule_definitions(ordered_rules)
            
            lexer_code = self._generate_lexer_code(rules_code)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(lexer_code)
            print(f"Lexer generado exitosamente en {output_file}")
            
        except Exception as e:
            print(f"Error generando lexer: {str(e)}", file=sys.stderr)
            raise

    def _generate_rule_definitions(self, rules: List[Dict[str, str]]) -> str:
        rule_lines = []
        for rule in rules:
            pattern = rule['pattern']
            action = rule['action']
            
            try:
                re.compile(pattern)
                rule_lines.append(f"            (r'{pattern}', {action})")
            except re.error:
                print(f"[WARN] Patrón inválido: {pattern}", file=sys.stderr)
                continue
                
        if not rule_lines:
            raise ValueError("No se generaron reglas válidas")
            
        return ',\n'.join(rule_lines)

    def _generate_lexer_code(self, rules_code: str) -> str:
        return f"""# -*- coding: utf-8 -*-
# Lexer generado automáticamente - NO MODIFICAR DIRECTAMENTE
{self.header}

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
                
            token = self._match_next_token()
            if token:
                tokens.append(token)
            else:
                self._report_lexical_error()
        return tokens

    def _skip_whitespace(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            if self.text[self.pos] == '\\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def _match_next_token(self) -> Optional[Tuple[str, str]]:
        for pattern, action in self.rules:
            try:
                match = re.match(pattern, self.text[self.pos:])
                if match:
                    value = match.group()
                    self.pos += len(value)
                    self.column += len(value)
                    return (action.strip(\"'\"), value) if action != 'None' else None
            except re.error as e:
                raise ValueError(f"Error en regex '{pattern}': {str(e)}")
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
            if token:  # Ignorar tokens None (como whitespace)
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

def main():
    try:
        parser = YalexParser(debug=True)
        yalex_file = input("Ingrese la ruta del archivo YALex: ").strip()
        parser.parse_file(yalex_file)
        
        output_file = input("Ingrese el archivo de salida [lexer.py]: ").strip()
        output_file = output_file if output_file else 'lexer.py'
        
        parser.generate_lexer(output_file)
    except Exception as e:
        print(f"\nError fatal: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()