## main.py
# Punto de entrada del generador de analizadores léxicos
from src.lexer_generator import LexerGenerator
import sys

def main():
    if len(sys.argv) < 3:
        print("Uso: python main.py <archivo.yal> -o <salida.py>")
        return
    
    yalex_file = sys.argv[1]
    output_file = sys.argv[3]
    
    generator = LexerGenerator(yalex_file)
    generator.generate_lexer(output_file)
    print(f"Analizador léxico generado en {output_file}")

if __name__ == "__main__":
    main()
