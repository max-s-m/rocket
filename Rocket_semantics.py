tabName = {
    'univ': {'declIn': '-'}
}
currentContext = 'univ'
functionContextStack = []

def failSem(message, line_num=''):
    line_info = f"in line {line_num}" if line_num else ""
    print(f"Semantic ERROR {line_info}: \n\t {message}")
    exit(10)

def insertName(cxt, name, line, attr):
    try:
        if name in tabName[cxt]:
            failSem(f"Repeated identifier declaration '{name}' in scope '{cxt}'", line)
        tabName[cxt][name] = attr
        print(f"Semantic: Inserted '{name}' into '{cxt}' with attributes {attr}")
    except KeyError:
        failSem(f"Unknown scope '{cxt}'", line)

def findName(name, cxt, line):
    try:
        current_cxt = cxt
        while current_cxt != '-':
            if name in tabName[current_cxt]:
                return (current_cxt, name, tabName[current_cxt][name])
            current_cxt = tabName[current_cxt]['declIn']
        failSem(f"Use of undeclared identifier '{name}'", line)
    except KeyError:
        failSem(f"Error searching for '{name}' in scope '{cxt}'", line)

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
        failSem(f"Cannot update undeclared variable '{name}'", line)
    except KeyError:
        failSem(f"Error updating name '{name}' in scope '{cxt}'", line)

def check_logic_op(l_type, op, r_type, line):
    if l_type == 'bool' and r_type == 'bool':
        return 'bool'
    else:
        failSem(f"Logical operator '{op}' cannot be applied to types '{l_type}' and '{r_type}'", line)
        return 'type_error'


def check_arithm_op(l_type, op, r_type, line):
    if l_type in ('bool', 'string') or r_type in ('bool', 'string'):
        if op == '+' and l_type == 'string' and r_type == 'string':
            return 'string', None
        else:
            failSem(f"Arithmetic operator '{op}' cannot be applied to '{l_type}' and '{r_type}'", line)
            return 'type_error', None

    if op == '^' or op == '/':
        conversion = None
        if l_type == 'int' and r_type == 'int':
            conversion = 'i2f_both'
        elif l_type == 'int':
            conversion = 'i2f_l'
        elif r_type == 'int':
            conversion = 'i2f_r'
        return 'float', conversion

    if l_type in ('int', 'float') and r_type in ('int', 'float'):
        if l_type == 'float' or r_type == 'float':
            conversion = None
            if l_type == 'int': conversion = 'i2f_l'
            elif r_type == 'int': conversion = 'i2f_r'
            return 'float', conversion
        return 'int', None

    failSem(f"Unknown type combination for operator '{op}': '{l_type}' and '{r_type}'", line)
    return 'type_error', None


def check_rel_op(l_type, op, r_type, line):
    if l_type in ('bool', 'string') or r_type in ('bool', 'string'):
        if l_type != r_type:
            failSem(f"Comparison operator '{op}' cannot be applied to '{l_type}' and '{r_type}'", line)
        return 'bool', None

    if l_type == 'int' and r_type == 'float':
        return 'bool', 'i2f_l'
    elif l_type == 'float' and r_type == 'int':
        return 'bool', 'i2f_r'

    return 'bool', None

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
        return
    failSem(f"Cannot assign expression of type '{expr_type}' to a variable of type '{var_type}'", line)