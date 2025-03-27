# yalex_parser.py
import re
from typing import Dict, List

class YalexParser:
    def __init__(self):
        self.definitions: Dict[str, str] = {}
        self.rules: List[Dict[str, str]] = []
        self.header = ""
        self.trailer = ""

    def parse_file(self, file_path: str) -> None:
        """Parsea un archivo YALex"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self._parse_content(content)

    def _parse_content(self, content: str) -> None:
        """Procesa el contenido YALex"""
        # Eliminar comentarios
        content = re.sub(r'\(\*.*?\*\)', '', content, flags=re.DOTALL)
        
        # Extraer secciones
        self._extract_header_trailer(content)
        self._extract_definitions(content)
        self._extract_rules(content)

    def _extract_header_trailer(self, content: str) -> None:
        """Extrae header y trailer entre llaves"""
        header_match = re.search(r'\{([^}]*)\}', content)
        trailer_match = re.search(r'\}\s*\{([^}]*)\}', content)
        
        if header_match:
            self.header = header_match.group(1).strip()
        if trailer_match:
            self.trailer = trailer_match.group(1).strip()

    def _extract_definitions(self, content: str) -> None:
        """Extrae definiciones 'let'"""
        pattern = r'let\s+(\w+)\s*=\s*([^;]+?)\s*(?=let\s|rule\s|\})'
        for match in re.finditer(pattern, content, re.DOTALL):
            name, regex = match.groups()
            self.definitions[name.strip()] = self._normalize_regex(regex.strip())

    def _extract_rules(self, content: str) -> None:
        """Extrae reglas 'rule tokens'"""
        rule_match = re.search(
            r'rule\s+tokens\s*=\s*\|?(.*?)(?=\s*\{[^}]*\}\s*$)', 
            content, 
            re.DOTALL
        )
        if not rule_match:
            return
            
        rules_text = rule_match.group(1)
        for line in rules_text.split('|'):
            line = line.strip()
            if not line:
                continue
                
            # Separar patrón y acción
            parts = re.split(r'\s*\{', line, maxsplit=1)
            if len(parts) == 2:
                pattern = parts[0].strip()
                action = parts[1].replace('}', '').strip()
                expanded_pattern = self._expand_pattern(pattern)
                self.rules.append({
                    'original': pattern,
                    'pattern': expanded_pattern,
                    'action': action
                })

    def _normalize_regex(self, regex: str) -> str:
        """Normaliza la sintaxis de expresiones regulares"""
        # Convertir [A-Z] a (A|B|...|Z)
        regex = re.sub(r'\[([^\]]+)\]', self._expand_character_class, regex)
        # Remover comillas simples
        regex = re.sub(r"'([^']*)'", r'\1', regex)
        return regex.strip()

    def _expand_character_class(self, match: re.Match) -> str:
        """Expande clases de caracteres como [A-Z0-9]"""
        chars = match.group(1)
        elements = []
        i = 0
        while i < len(chars):
            if i + 2 < len(chars) and chars[i+1] == '-':
                start, end = chars[i], chars[i+2]
                elements.extend([chr(c) for c in range(ord(start), ord(end)+1)])
                i += 3
            else:
                elements.append(chars[i])
                i += 1
        return f"({'|'.join(map(re.escape, elements))})"

    def _expand_pattern(self, pattern: str) -> str:
        """Expande referencias a definiciones"""
        for name, regex in self.definitions.items():
            pattern = pattern.replace(name, f'({regex})')
        return pattern

    def generate_lexer(self, output_file: str = 'lexer.py') -> None:
        """Genera el archivo del lexer"""
        if not self.rules:
            raise ValueError("""
            No se encontraron reglas léxicas. Verifica:
            1. El archivo contiene 'rule tokens = ...'
            2. Las reglas usan el formato '| patron { accion }'
            3. Las definiciones 'let' están antes de las reglas
            """)

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
{self._generate_rule_definitions()}
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
                    f"Carácter inesperado '{{self.text[self.pos]}}' "
                    f"en línea {{self.line}}, columna {{self.column}}"
                )
        return tokens

    def _skip_whitespace(self) -> bool:
        '''Omite espacios en blanco y actualiza posición'''
        match = re.match(r'[ \t\n]+', self.text[self.pos:])
        if match:
            self.line += match.group().count('\\n')
            self.column = match.end() - match.start() + 1 if '\\n' not in match.group() else 1
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

{self.trailer}

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
        print(f"Error léxico: {{e}}")
"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(lexer_code)
        print(f"Lexer generado exitosamente en: {output_file}")

    def _generate_rule_definitions(self) -> str:
        """Genera las definiciones de reglas para el lexer"""
        rule_lines = []
        for rule in self.rules:
            # Escapar solo si es un carácter individual
            pattern = re.escape(rule['pattern']) if len(rule['pattern']) == 1 else rule['pattern']
            action = rule['action']
            rule_lines.append(f"            (r'^{pattern}', {action}),")
        return '\n'.join(rule_lines)

def main():
    parser = YalexParser()
    
    # Solicitar archivo YALex
    yalex_file = input("Ingrese la ruta del archivo YALex (ej: 'slr-1.yal'): ").strip()
    
    try:
        parser.parse_file(yalex_file)
        
        # Opcional: solicitar archivo de salida
        output_file = input(
            "Ingrese el nombre del archivo de salida "
            "(opcional, presione Enter para 'lexer.py'): "
        ).strip() or 'lexer.py'
        
        parser.generate_lexer(output_file)
    except Exception as e:
        print(f"\nError: {e}")
        print("Posibles causas:")
        print("- El archivo no existe o tiene errores de formato")
        print("- Las reglas no siguen el formato esperado")
        print("- Las definiciones 'let' están mal formadas")

if __name__ == '__main__':
    main()