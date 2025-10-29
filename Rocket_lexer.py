# таблиця лексем, що визначаються за своїм повним ім'ям
tokenTable = {
    # булеві константи
    'true': 'boolval',
    'false': 'boolval',

    # ключові слова (Rocket)
    'int': 'keyword', 'float': 'keyword', 'bool': 'keyword', 'string': 'keyword',
    'print': 'keyword',
    'if': 'keyword', 'elif': 'keyword', 'else': 'keyword', # 'elif'
    'switch': 'keyword', 'case': 'keyword', 'default': 'keyword',
    'while': 'keyword', 'do': 'keyword', 'for': 'keyword', # 'do'
    'return': 'keyword',

    # логічні оператори
    '&&': 'logic_op', '||': 'logic_op', '!': 'logic_op',

    # арифметичні оператори
    '+': 'add_op', '-': 'add_op', '*': 'mult_op', '/': 'mult_op',

    # оператори відношення
    '=': 'assign_op', '+=': 'assign_op', '-=': 'assign_op', '*=': 'assign_op', '/=': 'assign_op',
    '==': 'rel_op', '!=': 'rel_op', '<': 'rel_op', '>': 'rel_op', '<=': 'rel_op', '>=': 'rel_op',

    # степеневий оператор
    '^': 'pow_op',

    # тернарний
    '?': 'tern_op',

    # дужки
    '(': 'brackets_op', ')': 'brackets_op',
    '{': 'brackets_op', '}': 'brackets_op',

    # пунктуація
    ',': 'punct', ';': 'punct', ':': 'punct',

    # коментар (використовується для виводу)
    '//': 'comment',

    # пропуски і перенесення
    ' ': 'ws', '\t': 'ws',
    '\n': 'eol', '\r': 'eol'
}

# решта токенів за кінцевим станом
tokStateTable = {
    4: 'id',
    7: 'realnum',
    8: 'intnum',
    10: 'stringval'
}

# ---------------- Ф-ція переходів ----------------
stf = {
    # q0: початковий стан
    (0, 'WhiteSpace'): 0,
    (0, 'NewLine'): 2,
    (0, 'Letter'): 3,
    (0, 'Digit'): 5,
    (0, 'Quote'): 9,
    (0, 'FSlash'): 12,
    (0, 'other'): 1,

    # q3 - q4: ідентифікатор
    (3, 'Letter'): 3,
    (3, 'Digit'): 3,
    (3, '_'): 3,  # дозволено '_'
    (3, 'other'): 4,

    # q5 - q8: числа
    (5, 'Digit'): 5,
    (5, 'dot'): 6,
    (5, 'other'): 8,
    (6, 'Digit'): 6,
    (6, 'other'): 7,

    # q9 - q11: рядкові літерали
    (9, 'other'): 9,
    (9, 'Quote'): 10,
    (9, 'NewLine'): 11,

    # q12 - q13/q17: коментар ('//') або ділення ('/')
    (0, '/'): 12,
    (12, 'FSlash'): 13,  # одноряд коментар
    (12, 'Equal'): 16,
    (12, 'other'): 17,  # ділення

    # q13: у коментарі, ігнор до NewLine
    (13, 'NewLine'): 2,
    (13, 'other'): 13,

    # q14: односимвольні роздільники
    (0, 'SpecialSigns'): 14,  # (), {}, [], :, ;, ?, ^

    # q15 - q17: одно та двосимвольні оператори
    (0, 'Am'): 15,  # +, -
    (0, 'Star'): 15,  # *
    (0, 'Exclam'): 15,  # !
    (0, 'More'): 15,  # >
    (0, 'Less'): 15,  # <
    (0, 'Equal'): 15,  # =
    (15, 'Equal'): 16,  # другий символ "=" (==, !=, >=, <=)
    (15, 'other'): 17,

    # q18 - q21: або
    (0, 'OrP'): 18,
    (18, 'OrP'): 21,
    (18, 'other'): 20,

    # q19 - q22: і
    (0, 'AndP'): 19,
    (19, 'AndP'): 22,
    (19, 'other'): 20,
}

# --- Конфігурація станів ---
initState = 0
# успішні кінцеві стани
F = {2, 4, 7, 8, 10, 14, 16, 17, 21, 22}
# стани повернення символу в потік
Fstar = {4, 7, 8, 17}
# стани помилок
Ferror = {1, 11, 20}

