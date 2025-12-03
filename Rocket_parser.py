import Rocket_lexer as lexer
import Rocket_semantics as semant
import poliz

# Запуск лексичного аналізатора
if lexer.sourceCode:
    FSuccess = ('Rocket', lexer.FSuccess[1])
else:
    FSuccess = ('Rocket', False)

# Глобальні змінні для парсера
numRow = 1
len_tableOfSymb = len(lexer.tableOfLex)
break_label_stack = []  # Стек для міток виходу з циклів/switch


def parseProgram():
    global numRow
    print("\nParser Log (Syntax, Semantic & POLIZ):")
    while numRow <= len_tableOfSymb:
        if numRow > len_tableOfSymb: break
        _, lex, tok, _ = getSymb()

        if lex in ('int', 'float', 'bool', 'string', 'void'):
            if numRow + 2 < len_tableOfSymb and lexer.tableOfLex[numRow + 2][1] == '(':
                parseFunctionDeclaration()
            elif lex != 'void':
                parseDeclaration()
            else:
                failParse('type mismatch',
                          (getSymb()[0], lex, tok, "'void' can only be used as a function return type"))
        elif lex in ('if', 'switch', 'while', 'do', 'for', 'print', 'return', 'break') or tok == 'id':
            parseStatement()
        elif tok == 'comment' or lex in ('{', '}'):
            numRow += 1
        else:
            failParse('instruction mismatch',
                      (getSymb()[0], lex, tok, 'Expected global declaration, function, or statement'))


def parseDeclaration():
    indent = nextIndt()
    print(indent + 'parseDeclaration():')
    global numRow
    line, declared_type, _, _ = getSymb()
    parseToken(declared_type, 'keyword')
    id_line, id_lex, id_tok, _ = getSymb()
    if id_tok != 'id':
        failParse('token mismatch', (id_line, id_lex, id_tok, 'expected identifier'))
    numRow += 1
    val_status = 'undefined'
    if numRow <= len_tableOfSymb and getSymb()[1] == '=':
        parseToken('=', 'assign_op')
        poliz.postfix_code_gen(id_lex, 'l-val')
        expr_type = parseExpression()
        semant.check_assign(declared_type, expr_type, line)
        poliz.postfix_code_gen('=', 'assign_op')
        val_status = 'assigned'
    attr = (len(semant.tabName[semant.currentContext]), 'variable', declared_type, val_status, '-')
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
    elif lex == 'break':
        parseBreakStatement()
    else:
        failParse('instruction mismatch', (getSymb()[0], lex, tok, 'expected a statement'))
    predIndt()


def parseBreakStatement():
    indent = nextIndt()
    print(indent + 'parseBreakStatement():')
    line, _, _, _ = getSymb()
    parseToken('break', 'keyword')
    if not break_label_stack:
        semant.failSem("'break' statement not within a switch or loop", line)
    poliz.current_rpn_table.append(break_label_stack[-1])
    poliz.postfix_code_gen('JMP', 'jump')
    parseToken(';', 'punct')
    predIndt()


def parseReturnStatement():
    indent = nextIndt()
    print(indent + 'parseReturnStatement():')
    line, _, _, _ = getSymb()
    parseToken('return', 'keyword')
    if not semant.functionContextStack:
        semant.failSem("'return' cannot be used outside of a function body", line)
    current_func = semant.functionContextStack[-1]
    current_func['has_return'] = True
    expected_type = current_func['return_type']
    if getSymb()[1] == ';':
        if expected_type != 'void':
            semant.failSem(f"A non-void function must return a value of type '{expected_type}'", line)
    else:
        if expected_type == 'void':
            semant.failSem("A 'void' function cannot return a value", line)
        expr_type = parseExpression()
        semant.check_assign(expected_type, expr_type, line)
    poliz.postfix_code_gen('RET', 'RET')
    parseToken(';', 'punct')
    predIndt()


