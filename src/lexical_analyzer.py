## lexical_analyzer.py
# Analizador léxico que ejecuta el AFD en una cadena de entrada
class LexicalAnalyzer:
    def __init__(self, afd):
        self.automaton = afd
    
    def analyze(self, input_string):
        tokens = []
        index = 0
        while index < len(input_string):
            token, length = self.match_token(input_string[index:])
            if token:
                tokens.append(token)
                index += length
            else:
                print(f"Error léxico en: {input_string[index]}")
                index += 1
        return tokens
    
    def match_token(self, string):
        # Implementación del reconocimiento de tokens usando el AFD
        pass
