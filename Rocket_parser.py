import Rocket_lexer as lexer

# Запускаємо лексичний аналізатор
if lexer.sourceCode:
    FSuccess = ('Rocket', lexer.FSuccess[1])
else:
    FSuccess = ('Rocket', False)

# Глобальні змінні для парсера
numRow = 1
len_tableOfSymb = len(lexer.tableOfLex)
print(('len_tableOfSymb', len_tableOfSymb))


def parseProgram():
    global numRow
    print("\nParser Log (Syntax Analysis Only):")
    while numRow <= len_tableOfSymb:
        # Перевіряємо, чи ми не в кінці файлу перед тим, як читати токен
        if numRow > len_tableOfSymb:
            break
        _, lex, tok, _ = getSymb()
        if lex in ('int', 'float', 'bool', 'string'):
            if numRow + 2 < len_tableOfSymb and lexer.tableOfLex[numRow + 2][1] == '(':
                parseFunctionDeclaration()
            else:
                parseDeclaration()
        elif lex in ('if', 'switch', 'while', 'do', 'for', 'print', 'return') or tok == 'id':
            parseStatement()
        elif tok == 'comment':
            numRow += 1
        elif lex in ('{', '}'):
            numRow += 1
        else:
            failParse('instruction mismatch',
                      (getSymb()[0], lex, tok, 'Expected global declaration, function, or statement'))


def parseDeclaration():
    indent = nextIndt()
    print(indent + 'parseDeclaration():')
    global numRow

    # Синтаксис: type id [= expression] ;
    parseToken(getSymb()[1], 'keyword')  # Тип

    id_line, id_lex, id_tok, _ = getSymb()
    if id_tok != 'id':
        failParse('token mismatch', (id_line, id_lex, id_tok, 'expected identifier'))
    numRow += 1

    if numRow <= len_tableOfSymb and getSymb()[1] == '=':
        parseToken('=', 'assign_op')
        parseExpression()

    parseToken(';', 'punct')
    predIndt()


def parseStatement():
    indent = nextIndt()
    print(indent + 'parseStatement():')
    _, lex, tok, _ = getSymb()

    if tok == 'id':
        parseAssign()
    elif lex == 'if':
        parseIf()
    elif lex == 'while':
        parseWhile()
    elif lex == 'do':
        parseDoWhile()
    elif lex == 'for':
        parseFor()
    elif lex == 'switch':
        parseSwitch()
    elif lex == 'print':
        parsePrint()
    elif lex == 'return':
        parseReturnStatement()
    else:
        failParse('instruction mismatch', (getSymb()[0], lex, tok, 'expected a statement'))
    predIndt()


def parseReturnStatement():
    indent = nextIndt()
    print(indent + 'parseReturnStatement():')

    parseToken('return', 'keyword')
    # return може бути без виразу (для void) або з виразом. Перевірка, чи наступний токен не крапка з комою
    if getSymb()[1] != ';':
        parseExpression()

    parseToken(';', 'punct')
    predIndt()


def parseAssign():
    indent = nextIndt()
    print(indent + 'parseAssign():')
    global numRow

    # Синтаксис: id assign_op expression ;
    if getSymb()[2] != 'id':
        failParse('token mismatch', (getSymb()[0:3], 'expected identifier for assignment'))
    numRow += 1

    if getSymb()[2] != 'assign_op':
        failParse('token mismatch', (getSymb()[0:3], 'expected assignment operator (=, +=, etc.)'))
    numRow += 1

    # Перевірка на спеціальні функції вводу (синтаксично вони є виразом)
    next_lex = getSymb()[1]
    input_functions = {'inputInt', 'inputFloat', 'inputBool', 'inputString'}
    if next_lex in input_functions:
        parseToken(next_lex, 'id')
        parseToken('(', 'brackets_op')
        parseToken(')', 'brackets_op')
    else:
        parseExpression()

    parseToken(';', 'punct')
    predIndt()


def parseIf():
    indent = nextIndt()
    print(indent + 'parseIf():')
    global numRow

    parseToken('if', 'keyword')
    parseToken('(', 'brackets_op')
    parseBooleanCondition()
    parseToken(')', 'brackets_op')
    parseToken('{', 'brackets_op')

    while numRow <= len_tableOfSymb and getSymb()[1] != '}':
        parseStatement()
    parseToken('}', 'brackets_op')

    while numRow <= len_tableOfSymb and getSymb()[1] == 'elif':
        print(indent + '  found elif')
        parseToken('elif', 'keyword')
        parseToken('(', 'brackets_op')
        parseBooleanCondition()
        parseToken(')', 'brackets_op')
        parseToken('{', 'brackets_op')
        while numRow <= len_tableOfSymb and getSymb()[1] != '}':
            parseStatement()
        parseToken('}', 'brackets_op')

    if numRow <= len_tableOfSymb and getSymb()[1] == 'else':
        print(indent + '  found else')
        parseElse()
    predIndt()