def parseAssign():
    indent = nextIndt()
    print(indent + 'parseAssign():')
    global numRow
    id_line, id_lex, _, _ = getSymb()
    _, _, attr = semant.findName(id_lex, semant.currentContext, id_line)
    id_type = attr[2]
    numRow += 1
    assign_line, assign_lex, assign_tok, _ = getSymb()
    if assign_tok != 'assign_op':
        failParse('token mismatch', (getSymb()[0:3], 'expected assignment operator'))
    numRow += 1
    if assign_lex != '=':
        poliz.postfix_code_gen(id_lex, 'l-val')
        poliz.postfix_code_gen(id_lex, 'r-val')
    else:
        poliz.postfix_code_gen(id_lex, 'l-val')
    if assign_lex == '/=':
        next_line, next_lex, next_tok, _ = getSymb()
        if next_tok in ('intnum', 'realnum') and float(next_lex) == 0:
            semant.failSem("Division by zero literal in '/=' operator", next_line)
    input_map = {'inputInt': 'int', 'inputFloat': 'float', 'inputBool': 'bool', 'inputString': 'string'}
    if getSymb()[1] in input_map:
        input_func = getSymb()[1]
        semant.check_assign(id_type, input_map[input_func], assign_line)
        parseToken(input_func, 'id')
        parseToken('(', 'brackets_op')
        parseToken(')', 'brackets_op')
        poliz.postfix_code_gen(input_func, 'inp_op')
    else:
        expr_type = parseExpression()
        if assign_lex == '=':
            semant.check_assign(id_type, expr_type, assign_line)
        else:
            op_map = {'+=': '+', '-=': '-', '*=': '*', '/=': '/'}
            arith_op = op_map.get(assign_lex)
            result_type = semant.check_arithm_op(id_type, arith_op, expr_type, assign_line)
            semant.check_assign(id_type, result_type, assign_line)
            poliz.postfix_code_gen(arith_op, 'math_op')
    poliz.postfix_code_gen('=', 'assign_op')
    semant.updateNameVal(id_lex, semant.currentContext, id_line, 'assigned')
    parseToken(';', 'punct')
    predIndt()


def parseIf():
    indent = nextIndt()
    print(indent + 'parseIf():')
    global numRow

    label_end_if = poliz.create_label()

    parseToken('if', 'keyword')
    parseToken('(', 'brackets_op')
    parseBooleanCondition()
    parseToken(')', 'brackets_op')

    label_next = poliz.create_label()
    poliz.current_rpn_table.append(label_next)
    poliz.postfix_code_gen('JF', 'jf')

    parseBlock()
    poliz.current_rpn_table.append(label_end_if)
    poliz.postfix_code_gen('JMP', 'jump')

    poliz.set_label_value(label_next)
    poliz.postfix_code_gen(':', 'colon')

    while numRow <= len_tableOfSymb and getSymb()[1] == 'elif':
        label_next = poliz.create_label()
        print(indent + '  found elif')
        parseToken('elif', 'keyword')
        parseToken('(', 'brackets_op')
        parseBooleanCondition()
        parseToken(')', 'brackets_op')
        poliz.current_rpn_table.append(label_next)
        poliz.postfix_code_gen('JF', 'jf')
        parseBlock()
        poliz.current_rpn_table.append(label_end_if)
        poliz.postfix_code_gen('JMP', 'jump')
        poliz.set_label_value(label_next)
        poliz.postfix_code_gen(':', 'colon')

    if numRow <= len_tableOfSymb and getSymb()[1] == 'else':
        print(indent + '  found else')
        parseElse()

    poliz.set_label_value(label_end_if)
    poliz.postfix_code_gen(':', 'colon')
    predIndt()


def parseElse():
    parseToken('else', 'keyword')
    parseBlock()


def parseWhile():
    indent = nextIndt()
    print(indent + 'parseWhile():')
    label_cond = poliz.create_label()
    label_end = poliz.create_label()
    break_label_stack.append(label_end)
    poliz.set_label_value(label_cond)
    poliz.postfix_code_gen(':', 'colon')
    parseToken('while', 'keyword')
    parseToken('(', 'brackets_op')
    parseBooleanCondition()
    parseToken(')', 'brackets_op')
    poliz.current_rpn_table.append(label_end)
    poliz.postfix_code_gen('JF', 'jf')
    parseBlock()
    poliz.current_rpn_table.append(label_cond)
    poliz.postfix_code_gen('JMP', 'jump')
    poliz.set_label_value(label_end)
    poliz.postfix_code_gen(':', 'colon')
    break_label_stack.pop()
    predIndt()


