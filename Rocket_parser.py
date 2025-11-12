import Rocket_lexer as lexer
import Rocket_semantics as semant

# Запуск лексичного аналізатора
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
    print("\nParser Log (Syntax & Semantic Analysis):")
    while numRow <= len_tableOfSymb:
        if numRow > len_tableOfSymb:
            break
        _, lex, tok, _ = getSymb()

        if lex in ('int', 'float', 'bool', 'string', 'void', 'const'):
            # Перевіряємо, чи наступний токен після ID - це '(', щоб відрізнити функцію
            # Ця логіка може бути не ідеальною для 'const', але для 'const int ...' спрацює
            func_check_row = numRow
            if lex == 'const':
                func_check_row += 1  # Пропускаємо 'const', щоб дивитись на 'int'

            # (Примітка: ця логіка все одно не дасть створити 'const' функцію, що логічно)
            if func_check_row + 2 < len_tableOfSymb and lexer.tableOfLex[func_check_row + 2][1] == '(':
                # 'void' може бути тільки типом повернення функції, не змінної
                if lex == 'void':
                    parseFunctionDeclaration()
                # 'const' не може бути початком функції (в нашій граматиці)
                elif lex == 'const':
                    failParse('grammar mismatch',
                              (getSymb()[0], lex, tok, "Cannot declare a 'const' function"))
                else:  # int, float, etc. можуть бути і тим, і тим
                    parseFunctionDeclaration()
            elif lex != 'void':  # 'void' не може бути типом змінної
                parseDeclaration()
            else:
                failParse('type mismatch',
                          (getSymb()[0], lex, tok, "'void' can only be used as a function return type"))

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

    # --- Нова логіка для 'const' ---
    is_constant = False
    if getSymb()[1] == 'const':
        is_constant = True
        parseToken('const', 'keyword') # З'їдаємо токен 'const'
    # ---------------------------------

    line, declared_type, tok, _ = getSymb()
    # Перевірка, що 'void' не використовується для змінних/констант
    if declared_type == 'void':
        failParse('type mismatch',
                  (getSymb()[0], declared_type, tok, "'void' can only be used as a function return type"))
    parseToken(declared_type, 'keyword')

    id_line, id_lex, id_tok, _ = getSymb()
    if id_tok != 'id':
        failParse('token mismatch', (id_line, id_lex, id_tok, 'expected identifier'))
    numRow += 1

    val_status = 'undefined'
    if numRow <= len_tableOfSymb and getSymb()[1] == '=':
        parseToken('=', 'assign_op')
        expr_type = parseExpression()
        semant.check_assign(declared_type, expr_type, line)
        val_status = 'assigned'
    # --- Нова семантична перевірка ---
    elif is_constant:
        # Якщо це 'const', але ми не зайшли у 'if' вище — це помилка
        semant.failSem(f"Constant identifier '{id_lex}' must be initialized", id_line)
    # ---------------------------------

    # Визначаємо, що писати в tabName: 'variable' чи 'constant'
    id_kind = 'constant' if is_constant else 'variable'

    # Змінюємо 'variable' на id_kind
    attr = (len(semant.tabName[semant.currentContext]), id_kind, declared_type, val_status, '-')
    semant.insertName(semant.currentContext, id_lex, id_line, attr)
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
    line, _, _, _ = getSymb()
    parseToken('return', 'keyword')

    # Перевірка, чи 'return' не знаходиться поза функцією
    if not semant.functionContextStack:
        semant.failSem("'return' cannot be used outside of a function body", line)

    current_func = semant.functionContextStack[-1]
    current_func['has_return'] = True  # Позначаємо, що return в функції є
    expected_type = current_func['return_type']

    # Випадок 1: 'return;' (без виразу)
    if getSymb()[1] == ';':
        if expected_type != 'void':
            semant.failSem(f"A non-void function must return a value of type '{expected_type}'", line)
    # Випадок 2: 'return <expression>;'
    else:
        if expected_type == 'void':
            semant.failSem("A 'void' function cannot return a value", line)

        expr_type = parseExpression()
        # Перевіряємо, чи можна тип виразу присвоїти типу повернення функції
        semant.check_assign(expected_type, expr_type, line)

    parseToken(';', 'punct')
    predIndt()