def parseElse():
    parseToken('else', 'keyword')
    parseToken('{', 'brackets_op')
    while numRow <= len_tableOfSymb and getSymb()[1] != '}':
        parseStatement()
    parseToken('}', 'brackets_op')


def parseWhile():
    indent = nextIndt()
    print(indent + 'parseWhile():')
    parseToken('while', 'keyword')
    parseToken('(', 'brackets_op')
    parseBooleanCondition()
    parseToken(')', 'brackets_op')
    parseToken('{', 'brackets_op')
    while numRow <= len_tableOfSymb and getSymb()[1] != '}':
        parseStatement()
    parseToken('}', 'brackets_op')
    predIndt()


def parseDoWhile():
    indent = nextIndt()
    print(indent + 'parseDoWhile():')
    parseToken('do', 'keyword')
    parseToken('{', 'brackets_op')
    while numRow <= len_tableOfSymb and getSymb()[1] != '}':
        parseStatement()
    parseToken('}', 'brackets_op')
    parseToken('while', 'keyword')
    parseToken('(', 'brackets_op')
    parseBooleanCondition()
    parseToken(')', 'brackets_op')
    parseToken(';', 'punct')
    predIndt()


def parseFor():
    indent = nextIndt()
    print(indent + 'parseFor():')
    global numRow

    parseToken('for', 'keyword')
    parseToken('(', 'brackets_op')
    parseDeclaration()
    parseBooleanCondition()
    parseToken(';', 'punct')

    # Ручний розбір інкремента (виразу присвоєння)
    if getSymb()[2] != 'id':
        failParse('token mismatch', (getSymb()[0:3], 'expected identifier in for increment'))
    numRow += 1
    if getSymb()[2] != 'assign_op':
        failParse('token mismatch', (getSymb()[0:3], 'expected assignment operator'))
    numRow += 1
    parseExpression()

    parseToken(')', 'brackets_op')
    parseToken('{', 'brackets_op')
    while numRow <= len_tableOfSymb and getSymb()[1] != '}':
        parseStatement()
    parseToken('}', 'brackets_op')
    predIndt()


def parseSwitch():
    indent = nextIndt()
    print(indent + 'parseSwitch():')
    global numRow

    parseToken('switch', 'keyword')
    if getSymb()[2] != 'id':
        failParse('token mismatch', (getSymb()[0:3], 'expected identifier after switch'))
    numRow += 1
    parseToken('{', 'brackets_op')

    while numRow <= len_tableOfSymb and getSymb()[1] in ('case', 'default'):
        if getSymb()[1] == 'case':
            parseCase()
        else:
            parseDefault()
    parseToken('}', 'brackets_op')
    predIndt()


def parseCase():
    indent = nextIndt()
    print(indent + 'parseCase():')
    global numRow

    parseToken('case', 'keyword')
    tok = getSymb()[2]
    if tok not in ('intnum', 'realnum', 'stringval'):
        failParse('token mismatch', (getSymb()[0:3], 'expected a constant value'))
    numRow += 1
    parseToken(':', 'punct')

    while numRow <= len_tableOfSymb and getSymb()[1] not in ('case', 'default', '}'):
        parseStatement()
    predIndt()


def parseDefault():
    indent = nextIndt()
    print(indent + 'parseDefault():')
    parseToken('default', 'keyword')
    parseToken(':', 'punct')
    while numRow <= len_tableOfSymb and getSymb()[1] != '}':
        parseStatement()
    predIndt()


def parsePrint():
    indent = nextIndt()
    print(indent + 'parsePrint():')
    parseToken('print', 'keyword')
    parseToken('(', 'brackets_op')
    parseExpression()
    parseToken(')', 'brackets_op')
    parseToken(';', 'punct')
    predIndt()