def parseDoWhile():
    indent = nextIndt()
    print(indent + 'parseDoWhile():')
    label_start = poliz.create_label()
    label_end = poliz.create_label()
    break_label_stack.append(label_end)
    poliz.set_label_value(label_start)
    poliz.postfix_code_gen(':', 'colon')
    parseToken('do', 'keyword')
    parseBlock()
    parseToken('while', 'keyword')
    parseToken('(', 'brackets_op')
    parseBooleanCondition()
    parseToken(')', 'brackets_op')
    poliz.current_rpn_table.append(label_start)
    poliz.postfix_code_gen('JNE', 'jne')
    poliz.set_label_value(label_end)  # Для break
    poliz.postfix_code_gen(':', 'colon')
    parseToken(';', 'punct')
    break_label_stack.pop()
    predIndt()


def parseFor():
    indent = nextIndt()
    print(indent + 'parseFor():')
    global numRow

    label_cond = poliz.create_label()
    label_end = poliz.create_label()

    break_label_stack.append(label_end)

    parseToken('for', 'keyword')
    parseToken('(', 'brackets_op')

    parseDeclaration()

    poliz.set_label_value(label_cond)
    poliz.postfix_code_gen(':', 'colon')
    parseBooleanCondition()
    parseToken(';', 'punct')

    poliz.current_rpn_table.append(label_end)
    poliz.postfix_code_gen('JF', 'jf')

    incr_start_row = numRow
    while getSymb()[1] != ')':
        numRow += 1

    parseToken(')', 'brackets_op')

    parseBlock()

    block_end_row = numRow

    numRow = incr_start_row

    id_line, id_lex, id_tok, _ = getSymb()
    if id_tok != 'id':
        failParse('token mismatch', (id_line, id_lex, id_tok, 'expected identifier in for increment'))

    _, _, attr = semant.findName(id_lex, semant.currentContext, id_line)
    id_type = attr[2]

    numRow += 1
    assign_line, assign_lex, assign_tok, _ = getSymb()
    if assign_tok != 'assign_op':
        failParse('token mismatch', (assign_line, assign_lex, assign_tok, 'expected assignment operator'))

    numRow += 1

    poliz.postfix_code_gen(id_lex, 'l-val')
    expr_type = parseExpression()  # Розбере вираз до ')'
    semant.check_assign(id_type, expr_type, assign_line)
    poliz.postfix_code_gen(assign_lex, 'assign_op')

    numRow = block_end_row

    poliz.current_rpn_table.append(label_cond)
    poliz.postfix_code_gen('JMP', 'jump')

    poliz.set_label_value(label_end)
    poliz.postfix_code_gen(':', 'colon')

    break_label_stack.pop()
    predIndt()


def parseSwitch():
    indent = nextIndt()
    print(indent + 'parseSwitch():')
    global numRow
    label_end_switch = poliz.create_label()
    break_label_stack.append(label_end_switch)
    parseToken('switch', 'keyword')
    line, switch_var_lex, _, _ = getSymb()
    semant.findName(switch_var_lex, semant.currentContext, line)
    numRow += 1
    parseToken('{', 'brackets_op')
    label_for_next_check = None
    has_default = False
    while numRow <= len_tableOfSymb and getSymb()[1] in ('case', 'default'):
        if getSymb()[1] == 'case':
            if label_for_next_check:
                poliz.set_label_value(label_for_next_check)
                poliz.postfix_code_gen(':', 'colon')
            label_for_next_check = poliz.create_label()
            parseToken('case', 'keyword')
            poliz.postfix_code_gen(switch_var_lex, 'r-val')
            case_line, case_lex, case_tok, _ = getSymb()
            poliz.postfix_code_gen(case_lex, case_tok)
            poliz.postfix_code_gen('==', 'rel_op')
            numRow += 1
            parseToken(':', 'punct')
            poliz.current_rpn_table.append(label_for_next_check)
            poliz.postfix_code_gen('JF', 'jf')
            while numRow <= len_tableOfSymb and getSymb()[1] not in ('case', 'default', '}'):
                parseStatement()
        elif getSymb()[1] == 'default':
            has_default = True
            if label_for_next_check:
                poliz.set_label_value(label_for_next_check)
                poliz.postfix_code_gen(':', 'colon')
            parseToken('default', 'keyword')
            parseToken(':', 'punct')
            while numRow <= len_tableOfSymb and getSymb()[1] != '}':
                parseStatement()
    if not has_default and label_for_next_check:
        poliz.set_label_value(label_for_next_check)
        poliz.postfix_code_gen(':', 'colon')
    poliz.set_label_value(label_end_switch)
    poliz.postfix_code_gen(':', 'colon')
    parseToken('}', 'brackets_op')
    break_label_stack.pop()
    predIndt()


