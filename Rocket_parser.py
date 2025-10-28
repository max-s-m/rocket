import Rocket_lexer as lexer
import Rocket_symbol_table as st

# Запускаємо лексичний аналізатор
# FSuccess буде ('Rocket', True) у разі успіху
if lexer.sourceCode:
    FSuccess = ('Rocket', lexer.FSuccess[1])
else:
    FSuccess = ('Rocket', False)

# Виводимо таблицю лексем, яку отримали від лексера
print('-' * 50)
print('Table of Lexemes (from Rocket_lexer):')
# Використовуємо функцію друку з лексера, якщо вона існує
if hasattr(lexer, 'format_table_of_symb_tabular'):
    print(lexer.format_table_of_symb_tabular(lexer.tableOfLex))
else:
    print(lexer.tableOfLex)
print('-' * 50)

# Глобальні змінні для парсера
numRow = 1
len_tableOfSymb = len(lexer.tableOfLex)
print(('len_tableOfSymb', len_tableOfSymb))


def parseProgram():
    global numRow
    print("\nParser Log:")
    while numRow <= len_tableOfSymb:
        numLine, lex, tok, _ = getSymb()

        # Оголошення змінної (починається з типу)
        if lex in ('int', 'float', 'bool', 'string'):
            parseDeclaration()
        # Оголошення функції
        elif lex == 'function':
            parseFunctionDeclaration()
        # Інструкції
        elif lex in ('if', 'switch', 'while', 'do', 'for', 'print') or tok == 'id':
            parseStatement()
        # Коментарі
        elif tok == 'comment':
            numRow += 1  # Просто пропускаємо коментар
        # Порожні блоки
        elif lex in ('{', '}'):
            numRow += 1
        else:
            failParse('instruction mismatch',
                      (numLine, lex, tok, 'Expected declaration of var, func, or instruction'))


def parseDeclaration():
    indent = nextIndt()
    print(indent + 'parseDeclaration():')
    global numRow

    # 1. Отримуємо тип
    numLine, declared_type, tok, _ = getSymb()
    parseToken(declared_type, 'keyword')

    # 2. Отримуємо ідентифікатор
    id_line, id_lex, id_tok, _ = getSymb()
    if id_tok != 'id':
        failParse('token mismatch', (id_line, id_lex, id_tok, 'expected id'))
    numRow += 1

    # 3. Перевірка на ініціалізацію
    val_status = 'undefined'
    if numRow <= len_tableOfSymb and getSymb()[1] == '=':
        parseToken('=', 'assign_op')

        # 4. Отримуємо тип виразу
        expr_type = parseExpression()

        # 5. Семантична перевірка типів
        st.check_assign(declared_type, expr_type, numLine)
        val_status = 'assigned'

    # 6. Додаємо ідентифікатор в таблицю символів
    attr = (len(st.tabName[st.currentContext]) - 1, 'variable', declared_type, val_status, '-')
    st.insertName(st.currentContext, id_lex, id_line, attr)

    # 7. Очікуємо крапку з комою
    parseToken(';', 'punct')

    predIndt()


def parseStatement():
    indent = nextIndt()
    print(indent + 'parseStatement():')

    numLine, lex, tok, _ = getSymb()

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
    else:
        failParse('instruction mismatch', (numLine, lex, tok, 'expected instruction'))

    predIndt()