def parseAssign():
    indent = nextIndt()
    print(indent + 'parseAssign():')
    global numRow

    id_line, id_lex, id_tok, _ = getSymb()
    _, _, attr = semant.findName(id_lex, semant.currentContext, id_line)

    # --- ГОЛОВНА ПЕРЕВІРКА ---
    # Атрибут attr[1] - це наш 'id_kind' ('variable' або 'constant')
    if attr[1] == 'constant':
        semant.failSem(f"Cannot assign to constant identifier '{id_lex}'", id_line)
    # -------------------------

    id_type = attr[2]
    numRow += 1

    assign_line, assign_lex, assign_tok, _ = getSymb()
    if assign_tok != 'assign_op':
        failParse('token mismatch', (getSymb()[0:3], 'expected assignment operator'))
    numRow += 1

    if assign_lex == '/=':
        next_line, next_lex, next_tok, _ = getSymb()
        if next_tok in ('intnum', 'realnum') and float(next_lex) == 0:
            semant.failSem("Division by zero literal in '/=' operator", next_line)

    input_map = {'inputInt': 'int', 'inputFloat': 'float', 'inputBool': 'bool', 'inputString': 'string'}
    if getSymb()[1] in input_map:
        input_func = getSymb()[1]
        expected_input_type = input_map[input_func]
        semant.check_assign(id_type, expected_input_type, assign_line)
        parseToken(input_func, 'id')
        parseToken('(', 'brackets_op')
        parseToken(')', 'brackets_op')
    else:
        expr_type = parseExpression()
        if assign_lex == '=':
            semant.check_assign(id_type, expr_type, assign_line)
        else:
            op_map = {'+=': '+', '-=': '-', '*=': '*', '/=': '/'}
            arith_op = op_map.get(assign_lex)
            result_type = semant.check_arithm_op(id_type, arith_op, expr_type, assign_line)
            semant.check_assign(id_type, result_type, assign_line)

    semant.updateNameVal(id_lex, semant.currentContext, id_line, 'assigned')
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
    parseBlock()

    while numRow <= len_tableOfSymb and getSymb()[1] == 'elif':
        print(indent + '  found elif')
        parseToken('elif', 'keyword')
        parseToken('(', 'brackets_op')
        parseBooleanCondition()
        parseToken(')', 'brackets_op')
        parseBlock()

    if numRow <= len_tableOfSymb and getSymb()[1] == 'else':
        print(indent + '  found else')
        parseElse()
    predIndt()


def parseElse():
    parseToken('else', 'keyword')
    parseBlock()


def parseWhile():
    indent = nextIndt()
    print(indent + 'parseWhile():')
    parseToken('while', 'keyword')
    parseToken('(', 'brackets_op')
    parseBooleanCondition()
    parseToken(')', 'brackets_op')
    parseBlock()
    predIndt()


def parseDoWhile():
    indent = nextIndt()
    print(indent + 'parseDoWhile():')
    parseToken('do', 'keyword')
    parseBlock()
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

    id_line, id_lex, id_tok, _ = getSymb()
    _, _, attr = semant.findName(id_lex, semant.currentContext, id_line)
    id_type = attr[2]
    numRow += 1

    assign_line, assign_lex, assign_tok, _ = getSymb()
    if assign_tok != 'assign_op':
        failParse('token mismatch', (getSymb()[0:3], 'expected assignment operator'))
    numRow += 1
    expr_type = parseExpression()

    if assign_lex == '=':
        semant.check_assign(id_type, expr_type, assign_line)
    else:
        op_map = {'+=': '+', '-=': '-', '*=': '*', '/=': '/'}
        arith_op = op_map.get(assign_lex)
        result_type = semant.check_arithm_op(id_type, arith_op, expr_type, assign_line)
        semant.check_assign(id_type, result_type, assign_line)

    parseToken(')', 'brackets_op')
    parseBlock()
    predIndt()


