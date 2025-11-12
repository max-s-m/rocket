tabName = {
    'global': {'declIn': '-'}  # глобальна область видимості
}
# Поточна область видимості
currentContext = 'global'

# Стек для перевірки return
functionContextStack = []


# Функція для виводу семантичних помилок
def failSem(message, line_num=''):
    line_info = f"in line {line_num}" if line_num else ""
    print(f"Semantic ERROR {line_info}: \n\t {message}")
    exit(10)


# Додає ім'я в таблицю, перевіряє на повторне оголошення
def insertName(cxt, name, line, attr):
    try:
        if name in tabName[cxt]:
            failSem(f"Repeated identifier declaration '{name}' in scope '{cxt}'", line)
        tabName[cxt][name] = attr
        print(f"Semantic: Inserted '{name}' into '{cxt}' with attributes {attr}")
        return True
    except KeyError:
        failSem(f"Unknown scope '{cxt}'", line)


# Шукає ім'я в поточній та батьківських областях
def findName(name, cxt, line):
    try:
        current_cxt = cxt
        while current_cxt != '-':
            if name in tabName[current_cxt]:
                attr = tabName[current_cxt][name]
                return (current_cxt, name, attr)
            current_cxt = tabName[current_cxt]['declIn']

        failSem(f"Use of undeclared identifier '{name}'", line)
    except KeyError:
        failSem(f"Error searching for '{name}' in scope '{cxt}'", line)


# Оновлює поле 'val_status' для змінної (на 'assigned')
def updateNameVal(name, cxt, line, newValue):
    try:
        current_cxt = cxt
        while current_cxt != '-':
            if name in tabName[current_cxt]:
                attr_list = list(tabName[current_cxt][name])
                attr_list[3] = newValue
                tabName[current_cxt][name] = tuple(attr_list)
                return
            current_cxt = tabName[current_cxt]['declIn']

        failSem(f"Can't update undeclared variable '{name}'", line)
    except KeyError:
        failSem(f"Error updating name '{name}' in scope '{cxt}'", line)


# ---Функції перевірки типів---
def check_logic_op(l_type, op, r_type, line):
    if l_type == 'bool' and r_type == 'bool':
        return 'bool'
    else:
        failSem(f"Logical op '{op}' can't be applied to types '{l_type}' and '{r_type}'", line)
        return 'type_error'


def check_arithm_op(l_type, op, r_type, line):
    if l_type in ('bool', 'string') or r_type in ('bool', 'string'):
        if op == '+' and l_type == 'string' and r_type == 'string':
            return 'string'
        else:
            failSem(f"Arith op '{op}' can't be applied to '{l_type}' and '{r_type}'", line)
            return 'type_error'

    if l_type in ('int', 'float') and r_type in ('int', 'float'):
        if l_type == 'float' or r_type == 'float':
            return 'float'
        return 'int'

    failSem(f"Unknown type combo for op '{op}': '{l_type}' and '{r_type}'", line)
    return 'type_error'


def check_rel_op(l_type, op, r_type, line):
    if l_type in ('bool', 'string') or r_type in ('bool', 'string'):
        if l_type != r_type:
            failSem(f"Compare op '{op}' can't be applied to '{l_type}' and '{r_type}'", line)
        return

    if l_type in ('int', 'float') and r_type in ('int', 'float'):
        return

    failSem(f"Comparison op '{op}' can't be applied to '{l_type}' and '{r_type}'", line)


def can_assign(var_type, expr_type):
    if var_type == expr_type:
        return True
    if var_type == 'float' and expr_type == 'int':
        return True
    return False


def check_assign(var_type, expr_type, line):
    if can_assign(var_type, expr_type):
        return

    if var_type == 'int' and expr_type == 'float':
        failSem(f"Can't assign 'float' to 'int' (no implicit allowed)",
                line)

    failSem(f"Can't assign type '{expr_type}' to type '{var_type}'", line)
