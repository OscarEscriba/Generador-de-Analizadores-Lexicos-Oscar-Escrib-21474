# test_lexer.py
import sys
from LexerOutput import Lexer, Token

def main():
    # Verificar argumentos de línea de comandos
    if len(sys.argv) != 2:
        print("Uso: python test_lexer.py <archivo_de_entrada.txt>")
        return

    input_file = sys.argv[1]
    
    try:
        # Leer el archivo de entrada
        with open(input_file, 'r', encoding='utf-8') as f:
            input_text = f.read()
        
        # Crear el lexer
        lexer = Lexer(input_text)
        
        # Procesar tokens
        while True:
            token = lexer.next_token()
            print(token)
            if token.type == 'EOF' or token.type == 'ERROR':
                print("Fin del análisis léxico.", KeyError)
                break
                
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{input_file}'")

if __name__ == "__main__":
    main()