def parseFunctionDeclaration():
    indent = nextIndt()
    print(indent + 'parseFunctionDeclaration():')
    global numRow
    # 1. Тип, що повертається
    parseToken(getSymb()[1], 'keyword')
    # 2. Ім'я функції
    if getSymb()[2] != 'id':
        failParse('token mismatch', (getSymb()[0:3], 'expected function name'))
    numRow += 1
    # 3. Список параметрів
    parseToken('(', 'brackets_op')
    if getSymb()[1] != ')':
        parseParameterList()
    parseToken(')', 'brackets_op')
    # 4. Тіло функції (викликаємо parseBlock)
    parseBlock()
    predIndt()


def parseBlock():
    indent = nextIndt()
    print(indent + 'parseBlock():')
    global numRow
    # Синтаксис блоку: { (Declaration | Statement)* }
    parseToken('{', 'brackets_op')

    while numRow <= len_tableOfSymb and getSymb()[1] != '}':
        # Логіка всередині блоку ідентична головному циклу програми
        _, lex, tok, _ = getSymb()

        if lex in ('int', 'float', 'bool', 'string'):
            # Перевіряємо, чи це оголошення функції, чи змінної
            if numRow + 1 < len_tableOfSymb and lexer.tableOfLex[numRow + 2][1] == '(':
                parseFunctionDeclaration()
            else:
                parseDeclaration()
        elif lex in ('if', 'switch', 'while', 'do', 'for', 'print', 'return') or tok == 'id':
            parseStatement()
        elif tok == 'comment':
            numRow += 1
        elif lex in ('{', '}'):  # Порожні вкладені блоки
            numRow += 1
        else:
            failParse('instruction mismatch',
                      (getSymb()[0], lex, tok, 'Expected declaration or statement inside block'))

    parseToken('}', 'brackets_op')
    predIndt()


def parseParameterList():
    indent = nextIndt()
    print(indent + 'parseParameterList():')
    global numRow
    # Перший параметр
    parseToken(getSymb()[1], 'keyword')  # Тип параметра
    if getSymb()[2] != 'id':
        failParse('token mismatch', (getSymb()[0:3], 'expected parameter name'))
    numRow += 1
    # Наступні параметри (якщо є)
    while numRow <= len_tableOfSymb and getSymb()[1] == ',':
        numRow += 1  # Пропускаємо кому
        parseToken(getSymb()[1], 'keyword')  # Тип параметра
        if getSymb()[2] != 'id':
            failParse('token mismatch', (getSymb()[0:3], 'expected parameter name'))
        numRow += 1

    predIndt()


def parseBooleanCondition():
    indent = nextIndt()
    print(indent + 'parseBooleanCondition():')
    # Синтаксично, будь-який вираз може бути умовою
    parseExpression()
    predIndt()


def parseExpression():
    indent = nextIndt()
    print(indent + 'parseExpression():')

    parseOr()  # Починаємо з найнижчого пріоритету

    # Обробка тернарного оператора
    if numRow <= len_tableOfSymb and getSymb()[1] == '?':
        parseToken('?', 'tern_op')
        parseExpression()
        parseToken(':', 'punct')
        parseExpression()

    predIndt()


def parseOr():
    indent = nextIndt()
    print(indent + 'parseOr():')
    global numRow
    parseAnd()
    while numRow <= len_tableOfSymb and getSymb()[1] == '||':
        numRow += 1
        parseAnd()
    predIndt()


def parseAnd():
    indent = nextIndt()
    print(indent + 'parseAnd():')
    global numRow
    parseRel()
    while numRow <= len_tableOfSymb and getSymb()[1] == '&&':
        numRow += 1
        parseRel()
    predIndt()


def parseRel():
    indent = nextIndt()
    print(indent + 'parseRel():')
    global numRow
    parseArithmExpression()
    if numRow <= len_tableOfSymb and getSymb()[2] == 'rel_op':
        numRow += 1
        parseArithmExpression()
    predIndt()


def parseArithmExpression():
    indent = nextIndt()
    print(indent + 'parseArithmExpression():')
    global numRow
    parseTerm()
    while numRow <= len_tableOfSymb and getSymb()[2] == 'add_op':
        numRow += 1
        parseTerm()
    predIndt()


def parseTerm():
    indent = nextIndt()
    print(indent + 'parseTerm():')
    global numRow
    parsePower()
    while numRow <= len_tableOfSymb and getSymb()[2] == 'mult_op':
        numRow += 1
        parsePower()
    predIndt()


def parsePower():
    indent = nextIndt()
    print(indent + 'parsePower():')
    global numRow
    parseFactor()
    if numRow <= len_tableOfSymb and getSymb()[2] == 'pow_op':
        numRow += 1
        parseFactor()
    predIndt()