def parseSwitch():
    indent = nextIndt()
    print(indent + 'parseSwitch():')
    global numRow
    parseToken('switch', 'keyword')
    line, lex, tok, _ = getSymb()
    semant.findName(lex, semant.currentContext, line)
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
    _, _, tok, _ = getSymb()
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

    return_line, return_type, _, _ = getSymb()
    parseToken(return_type, 'keyword')

    func_line, func_name, func_tok, _ = getSymb()
    if func_tok != 'id':
        failParse('token mismatch', (getSymb()[0:3], 'expected function name'))
    numRow += 1

    parent_context = semant.currentContext
    # Попередньо додаємо функцію, поки без списку параметрів
    semant.insertName(parent_context, func_name, func_line, (0, 'function', return_type, 'defined', []))

    # Входимо в нову область видимості
    semant.currentContext = func_name
    semant.tabName[semant.currentContext] = {'declIn': parent_context}
    semant.functionContextStack.append({'name': func_name, 'return_type': return_type, 'has_return': False})

    parseToken('(', 'brackets_op')
    param_types = []
    if getSymb()[1] != ')':
        param_types = parseParameterList()
    parseToken(')', 'brackets_op')

    # Оновлюємо запис про функцію, додаючи типи параметрів
    func_attr = list(semant.tabName[parent_context][func_name])
    func_attr[4] = param_types
    semant.tabName[parent_context][func_name] = tuple(func_attr)
    print(f"Semantic: Updated function '{func_name}' with parameter types: {param_types}")

    parseBlock()

    current_func = semant.functionContextStack.pop()
    # Якщо функція не void і в ній не було жодного return
    if current_func['return_type'] != 'void' and not current_func['has_return']:
        semant.failSem(f"Function '{func_name}' must return a value of type '{return_type}'", func_line)

    # Повертаємось до попередньої області видимості
    semant.currentContext = parent_context
    predIndt()


def parseBlock():
    indent = nextIndt()
    print(indent + 'parseBlock():')
    global numRow
    parseToken('{', 'brackets_op')
    while numRow <= len_tableOfSymb and getSymb()[1] != '}':
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
        else:
            failParse('instruction mismatch',
                      (getSymb()[0], lex, tok, 'Expected declaration or statement inside block'))
    parseToken('}', 'brackets_op')
    predIndt()


def parseParameterList():
    indent = nextIndt()
    print(indent + 'parseParameterList():')
    global numRow
    param_types = []

    p_line, p_type, _, _ = getSymb()
    parseToken(p_type, 'keyword')
    param_types.append(p_type)

    id_line, id_lex, _, _ = getSymb()
    if getSymb()[2] != 'id':
        failParse('token mismatch', (getSymb()[0:3], 'expected parameter name'))

    attr = (len(semant.tabName[semant.currentContext]), 'variable', p_type, 'assigned', '-')
    semant.insertName(semant.currentContext, id_lex, id_line, attr)
    numRow += 1

    while numRow <= len_tableOfSymb and getSymb()[1] == ',':
        numRow += 1
        p_line, p_type, _, _ = getSymb()
        parseToken(p_type, 'keyword')
        param_types.append(p_type)
        id_line, id_lex, _, _ = getSymb()
        if getSymb()[2] != 'id':
            failParse('token mismatch', (getSymb()[0:3], 'expected parameter name'))

        attr = (len(semant.tabName[semant.currentContext]), 'variable', p_type, 'assigned', '-')
        semant.insertName(semant.currentContext, id_lex, id_line, attr)
        numRow += 1

    predIndt()
    return param_types


