import re
from collections import defaultdict
from graphviz import Digraph

class YALexGenerator:
    def __init__(self):
        self.tokens = []
        self.regex_defs = {}
        self.header = ""
        self.trailer = ""
        self.entrypoint = "tokens"
        self.entrypoint_args = []
    
    def parse_yalex_file(self, filename):
        with open(filename, 'r') as file:
            content = file.read()
        
        content = re.sub(r"\(\*.*?\*\)", "", content, flags=re.DOTALL)
        
        sections = re.split(r"(?<=\})\s*|\s*rule\s+", content)
        sections = [s.strip() for s in sections if s.strip()]
        
        if sections and sections[0].startswith('{'):
            self.header = sections[0][1:-1].strip()
            sections.pop(0)
        
        while sections and not sections[0].startswith('{') and '=' in sections[0]:
            line = sections.pop(0)
            ident, regex = line.split('=', 1)
            self.regex_defs[ident.strip()] = regex.strip()
        
        if sections:
            rule_part = sections.pop(0)
            if '=' in rule_part:
                entrypoint_part, rest = rule_part.split('=', 1)
                self.entrypoint = entrypoint_part.strip()
                if '[' in self.entrypoint:
                    self.entrypoint, args = self.entrypoint.split('[', 1)
                    args = args.split(']', 1)[0]
                    self.entrypoint_args = [a.strip() for a in args.split(',')]
                
                rules = rest.split('|')
                for rule in rules:
                    if not rule.strip():
                        continue
                    if '{' in rule:
                        regex_part, action = rule.split('{', 1)
                        action = action.split('}', 1)[0].strip()
                        regex_part = regex_part.strip()
                        expanded_regex = self.expand_regex(regex_part)
                        self.tokens.append((expanded_regex, action))
            
            if sections and sections[0].startswith('{'):
                self.trailer = sections[0][1:-1].strip()
    
    def expand_regex(self, regex):
        for ident in sorted(self.regex_defs.keys(), key=len, reverse=True):
            regex = regex.replace(ident, f"({self.regex_defs[ident]})")
        return regex
    
    def generate_lexer(self, output_filename, language='python'):
        if language.lower() != 'python':
            raise NotImplementedError("Only Python output is currently supported")
        
        try:
            with open(output_filename, 'w') as f:
                if self.header:
                    f.write(self.header + "\n\n")
                
                f.write("import re\n")
                f.write("from collections import defaultdict\n\n")
                
                f.write("class Lexer:\n")
                f.write("    def __init__(self, input_text):\n")
                f.write("        self.input = input_text\n")
                f.write("        self.position = 0\n")
                f.write("        self.current_char = self.input[self.position] if self.input else None\n")
                f.write("        self.line = 1\n")
                f.write("        self.column = 1\n")
                
                f.write("        self.patterns = [\n")
                for regex, action in self.tokens:
                    py_regex = self.yalex_to_python_regex(regex)
                    if action.strip() == 'pass':
                        f.write(f"            (r'{py_regex}', None),\n")
                    else:
                        action_value = action.replace('return', '').strip().strip("'")
                        f.write(f"            (r'{py_regex}', '{action_value}'),\n")
                f.write("        ]\n\n")
                
                f.write("    def advance(self):\n")
                f.write("        if self.current_char == '\\n':\n")
                f.write("            self.line += 1\n")
                f.write("            self.column = 1\n")
                f.write("        else:\n")
                f.write("            self.column += 1\n")
                f.write("        self.position += 1\n")
                f.write("        if self.position < len(self.input):\n")
                f.write("            self.current_char = self.input[self.position]\n")
                f.write("        else:\n")
                f.write("            self.current_char = None\n\n")
                
                f.write("    def skip_whitespace(self):\n")
                f.write("        while self.current_char is not None and self.current_char.isspace():\n")
                f.write("            self.advance()\n\n")
                
                f.write(f"    def {self.entrypoint}(self):\n")
                f.write("        tokens = []\n")
                f.write("        while self.position < len(self.input):\n")
                f.write("            if self.current_char is not None and self.current_char.isspace():\n")
                f.write("                self.skip_whitespace()\n")
                f.write("                continue\n")
                f.write("            \n")
                f.write("            matched = False\n")
                f.write("            for pattern, token_type in self.patterns:\n")
                f.write("                match = re.match(pattern, self.input[self.position:])\n")
                f.write("                if match:\n")
                f.write("                    value = match.group(0)\n")
                f.write("                    if token_type is not None:\n")
                f.write("                        tokens.append((token_type, value))\n")
                f.write("                    self.position += len(value)\n")
                f.write("                    self.current_char = self.input[self.position] if self.position < len(self.input) else None\n")
                f.write("                    matched = True\n")
                f.write("                    break\n")
                f.write("            \n")
                f.write("            if not matched:\n")
                f.write("                raise ValueError(f'Unexpected character {self.current_char} at line {self.line}, column {self.column}')\n")
                f.write("        \n")
                f.write("        return tokens\n\n")
                
                if self.trailer:
                    f.write(self.trailer + "\n")
        except Exception as e:
            print(f"Error al generar el lexer: {e}")
            raise
    
    def yalex_to_python_regex(self, yalex_regex):
        python_regex = yalex_regex
        python_regex = python_regex.replace("\\t", r"\t")
        python_regex = python_regex.replace("\\n", r"\n")
        python_regex = re.sub(r"\[([^\]]+)\]", lambda m: f"[{m.group(1)}]", python_regex)
        python_regex = re.sub(r"\[\^([^\]]+)\]", lambda m: f"[^{m.group(1)}]", python_regex)
        python_regex = python_regex.replace("#", "-")
        python_regex = python_regex.replace('"', r'\"')
        return python_regex.strip()

if __name__ == "__main__":
    try:
        generator = YALexGenerator()
        generator.parse_yalex_file("slr-1.yal")
        generator.generate_lexer("thelexer.py")
        print("Analizador léxico generado exitosamente en 'thelexer.py'")
    except Exception as e:
        print(f"Error durante la generación: {e}")