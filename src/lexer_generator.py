## lexer_generator.py
# Generador del analizador léxico basado en la definición de YALex
from src.token_definition import TokenDefinition
from src.regex_to_afd import RegexToDFA
from src.afd_union import AFDUnion

class LexerGenerator:
    def __init__(self, yalex_file):
        self.yalex_file = yalex_file
        self.token_definitions = []
    
    def parse_yalex(self):
        with open(self.yalex_file, "r") as file:
            lines = file.readlines()
        
        for line in lines:
            if "=" in line:
                token_name, regex = map(str.strip, line.split("="))
                self.token_definitions.append(TokenDefinition(token_name, regex))
    
    def generate_lexer(self, output_file):
        self.parse_yalex()
        afds = [RegexToDFA(token.regex).construct_dfa() for token in self.token_definitions]
        unified_afd = AFDUnion(afds).combine()
        
        with open(output_file, "w") as out:
            out.write("# Analizador léxico generado\n")
            out.write("class Lexer:\n")
            out.write("    def __init__(self):\n")
            out.write("        self.automaton = {}\n")  # Aquí se insertará el AFD final