# --- Таблиці ---
tableOfId = {}
tableOfConst = {}
tableOfLex = {}
state = initState

# ---------------- Ввід програми ----------------
try:
    with open('Rocket_test.rocket', 'r', encoding="utf-8") as f:
        sourceCode = f.read()
except FileNotFoundError:
    print("Error: Rocket_test.rocket not found. Please create the file.")
    sourceCode = ""

# --- Глобальні змінні ---
FSuccess = ('Rocket', False)
lenCode = len(sourceCode)
numLine = 1
numChar = -1
char = ''
lexeme = ''

# ---------------- Основний цикл ----------------
def lex():
    global state, numLine, char, lexeme, numChar, FSuccess
    try:
        while numChar < lenCode - 1:
            char = nextChar()
            classCh = classOfChar(char)
            state = nextState(state, classCh)
            # блок перевірки на помилку
            if state in Ferror:
                # лексема з одного символу
                if state in (1, 11):
                    lexeme = char
                # помилки типу & чи |
                elif state == 20:
                    lexeme += char
                fail() # обробник помилок і завершення роботу
                return

            # якщо ми в коментарі, продовжуємо до кінця рядка
            if state == 13:
                lexeme = ''
                continue

            if is_final(state):
                processing()
            elif state == initState:
                lexeme = ''
            else:
                lexeme += char

        print('\nRocket: Lexical analysis done')
        FSuccess = ('Rocket', True)
    except SystemExit as e:
        # виклик exit() з fail()
        print(f'\nRocket: A lexical error occurred.')


# ---------------- Обробка фінальних станів ----------------
def processing():
    global state, lexeme, char, numLine, numChar, tableOfLex, initState

    # помилка невідомого символу
    if state == 1:
        lexeme = char  # лексема з одного невідомого символу

    # стани з поверненням символу
    if state in Fstar:
        token = getToken(state, lexeme)

        # ідентифікатори можуть бути ключовими словами або bool
        if token == 'id' or lexeme in tokenTable:
            if lexeme in tokenTable:  # перевірка на ключове слово/bool
                token = tokenTable[lexeme]
                if token == 'boolval':
                    index = indexIdConst_for_bool_or_str('boolval', lexeme)
                    tableOfLex[len(tableOfLex) + 1] = (numLine, lexeme, token, index)
                else:  # keyword
                    # Ключові слова не отримують індекс
                    tableOfLex[len(tableOfLex) + 1] = (numLine, lexeme, token, '')
            else:  # звичайний ідентифікатор
                index = indexIdConst(state, lexeme)
                tableOfLex[len(tableOfLex) + 1] = (numLine, lexeme, token, index)
        else:  # числа (intnum, realnum)
            index = indexIdConst(state, lexeme)
            tableOfLex[len(tableOfLex) + 1] = (numLine, lexeme, token, index)

        lexeme = ''
        numChar = putCharBack(numChar)
        state = initState
        return

    # двосимвольні: ==, !=, <=, >=, &&, ||
    if state in (16, 21, 22):
        lexeme += char
        token = getToken(state, lexeme)
        tableOfLex[len(tableOfLex) + 1] = (numLine, lexeme, token, '')
        lexeme = ''
        state = initState
        return

    # рядкові константи
    if state == 10:
        lexeme += char  # додається закриваюча лапка
        token = getToken(state, lexeme)
        inner_value = lexeme[1:-1]  # зберігання без лапок
        index = indexIdConst_for_bool_or_str('stringval', inner_value)
        tableOfLex[len(tableOfLex) + 1] = (numLine, lexeme, token, index)
        lexeme = ''
        state = initState
        return

    # односимвольні: (), {}, :, ;, ?, ^
    if state == 14:
        lexeme += char
        token = getToken(state, lexeme)
        tableOfLex[len(tableOfLex) + 1] = (numLine, lexeme, token, '')
        lexeme = ''
        state = initState
        return

    # новий рядок
    if state == 2:
        numLine += 1
        state = initState
        lexeme = ''
        return

    # обробка помилок
    if state in Ferror:
        fail()


# ---------------- Помилки ----------------
def fail():
    global state, numLine, char, lexeme
    if state == 1:
        print(f'ERROR(line {numLine}): Unexpected char "{char}"')
        exit(1)
    if state == 11:
        print(f'ERROR(line {numLine}): String ripped')
        exit(11)
    if state == 20:
        print(f'ERROR(line {numLine}): Unexpected char "{char}" after "{lexeme}". Expected {lexeme}')
        exit(20)


