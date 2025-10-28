
tabName = {
    'univ': {'declIn': '-'}  # Універсальна (глобальна) область видимості
}

# Поточна область видимості
currentContext = 'univ'


# Функція для виводу семантичних помилок
def failSem(message, line_num=''):
    line_info = f"in {line_num}" if line_num else ""
    print(f"Semantic ERROR {line_info}: \n\t {message}")
    exit(10)


# Додає ім'я в таблицю, перевіряє на повторне оголошення
def insertName(cxt, name, line, attr):
    try:
        if name in tabName[cxt]:
            failSem(f"Repeated id declaration '{name}' in scope '{cxt}'", line)
        tabName[cxt][name] = attr
        print(f"Semantic: Added {name} in {cxt} with {attr}")
        return True
    except KeyError:
        failSem(f"Unknown scope '{cxt}'", line)


# Шукає ім'я в поточній та батьківських областях, перевіряє на неоголошені ідентифікатори
def findName(name, cxt, line):
    try:
        current_cxt = cxt
        while current_cxt != '-':
            if name in tabName[current_cxt]:
                attr = tabName[current_cxt][name]
                return (current_cxt, name, attr)
            current_cxt = tabName[current_cxt]['declIn']

        failSem(f"Used undeclared var '{name}'", line)
    except KeyError:
        failSem(f"Error searching for '{name}' in scope '{cxt}'", line)


# Оновлює поле 'val_status' для змінної (на 'assigned')
def updateNameVal(name, cxt, line, newValue):
    try:
        current_cxt = cxt
        while current_cxt != '-':
            if name in tabName[current_cxt]:
                attr = tabName[current_cxt][name]
                # Оновлюємо значення, зберігаючи решту атрибутів
                tabName[current_cxt][name] = (attr[0], attr[1], attr[2], newValue, attr[4])
                return
            current_cxt = tabName[current_cxt]['declIn']

        failSem(f"Can't update undeclared var '{name}'", line)
    except KeyError:
        failSem(f"Error updating name '{name}' in scope '{cxt}'", line)


# --- Допоміжні функції перевірки типів ---

def check_logic_op(l_type, op, r_type, line):
    if l_type == 'bool' and r_type == 'bool':
        return 'bool'
    else:
        failSem(f"Logic operation '{op}' can't be used for '{l_type}' and '{r_type}'", line)
        return 'type_error'


def check_arithm_op(l_type, op, r_type, line):
    # Забороняємо арифметичні операції з bool та string (крім конкатенації)
    if l_type in ('bool', 'string') or r_type in ('bool', 'string'):
        if op == '+' and l_type == 'string' and r_type == 'string':
            return 'string'
        else:
            failSem(f"Aryth op '{op}' can't be used for '{l_type}' and '{r_type}'", line)
            return 'type_error'

    # Дозволяємо операції між int та float
    if l_type in ('int', 'float') and r_type in ('int', 'float'):
        if l_type == 'float' or r_type == 'float':
            return 'float'  # Розширення до float
        return 'int'

    failSem(f"Unknown type combination '{op}': '{l_type}' та '{r_type}'", line)
    return 'type_error'


def check_rel_op(l_type, op, r_type, line):
    # bool та string можна порівнювати тільки з однаковим типом
    if l_type in ('bool', 'string') or r_type in ('bool', 'string'):
        if l_type != r_type:
            failSem(f"Compare op '{op}' can't be used for '{l_type}' and '{r_type}'", line)
        return

    # int та float можна порівнювати між собою
    if l_type in ('int', 'float') and r_type in ('int', 'float'):
        return

    failSem(f"Compare op '{op}' can't be used for '{l_type}' and '{r_type}'", line)


# Допоміжна функція, що повертає True/False, а не викликає помилку
def can_assign(var_type, expr_type):
    if var_type == expr_type:
        return True
    # Дозволяємо неявне приведення int до float
    if var_type == 'float' and expr_type == 'int':
        return True
    return False


def check_assign(var_type, expr_type, line):
    if can_assign(var_type, expr_type):
        return True

    # Заборона неявного приведення float до int
    if var_type == 'int' and expr_type == 'float':
        failSem(f"Can't assign float to int var (no implicit types)", line)

    failSem(f"Can't assign expression type '{expr_type}' to var type '{var_type}'", line)