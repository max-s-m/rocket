# Основні таблиці для головної програми (main)
main_rpn_table = []
main_label_table = {}

# Посилання на поточні таблиці
current_rpn_table = main_rpn_table
current_label_table = main_label_table

# Словник для мапування токенів парсера на токени ПОЛІЗ
TOKEN_MAP = {
    'intnum': 'int',
    'realnum': 'float',
    'boolval': 'bool',
    'stringval': 'string',
    'assign_op': 'assign_op',
    'add_op': 'math_op',
    'mult_op': 'math_op',
    'pow_op': 'pow_op',
    'rel_op': 'rel_op',
    'logic_op': 'bool_op',
    'tern_op': 'tern_op',
    'punct': 'punct'
}


def postfix_code_gen(lex, tok):
    rpn_tok = TOKEN_MAP.get(tok, tok)
    current_rpn_table.append((lex, rpn_tok))


def create_label():
    label_index = len(current_label_table) + 1
    label_name = f"m{label_index}"
    current_label_table[label_name] = 'undef'
    return (label_name, 'label')


def set_label_value(label_tuple):
    label_name, _ = label_tuple
    current_label_table[label_name] = len(current_rpn_table)


def generate_postfix_file(filename, local_scope, rpn_table, label_table, functions_in_scope=None):
    output_path = f"{filename}.postfix"

    used_globals = set()
    local_vars = set()

    # Збираємо імена локальних змінних ТА констант
    if local_scope:
        for name, attr in local_scope.items():
            if name != 'declIn' and attr[1] in ('variable', 'constant'):
                local_vars.add(name)

    # Скануємо код на наявність змінних
    for lex, tok in rpn_table:
        if tok in ('l-val', 'r-val'):
            if lex not in local_vars:
                used_globals.add(lex)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(".target: Postfix Machine\n")
        f.write(".version: 0.3\n\n")

        f.write(".vars(\n")
        if local_scope:
            sorted_vars = sorted(
                [k for k in local_scope.keys() if k != 'declIn' and local_scope[k][1] in ('variable', 'constant')],
                key=lambda k: local_scope[k][0]
            )

            for name in sorted_vars:
                attr = local_scope[name]
                f.write(f"\t{name}\t{attr[2]}\n")
        f.write(")\n\n")

        if used_globals:
            f.write(".globVarList(\n")
            for var in used_globals:
                f.write(f"\t{var}\n")
            f.write(")\n\n")

        f.write(".funcs(\n")
        if functions_in_scope:
            for func_name, attr in functions_in_scope.items():
                if func_name == 'declIn': continue
                if attr[1] == 'function':
                    return_type = attr[2]
                    num_params = len(attr[4])
                    f.write(f"\t{func_name}\t{return_type}\t{num_params}\n")
        f.write(")\n\n")

        f.write(".labels(\n")
        for lbl, addr in label_table.items():
            if addr != 'undef':
                f.write(f"\t{lbl}\t{addr}\n")
        f.write(")\n\n")

        f.write(".code(\n")
        for lexeme, token_type in rpn_table:
            f.write(f"\t{lexeme:<10}\t{token_type}\n")
        f.write(")\n")

    print(f"Generated: {output_path}")