# ---------------- Службові функції ----------------
def is_final(state):
    return state in F


def nextState(state, classCh):
    try:
        return stf[(state, classCh)]
    except KeyError:
        # якщо нема переходу за цим класом, спроба перейти за 'other'
        return stf.get((state, 'other'), initState)


def nextChar():
    global numChar
    numChar += 1
    return sourceCode[numChar]


def putCharBack(numChar):
    return numChar - 1


def classOfChar(char):
    if char == '.':
        return "dot"
    if char in  'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_':
        return "Letter"
    if char.isdigit():
        return "Digit"
    if char in " \t":
        return "WhiteSpace"
    if char in "\n\r":
        return "NewLine"
    if char == '=':
        return "Equal"
    if char == '>':
        return "More"
    if char == '<':
        return "Less"
    if char == '&':
        return "AndP"
    if char == '|':
        return "OrP"
    if char == '"':
        return "Quote"
    if char == '!':
        return "Exclam"
    if char == '*':
        return "Star"
    if char == '/':
        return "FSlash"
    if char in '(){}[],:;?^':
        return "SpecialSigns"
    if char in '+-':
        return 'Am'
    return "other"


def getToken(state, lexeme):
    try:
        # пріоритет у лексем, що повністю збігаються (ключові слова, оператори)
        return tokenTable[lexeme]
    except KeyError:
        # якщо немає повного збігу, визначаємо токен за кінцевим станом
        return tokStateTable.get(state, 'unknown_token')


# pаносить id або числові константи у відповідні таблиці
def indexIdConst(state, lexeme):
    if state == 4:  # ідентифікатор
        if lexeme not in tableOfId:
            tableOfId[lexeme] = len(tableOfId) + 1
        return tableOfId[lexeme]

    if state in (7, 8):  # числа (realnum, intnum)
        if lexeme not in tableOfConst:
            token_type = tokStateTable[state]
            tableOfConst[lexeme] = (token_type, len(tableOfConst) + 1)
        return tableOfConst[lexeme][1]

    return ''  # для операторів індекс не потрібен


def indexIdConst_for_bool_or_str(ctype, value_lexeme):
    # Заносить true/false та рядки у tableOfConst
    if value_lexeme not in tableOfConst:
        tableOfConst[value_lexeme] = (ctype, len(tableOfConst) + 1)
    return tableOfConst[value_lexeme][1]


# ---------------- Запуск ----------------
if sourceCode:
    lex()

# ---------------- Друк таблиць ----------------
if FSuccess[1]:

    def format_table_of_symb_tabular(symb_table):
        header = f"| {'Line':<5} | {'Lexeme':<20} | {'Token':<15} | {'Index':<5} |"
        separator = "-" * len(header)
        output = f"{header}\n{separator}\n"
        for _, v in symb_table.items():
            line, lexeme, token, index = v
            index_str = str(index) if index != '' else ''
            row = f"| {str(line):<5} | {lexeme:<20} | {token:<15} | {index_str:<5} |"
            output += f"{row}\n"
        return output


    def format_id_const_tabular(data_table, name):
        output = f"\n{name}:\n"
        if not data_table:
            return output + "Empty\n"
        if name == 'tableOfId':
            header = f"| {'Identifier':<20} | {'Index':<5} |"
            separator = "-" * len(header)
            output += f"{header}\n{separator}\n"
            for k, v in data_table.items():
                row = f"| {k:<20} | {v:<5} |"
                output += f"{row}\n"
        else:  # tableOfConst
            header = f"| {'Constant':<20} | {'Type':<15} | {'Index':<5} |"
            separator = "-" * len(header)
            output += f"{header}\n{separator}\n"
            for k, v in data_table.items():
                c_type, c_index = v
                row = f"| {k:<20} | {c_type:<15} | {c_index:<5} |"
                output += f"{row}\n"
        return output


    print("\ntableOfLex:")
    print(format_table_of_symb_tabular(tableOfLex))
    print(format_id_const_tabular(tableOfId, 'tableOfId'))
    print(format_id_const_tabular(tableOfConst, 'tableOfConst'))
    if FSuccess[1]:
        print("LEXING SUCCESS")
    else:
        print("LEXING FAIL")