# ... (решта файлу без змін)

def parseCase():
    pass  # Логіка тепер всередині parseSwitch


def parseDefault():
    pass  # Логіка тепер всередині parseSwitch


def parsePrint():
    indent = nextIndt()
    print(indent + 'parsePrint():')
    parseToken('print', 'keyword')
    parseToken('(', 'brackets_op')
    parseExpression()
    parseToken(')', 'brackets_op')
    poliz.postfix_code_gen('PRINT', 'out_op')
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
    semant.insertName(parent_context, func_name, func_line, (0, 'function', return_type, 'defined', []))
    semant.currentContext = func_name
    semant.tabName[semant.currentContext] = {'declIn': parent_context}
    semant.functionContextStack.append({'name': func_name, 'return_type': return_type, 'has_return': False})
    parseToken('(', 'brackets_op')
    param_types = []
    if getSymb()[1] != ')':
        param_types = parseParameterList()
    parseToken(')', 'brackets_op')
    func_attr = list(semant.tabName[parent_context][func_name])
    func_attr[4] = param_types
    semant.tabName[parent_context][func_name] = tuple(func_attr)
    parseBlock()
    current_func = semant.functionContextStack.pop()
    if current_func['return_type'] != 'void' and not current_func['has_return']:
        semant.failSem(f"Function '{func_name}' must return a value of type '{return_type}'", func_line)
    semant.currentContext = parent_context
    predIndt()


def parseBlock():
    indent = nextIndt()
    print(indent + 'parseBlock():')
    global numRow
    parseToken('{', 'brackets_op')
    while numRow <= len_tableOfSymb and getSymb()[1] != '}':
        _, lex, tok, _ = getSymb()
        if lex in ('int', 'float', 'bool', 'string', 'void'):
            if numRow + 2 < len_tableOfSymb and lexer.tableOfLex[numRow + 2][1] == '(':
                parseFunctionDeclaration()
            elif lex != 'void':
                parseDeclaration()
        elif lex in ('if', 'switch', 'while', 'do', 'for', 'print', 'return', 'break') or tok == 'id':
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
        label_false = poliz.create_label()
        label_end = poliz.create_label()
        poliz.current_rpn_table.append(label_false)
        poliz.postfix_code_gen('JF', 'jf')
        line_tern, _, _, _ = getSymb()
        parseToken('?', 'tern_op')
        true_type = parseExpression()
        poliz.current_rpn_table.append(label_end)
        poliz.postfix_code_gen('JMP', 'jump')
        poliz.set_label_value(label_false)
        poliz.postfix_code_gen(':', 'colon')
        parseToken(':', 'punct')
        false_type = parseExpression()
        poliz.set_label_value(label_end)
        poliz.postfix_code_gen(':', 'colon')
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
        line, lex, tok, _ = getSymb()
        numRow += 1
        r_type = parseAnd()
        l_type = semant.check_logic_op(l_type, lex, r_type, line)
        poliz.postfix_code_gen(lex, tok)
    predIndt()
    return l_type


def parseAnd():
    indent = nextIndt()
    print(indent + 'parseAnd():')
    global numRow
    l_type = parseRel()
    while numRow <= len_tableOfSymb and getSymb()[1] == '&&':
        line, lex, tok, _ = getSymb()
        numRow += 1
        r_type = parseRel()
        l_type = semant.check_logic_op(l_type, lex, r_type, line)
        poliz.postfix_code_gen(lex, tok)
    predIndt()
    return l_type