def parseFactor():
    indent = nextIndt()
    print(indent + 'parseFactor():')
    global numRow

    line, lex, tok, _ = getSymb()

    if (lex, tok) in (('+', 'add_op'), ('-', 'add_op')):
        numRow += 1
        parseFactor()
    elif tok in ('intnum', 'realnum', 'stringval', 'boolval'):
        numRow += 1
    elif tok == 'id':
        # Заглядаємо наперед, щоб відрізнити змінну від виклику функції
        if numRow + 1 < len_tableOfSymb and lexer.tableOfLex[numRow + 1][1] == '(':
            parseFunctionCall()
        else:  # Це звичайна змінна
            numRow += 1
    # --- КІНЕЦЬ ОНОВЛЕННЯ ---
    elif lex == '(':
        parseToken('(', 'brackets_op')
        parseExpression()
        parseToken(')', 'brackets_op')
    elif lex == '!':
        numRow += 1
        parseFactor()
    else:
        failParse('token mismatch',
                  (line, lex, tok, 'expected number, identifier, expression, or unary operator'))
    predIndt()


def parseFunctionCall():
    indent = nextIndt()
    print(indent + 'parseFunctionCall():')
    global numRow
    # Синтаксис: id ( [arguments] )
    if getSymb()[2] != 'id':
        failParse('token mismatch', (getSymb()[0:3], 'expected function name for a call'))
    numRow += 1

    parseToken('(', 'brackets_op')
    if getSymb()[1] != ')':
        parseArgumentList()
    parseToken(')', 'brackets_op')
    predIndt()


def parseArgumentList():
    indent = nextIndt()
    print(indent + 'parseArgumentList():')
    global numRow

    # Синтаксис: expression [, expression]*
    parseExpression()  # Перший аргумент

    while numRow <= len_tableOfSymb and getSymb()[1] == ',':
        numRow += 1  # Пропускаємо кому
        parseExpression()  # Наступний аргумент

    predIndt()


def parseToken(lexeme, token):
    global numRow
    indent = nextIndt()

    if numRow > len_tableOfSymb:
        failParse('Unexpected end of program', (lexeme, token, numRow))

    numLine, lex, tok, _ = getSymb()

    if (lex, tok) == (lexeme, token):
        print(indent + f'parseToken: in line {numLine}, got token {(lexeme, token)}')
        numRow += 1
        predIndt()
        return True
    else:
        failParse('token mismatch', (numLine, lex, tok, lexeme, token))
        return False


def getSymb():
    if numRow > len_tableOfSymb:
        failParse('getSymb(): Unexpected end of program', numRow)
    return lexer.tableOfLex[numRow]


def failParse(str_msg, details):
    if str_msg == 'Unexpected end of program':
        lexeme, token, row = details
        print(
            f'Parser ERROR: \n\t Unexpected end of program. Expected ({lexeme}, {token}), but token table ended at row {row - 1}.')
    elif str_msg == 'getSymb(): Unexpected end of program':
        row = details
        print(
            f'Parser ERROR: \n\t Attempted to read row {row} from token table, which only has {len_tableOfSymb} entries.')
    elif str_msg == 'token mismatch':
        if len(details) == 5:
            numLine, lexeme, token, expected_lex, expected_tok = details
            print(
                f'Parser ERROR: \n\t Unexpected token ({lexeme},{token}) in line {numLine}. \n\t Expected - ({expected_lex},{expected_tok}).')
        else:
            numLine, lexeme, token, expected = details
            print(
                f'Parser ERROR: \n\t Unexpected token ({lexeme},{token}) in line {numLine}. \n\t Expected - {expected}.')
    else:
        numLine, lex, tok, expected = details
        print(f'Parser ERROR: \n\t {str_msg} ({lex},{tok}) in line {numLine}. \n\t Expected - {expected}.')
    exit(1)


stepIndt = 2
indt = -2


def nextIndt():
    global indt
    indt += stepIndt
    return ' ' * indt


def predIndt():
    global indt
    indt -= stepIndt
    return ' ' * indt


# ----------------- Основний запуск -----------------
if FSuccess == ('Rocket', True):
    try:
        parseProgram()
        print("\nPARSER SUCCESS")
    except SystemExit:
        print(f"\nPARSER FAIL")
else:
    print("\nPARSER FAIL DUE TO LEXER FAIL")
