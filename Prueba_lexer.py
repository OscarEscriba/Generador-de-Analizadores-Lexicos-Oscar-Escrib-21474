from thelexer import Lexer
 

def main():
    test_cases = [
        "variable + 12.34E-5 * (x - 5)",
        "123.45 + test_var / (2E+3 - 1)",
        "x1 + 3.14E-2 * (y - 5)"  # Caso adicional
    ]

    for test in test_cases:
        print(f"\nAnalizando: '{test}'")
        lexer = Lexer(test)
        try:
            for token in lexer.tokenize():
                print(f"{token[0]:<10} => {token[1]}")
        except SyntaxError as e:
            print(e)

if __name__ == "__main__":
    main()