def parseAssign():
    indent = nextIndt()
    print(indent + 'parseAssign():')
    global numRow

    # 1. Перевіряємо l-value (ідентифікатор)
    id_line, id_lex, id_tok, _ = getSymb()
    if id_tok != 'id':
        failParse('token mismatch', (id_line, id_lex, id_tok, 'expected id for assignment'))

    cxt_found, name, attr = st.findName(id_lex, st.currentContext, id_line)
    id_type = attr[2]
    numRow += 1

    # 2. Отримуємо оператор присвоєння
    assign_line, assign_lex, assign_tok, _ = getSymb()
    if assign_tok != 'assign_op':
        failParse('token mismatch',
                  (assign_line, assign_lex, assign_tok, 'assign op (=, +=, -=, *=, /=)'))
    numRow += 1

    # 3. Перевіряємо, чи це спеціальна функція вводу
    next_line, next_lex, next_tok, _ = getSymb()
    input_map = {
        'inputInt': 'int', 'inputFloat': 'float',
        'inputBool': 'bool', 'inputString': 'string'
    }

    if next_lex in input_map:
        st.check_assign(id_type, input_map[next_lex], assign_line)
        # Функції вводу розпізнаються як id, але лексер не знає про них, тому токен буде 'id'
        # Потрібно перевіряти лексему.
        parseToken(next_lex, 'id')
        parseToken('(', 'brackets_op')
        parseToken(')', 'brackets_op')
    else:
        # 4. Або це звичайний вираз
        expr_type = parseExpression()

        if assign_lex == '=':
            st.check_assign(id_type, expr_type, assign_line)
        else:  # Складне присвоєння (+=, -=, ...)
            op_map = {'+=': '+', '-=': '-', '*=': '*', '/=': '/'}
            arith_op = op_map.get(assign_lex)

            # Перевіряємо, чи сама операція (a + b) валідна
            result_type = st.check_arithm_op(id_type, arith_op, expr_type, assign_line)
            # Перевіряємо, чи можна результат присвоїти назад до 'a'
            st.check_assign(id_type, result_type, assign_line)

    # 5. Очікуємо крапку з комою
    parseToken(';', 'punct')

    # 6. Позначаємо змінну як ініціалізовану
    st.updateNameVal(id_lex, st.currentContext, id_line, 'assigned')

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

    # Спочатку обробляються всі можливі 'elif' у ланцюжку
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

    # Після всіх 'elif' (або якщо їх не було) перевіряємо наявність 'else'
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

    # Умова
    parseBooleanCondition()
    parseToken(';', 'punct')

    # Отримуємо ідентифікатор (l-value)
    id_line, id_lex, id_tok, _ = getSymb()
    if id_tok != 'id':
        failParse('token mismatch', (id_line, id_lex, id_tok, 'expected id in for'))

    # Семантична перевірка l-value
    cxt_found, name, attr = st.findName(id_lex, st.currentContext, id_line)
    id_type = attr[2]
    numRow += 1

    # Отримуємо оператор присвоєння
    assign_line, assign_lex, assign_tok, _ = getSymb()
    if assign_tok != 'assign_op':
        failParse('token mismatch', (assign_line, assign_lex, assign_tok, 'assign op (=, +=, etc.)'))
    numRow += 1

    # Розбираємо вираз (r-value)
    expr_type = parseExpression()

    # Семантична перевірка
    if assign_lex == '=':
        st.check_assign(id_type, expr_type, assign_line)
    else:  # Складне присвоєння
        op_map = {'+=': '+', '-=': '-', '*=': '*', '/=': '/'}
        arith_op = op_map.get(assign_lex)
        result_type = st.check_arithm_op(id_type, arith_op, expr_type, assign_line)
        st.check_assign(id_type, result_type, assign_line)

    # --- Тіло циклу ---
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

    # Змінна для перевірки
    line, lex, tok, _ = getSymb()
    if tok != 'id':
        failParse('token mismatch', (line, lex, tok, 'expected id'))
    st.findName(lex, st.currentContext, line)  # Перевірка, що змінна існує
    numRow += 1

    parseToken('{', 'brackets_op')

    while numRow <= len_tableOfSymb and getSymb()[1] in ('case', 'default'):
        if getSymb()[1] == 'case':
            parseCase()
        else:  # default
            parseDefault()

    parseToken('}', 'brackets_op')
    predIndt()


def parseCase():
    indent = nextIndt()
    print(indent + 'parseCase():')
    global numRow

    parseToken('case', 'keyword')

    # Очікуємо константу (число або рядок)
    line, lex, tok, _ = getSymb()
    if tok not in ('intnum', 'realnum', 'stringval'):
        failParse('token mismatch', (line, lex, tok, 'expected const'))
    numRow += 1

    parseToken(':', 'punct')

    # Інструкції
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
    parseExpression()  # print може виводити результат будь-якого виразу
    parseToken(')', 'brackets_op')
    parseToken(';', 'punct')

    predIndt()