def parseRel():
    indent = nextIndt()
    print(indent + 'parseRel():')
    global numRow
    l_type = parseArithmExpression()
    if numRow <= len_tableOfSymb and getSymb()[2] == 'rel_op':
        line, lex, tok, _ = getSymb()
        numRow += 1
        r_type = parseArithmExpression()
        semant.check_rel_op(l_type, lex, r_type, line)
        poliz.postfix_code_gen(lex, tok)
        return 'bool'
    predIndt()
    return l_type


def parseArithmExpression():
    indent = nextIndt()
    print(indent + 'parseArithmExpression():')
    global numRow
    l_type = parseTerm()
    while numRow <= len_tableOfSymb and getSymb()[2] == 'add_op':
        line, lex, tok, _ = getSymb()
        numRow += 1
        r_type = parseTerm()
        l_type = semant.check_arithm_op(l_type, lex, r_type, line)
        poliz.postfix_code_gen(lex, tok)
    predIndt()
    return l_type


def parseTerm():
    indent = nextIndt()
    print(indent + 'parseTerm():')
    global numRow
    l_type = parsePower()
    while numRow <= len_tableOfSymb and getSymb()[2] == 'mult_op':
        op_line, op_lex, op_tok, _ = getSymb()
        if op_lex == '/':
            next_line, next_lex, next_tok, _ = lexer.tableOfLex[numRow + 1]
            if next_tok in ('intnum', 'realnum') and float(next_lex) == 0:
                semant.failSem("Division by zero literal", next_line)
        numRow += 1
        r_type = parsePower()
        l_type = semant.check_arithm_op(l_type, op_lex, r_type, op_line)
        poliz.postfix_code_gen(op_lex, op_tok)
    predIndt()
    return l_type


def parsePower():
    indent = nextIndt()
    print(indent + 'parsePower():')
    global numRow
    l_type = parseFactor()
    if numRow <= len_tableOfSymb and getSymb()[2] == 'pow_op':
        line, lex, tok, _ = getSymb()
        numRow += 1
        r_type = parseFactor()
        l_type = semant.check_arithm_op(l_type, lex, r_type, line)
        poliz.postfix_code_gen(lex, tok)
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
            semant.failSem(f"Unary operator '{lex}' can only be applied to 'int' or 'float'", line)
        if lex == '-':
            poliz.postfix_code_gen('NEG', 'math_op')
    elif tok in ('intnum', 'realnum', 'stringval', 'boolval'):
        poliz.postfix_code_gen(lex, tok)
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
            poliz.postfix_code_gen(lex, 'r-val')
            numRow += 1
    elif lex == '(':
        parseToken('(', 'brackets_op')
        factor_type = parseExpression()
        parseToken(')', 'brackets_op')
    elif lex == '!':
        numRow += 1
        factor_type = parseFactor()
        if factor_type != 'bool':
            semant.failSem(f"Operator '!' can only be applied to 'bool'", line)
        factor_type = 'bool'
        poliz.postfix_code_gen('!', 'bool_op')
    else:
        failParse('token mismatch', (line, lex, tok, 'expected number, identifier, expression, or unary operator'))
    predIndt()
    return factor_type


def parseFunctionCall():
    indent = nextIndt()
    print(indent + 'parseFunctionCall():')
    global numRow
    line, lex, _, _ = getSymb()
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
            semant.failSem(f"Incorrect type for argument {i + 1} in function '{lex}'", line)
    poliz.postfix_code_gen(lex, 'CALL')
    predIndt()
    return attr[2]


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
        poliz.generate_postfix_file('rocket_output', semant.tabName, poliz.main_rpn_table, poliz.main_label_table)
        print("\nFinal Symbol Table:")
        import json


        def default_serializer(o):
            return str(o)


        print(json.dumps(semant.tabName, indent=2, ensure_ascii=False, default=default_serializer))
    except SystemExit:
        print(f"\nANALYSIS FAILED")
else:
    print("\nPARSER NOT STARTED DUE TO LEXICAL ERRORS")
