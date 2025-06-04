from slr2 import Lexer

text1 = "x + y * (z123)"
text2 = "370860  vsuzzzf     	6   367882 "
text3 = "9.49E-9     /	gweaxj	)   	)    *   	jbyfkxqcfn	sokqmzyik "
lexer = Lexer(text3)
tokens = lexer.tokenize()

for token in tokens:
    print(token)