def parseFunctionDeclaration():
    indent = nextIndt()
    print(indent + 'parseFunctionDeclaration():')
    global numRow

    parseToken('function', 'keyword')

    # Ім'я функції
    func_line, func_name, func_tok, _ = getSymb()
    if func_tok != 'id':
        failParse('очікувалось ім\'я функції', getSymb(True))
    numRow += 1

    # Створюємо нову область видимості
    parentContext = st.currentContext
    st.currentContext = func_name
    st.tabName[st.currentContext] = {'declIn': parentContext}
    print(f"DEBUG: Вхід в область видимості {st.currentContext}, батько {parentContext}")

    # Додаємо функцію в батьківську область
    func_attr = (len(st.tabName[parentContext]) - 1, 'function', 'void', 'assigned', 0)
    st.insertName(parentContext, func_name, func_line, func_attr)

    parseToken('(', 'brackets_op')
    # Тут був би розбір параметрів
    parseToken(')', 'brackets_op')
    parseToken('{', 'brackets_op')

    # Тіло функції
    while numRow <= len_tableOfSymb and getSymb()[1] != '}':
        parseStatement()

    parseToken('}', 'brackets_op')

    # Виходимо з області видимості
    st.currentContext = parentContext
    print(f"DEBUG: Exit scope, return to {st.currentContext}")
    predIndt()


def parseBooleanCondition():
    indent = nextIndt()
    print(indent + 'parseBooleanCondition():')

    line, _, _, _ = getSymb()
    expr_type = parseExpression()

    if expr_type != 'bool':
        st.failSem(f"Condition must be bool, not '{expr_type}'", line)

    predIndt()


def parseExpression():
    indent = nextIndt()
    print(indent + 'parseExpression():')
    global numRow

    # Починаємо з логічного виразу (найнижчий пріоритет)
    l_type = parseOr()

    # Перевірка на тернарний оператор
    if numRow <= len_tableOfSymb and getSymb()[1] == '?':
        line_tern, _, _, _ = getSymb()
        if l_type != 'bool':
            st.failSem("Tern op condition must be bool", line_tern)

        # Очікуємо унікальний токен для '?'
        parseToken('?', 'tern_op')
        true_type = parseExpression()
        # Очікуємо токен пунктуації для ':'
        parseToken(':', 'punct')
        false_type = parseExpression()

        # Типи результатів мають бути сумісними
        if not st.can_assign(true_type, false_type) and not st.can_assign(false_type, true_type):
            st.failSem(f"Tern op result types incompatible: '{true_type}' та '{false_type}'", line_tern)

        # Результат має "найширший" тип (float > int)
        l_type = 'float' if 'float' in (true_type, false_type) else true_type

    predIndt()
    return l_type


def parseOr():
    indent = nextIndt()
    print(indent + 'parseOr():')
    global numRow

    l_type = parseAnd()
    while numRow <= len_tableOfSymb and getSymb()[1] == '||':
        op_line, op_lex, op_tok, _ = getSymb()
        numRow += 1
        r_type = parseAnd()
        l_type = st.check_logic_op(l_type, op_lex, r_type, op_line)

    predIndt()
    return l_type


def parseAnd():
    indent = nextIndt()
    print(indent + 'parseAnd():')
    global numRow

    l_type = parseRel()
    while numRow <= len_tableOfSymb and getSymb()[1] == '&&':
        op_line, op_lex, op_tok, _ = getSymb()
        numRow += 1
        r_type = parseRel()
        l_type = st.check_logic_op(l_type, op_lex, r_type, op_line)

    predIndt()
    return l_type


def parseRel():
    indent = nextIndt()
    print(indent + 'parseRel():')
    global numRow

    l_type = parseArithmExpression()
    if numRow <= len_tableOfSymb and getSymb()[2] == 'rel_op':
        op_line, op_lex, op_tok, _ = getSymb()
        numRow += 1
        r_type = parseArithmExpression()
        st.check_rel_op(l_type, op_lex, r_type, op_line)
        l_type = 'bool'  # Результат порівняння - bool

    predIndt()
    return l_type


def parseArithmExpression():
    indent = nextIndt()
    print(indent + 'parseArithmExpression():')
    global numRow

    l_type = parseTerm()
    while numRow <= len_tableOfSymb and getSymb()[2] == 'add_op':
        op_line, op_lex, op_tok, _ = getSymb()
        numRow += 1
        r_type = parseTerm()
        l_type = st.check_arithm_op(l_type, op_lex, r_type, op_line)

    predIndt()
    return l_type


def parseTerm():
    indent = nextIndt()
    print(indent + 'parseTerm():')
    global numRow

    l_type = parsePower()
    while numRow <= len_tableOfSymb and getSymb()[2] == 'mult_op':
        op_line, op_lex, op_tok, _ = getSymb()
        numRow += 1
        r_type = parsePower()
        l_type = st.check_arithm_op(l_type, op_lex, r_type, op_line)

    predIndt()
    return l_type