def parseBooleanCondition():
    indent = nextIndt()
    print(indent + 'parseBooleanCondition():')
    line, _, _, _ = getSymb()
    expr_type = parseExpression()
    if expr_type != 'bool':
        semant.failSem(f"Condition must be of type 'bool', not '{expr_type}'", line)
    predIndt()


def parseExpression():
    indent = nextIndt()
    print(indent + 'parseExpression():')
    l_type = parseOr()
    if numRow <= len_tableOfSymb and getSymb()[1] == '?':
        line_tern, _, _, _ = getSymb()
        if l_type != 'bool':
            semant.failSem("Ternary operator condition must be of type 'bool'", line_tern)
        parseToken('?', 'tern_op')
        true_type = parseExpression()
        parseToken(':', 'punct')
        false_type = parseExpression()
        if not semant.can_assign(true_type, false_type) and not semant.can_assign(false_type, true_type):
            semant.failSem(f"Ternary operator result types are incompatible: '{true_type}' and '{false_type}'",
                           line_tern)
        l_type = 'float' if 'float' in (true_type, false_type) else true_type
    predIndt()
    return l_type


def parseOr():
    indent = nextIndt()
    print(indent + 'parseOr():')
    global numRow
    l_type = parseAnd()
    while numRow <= len_tableOfSymb and getSymb()[1] == '||':
        line, lex, _, _ = getSymb()
        numRow += 1
        r_type = parseAnd()
        l_type = semant.check_logic_op(l_type, lex, r_type, line)
    predIndt()
    return l_type


def parseAnd():
    indent = nextIndt()
    print(indent + 'parseAnd():')
    global numRow
    l_type = parseRel()
    while numRow <= len_tableOfSymb and getSymb()[1] == '&&':
        line, lex, _, _ = getSymb()
        numRow += 1
        r_type = parseRel()
        l_type = semant.check_logic_op(l_type, lex, r_type, line)
    predIndt()
    return l_type


def parseRel():
    indent = nextIndt()
    print(indent + 'parseRel():')
    global numRow
    l_type = parseArithmExpression()
    if numRow <= len_tableOfSymb and getSymb()[2] == 'rel_op':
        line, lex, _, _ = getSymb()
        numRow += 1
        r_type = parseArithmExpression()
        semant.check_rel_op(l_type, lex, r_type, line)
        return 'bool'
    predIndt()
    return l_type


def parseArithmExpression():
    indent = nextIndt()
    print(indent + 'parseArithmExpression():')
    global numRow
    l_type = parseTerm()
    while numRow <= len_tableOfSymb and getSymb()[2] == 'add_op':
        line, lex, _, _ = getSymb()
        numRow += 1
        r_type = parseTerm()
        l_type = semant.check_arithm_op(l_type, lex, r_type, line)
    predIndt()
    return l_type


def parseTerm():
    indent = nextIndt()
    print(indent + 'parseTerm():')
    global numRow
    l_type = parsePower()
    while numRow <= len_tableOfSymb and getSymb()[2] == 'mult_op':
        op_line, op_lex, _, _ = getSymb()

        if op_lex == '/':
            next_line, next_lex, next_tok, _ = lexer.tableOfLex[numRow + 1]
            if next_tok in ('intnum', 'realnum') and float(next_lex) == 0:
                semant.failSem("Division by zero literal", next_line)

        numRow += 1
        r_type = parsePower()
        l_type = semant.check_arithm_op(l_type, op_lex, r_type, op_line)
    predIndt()
    return l_type


def parsePower():
    indent = nextIndt()
    print(indent + 'parsePower():')
    global numRow
    l_type = parseFactor()  # Розбираємо ліву частину (напр. '2')

    if numRow <= len_tableOfSymb and getSymb()[2] == 'pow_op':
        line, lex, _, _ = getSymb()  # Бачимо '^'
        numRow += 1

        # Рекурсивно викликаємо parsePower() для розбору ВСЬОГО, що йде праворуч
        # напр. '3 ^ 4'
        r_type = parsePower()  # <--- ОСЬ ГОЛОВНА ЗМІНА

        # Об'єднуємо '2' з результатом '(3 ^ 4)'
        l_type = semant.check_arithm_op(l_type, lex, r_type, line)

    predIndt()
    return l_type


