## test_lexer.py
# Pruebas del analizador léxico
from lexical_analyzer import LexicalAnalyzer

def run_tests():
    analyzer = LexicalAnalyzer({})  # Se pasará el AFD generado
    test_cases = [
        ("123 + 456", ["NUM", "PLUS", "NUM"]),
        ("var = 10", ["ID", "EQUALS", "NUM"])
    ]
    
    for test_input, expected_output in test_cases:
        result = analyzer.analyze(test_input)
        assert result == expected_output, f"Fallo en {test_input}: {result}"
    
    print("Todas las pruebas pasaron correctamente.")

if __name__ == "__main__":
    run_tests()