def parsePower():
    indent = nextIndt()
    print(indent + 'parsePower():')
    global numRow

    l_type = parseFactor()
    if numRow <= len_tableOfSymb and getSymb()[2] == 'pow_op':
        op_line, op_lex, op_tok, _ = getSymb()
        numRow += 1
        r_type = parseFactor()
        l_type = st.check_arithm_op(l_type, op_lex, r_type, op_line)

    predIndt()
    return l_type


def parseFactor():
    indent = nextIndt()
    print(indent + 'parseFactor():')
    global numRow

    line, lex, tok, _ = getSymb()
    factor_type = 'type_error'

    # Обробка унарного мінуса/плюса
    if (lex, tok) in (('+', 'add_op'), ('-', 'add_op')):
        numRow += 1  # "З'їдаємо" знак
        factor_type = parseFactor()
        # Семантична перевірка: унарні оператори застосовуються тільки до чисел.
        if factor_type not in ('int', 'float'):
            st.failSem(
                f"Unary op '{lex}' can only be used for 'int' or 'float', not '{factor_type}'",
                line)

    elif tok in ('intnum', 'realnum', 'stringval', 'boolval'):
        numRow += 1
        if tok == 'intnum':
            factor_type = 'int'
        elif tok == 'realnum':
            factor_type = 'float'
        elif tok == 'stringval':
            factor_type = 'string'
        elif tok == 'boolval':
            factor_type = 'bool'
    elif tok == 'id':
        # Перевірка, чи це не виклик функції (у майбутньому)
        cxt_found, name, attr = st.findName(lex, st.currentContext, line)
        factor_type = attr[2]
        numRow += 1
    elif lex == '(':
        parseToken('(', 'brackets_op')
        factor_type = parseExpression()
        parseToken(')', 'brackets_op')
    elif lex == '!':  # Унарний 'не'
        numRow += 1
        factor_type = parseFactor()
        if factor_type != 'bool':
            st.failSem(f"Operator '!' only for bool, not '{factor_type}'", line)
        factor_type = 'bool'
    else:
        failParse('token mismatch',
                  (line, lex, tok, 'expected number, id, bracket expression, or unary op'))

    predIndt()
    return factor_type


def parseToken(lexeme, token):
    global numRow
    indent = nextIndt()

    if numRow > len_tableOfSymb:
        failParse('Unexpected program end', (lexeme, token, numRow))

    numLine, lex, tok, _ = getSymb()

    if (lex, tok) == (lexeme, token):
        print(indent + f'parseToken: in {numLine} token {(lexeme, token)}')
        numRow += 1
        predIndt()
        return True
    else:
        failParse('token mismatch', (numLine, lex, tok, lexeme, token))
        return False


def getSymb():
    if numRow > len_tableOfSymb:
        failParse('getSymb(): Unexpected program end', numRow)

    return lexer.tableOfLex[numRow]


def failParse(str_msg, details):
    if str_msg == 'Unexpected program end':
        lexeme, token, row = details
        print(
            f'Parser ERROR: \n\t Unexpected program end. Expected ({lexeme}, {token}), but table ended in {row - 1}.')
        exit(1001)
    elif str_msg == 'getSymb(): Unexpected program end':
        row = details
        print(
            f'Parser ERROR: \n\t Tried read in {row} from lex table, which has only {len_tableOfSymb}')
        exit(1002)
    elif str_msg == 'token mismatch':
        if len(details) == 5:
            numLine, lexeme, token, expected_lex, expected_tok = details
            print(
                f'Parser ERROR: \n\t Unexpected ({lexeme},{token}) in {numLine}. \n\t Expected - ({expected_lex},{expected_tok}).')
        else:
            numLine, lexeme, token, expected = details
            print(
                f'Parser ERROR: \n\t Unexpected ({lexeme},{token}) in {numLine}. \n\t Expected - {expected}.')
        exit(1)
    else:
        numLine, lex, tok, expected = details
        print(f'Parser ERROR: \n\t {str_msg} ({lex},{tok}) in {numLine}. \n\t Expected - {expected}.')
        exit(2)

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


# Очновний запуск
if FSuccess == ('Rocket', True):
    try:
        parseProgram()
        print("\nPARSER SUCCESS")
    except SystemExit as e:
        print(f"\nPARSER FAIL")
else:
    print("\nPARSER FAIL DUE TO LEXER FAIL")