def parseFactor():
    indent = nextIndt()
    print(indent + 'parseFactor():')
    global numRow
    line, lex, tok, _ = getSymb()
    factor_type = 'type_error'
    if (lex, tok) in (('+', 'add_op'), ('-', 'add_op')):
        numRow += 1
        factor_type = parseFactor()
        if factor_type not in ('int', 'float'):
            semant.failSem(f"Unary operator '{lex}' can only be applied to 'int' or 'float', not '{factor_type}'",
                           line)
    elif tok in ('intnum', 'realnum', 'stringval', 'boolval'):
        numRow += 1
        if tok == 'intnum':
            factor_type = 'int'
        elif tok == 'realnum':
            factor_type = 'float'
        elif tok == 'stringval':
            factor_type = 'string'
        else:
            factor_type = 'bool'
    elif tok == 'id':
        if numRow + 1 < len_tableOfSymb and lexer.tableOfLex[numRow + 1][1] == '(':
            factor_type = parseFunctionCall()
        else:
            _, _, attr = semant.findName(lex, semant.currentContext, line)
            factor_type = attr[2]
            numRow += 1
    elif lex == '(':
        parseToken('(', 'brackets_op')
        factor_type = parseExpression()
        parseToken(')', 'brackets_op')
    elif lex == '!':
        numRow += 1
        factor_type = parseFactor()
        if factor_type != 'bool':
            semant.failSem(f"Operator '!' can only be applied to 'bool', not '{factor_type}'", line)
        factor_type = 'bool'
    else:
        failParse('token mismatch', (line, lex, tok, 'expected number, identifier, expression, or unary operator'))
    predIndt()
    return factor_type


def parseFunctionCall():
    indent = nextIndt()
    print(indent + 'parseFunctionCall():')
    global numRow
    line, lex, tok, _ = getSymb()
    _, _, attr = semant.findName(lex, semant.currentContext, line)
    if attr[1] != 'function':
        semant.failSem(f"'{lex}' is not a function", line)

    expected_param_types = attr[4]
    numRow += 1

    parseToken('(', 'brackets_op')
    actual_arg_types = []
    if getSymb()[1] != ')':
        actual_arg_types = parseArgumentList()
    parseToken(')', 'brackets_op')

    if len(expected_param_types) != len(actual_arg_types):
        semant.failSem(
            f"Function '{lex}' expects {len(expected_param_types)} arguments, but {len(actual_arg_types)} were given",
            line)

    for i, (expected, actual) in enumerate(zip(expected_param_types, actual_arg_types)):
        if not semant.can_assign(expected, actual):
            semant.failSem(
                f"Incorrect type for argument {i + 1} in function '{lex}': expected '{expected}', but got '{actual}'",
                line)

    predIndt()
    return attr[2]  # Повертаємо тип, який повертає функція


def parseArgumentList():
    indent = nextIndt()
    print(indent + 'parseArgumentList():')
    global numRow
    arg_types = []
    arg_types.append(parseExpression())
    while numRow <= len_tableOfSymb and getSymb()[1] == ',':
        numRow += 1
        arg_types.append(parseExpression())
    predIndt()
    return arg_types


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
        print("\nSYNTAX AND SEMANTIC ANALYSIS SUCCESSFUL")
        print("\nFinal Symbol Table:")
        import json


        def default_serializer(o):
            return str(o)


        print(json.dumps(semant.tabName, indent=2, ensure_ascii=False, default=default_serializer))
    except SystemExit as e:
        print(f"\nANALYSIS FAILED")
else:
    print("\nPARSER NOT STARTED DUE TO LEXICAL ERRORS")
