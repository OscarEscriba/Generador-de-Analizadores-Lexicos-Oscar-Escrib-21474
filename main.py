from Parser import LexerGenerator
# Ruta a tu archivo YALex
yalex_file = "slr-1.yal"

# Crear el generador de lexer
generator = LexerGenerator(yalex_file)

# Procesar el archivo YALex
generator.parse_yalex()

# Construir las estructuras internas
generator.build_regex_trees()
generator.build_nfas()
generator.build_dfas()

# Visualizar (opcional)
#generator.visualize_regex_trees()

#generator.visualize_nfas()

#generator.visualize_dfas()

generator.generate_lexer("LexerOutput.py")
print("Lexer generado con éxito: LexerOutput.py") 