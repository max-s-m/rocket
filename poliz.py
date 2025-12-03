# Глобальні таблиці для ПОЛІЗ
main_rpn_table = []
main_label_table = {}

# Посилання на поточні таблиці (для обробки функцій)
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
    print(f"POLIZ: Appended ('{lex}', '{rpn_tok}')")


def create_label():
    label_index = len(main_label_table) + 1
    label_name = f"m{label_index}"
    main_label_table[label_name] = 'undef'
    print(f"POLIZ: Created label '{label_name}'")
    return (label_name, 'label')


def set_label_value(label_tuple):
    label_name, _ = label_tuple
    main_label_table[label_name] = len(current_rpn_table)
    print(f"POLIZ: Set label '{label_name}' to address {main_label_table[label_name]}")


def generate_postfix_file(filename, sym_table, rpn_table, label_table):
    output_path = f"{filename}.postfix"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(".target: Postfix Machine\n.version: 1.0\n\n")

        f.write(".vars(\n")
        if 'univ' in sym_table:
            for name, attr in sym_table['univ'].items():
                if name != 'declIn' and attr[1] == 'variable':
                    f.write(f"\t{name}\t{attr[2]}\n")
        f.write(")\n\n")

        f.write(".funcs(\n")
        if 'univ' in sym_table:
            for name, attr in sym_table['univ'].items():
                if name != 'declIn' and attr[1] == 'function':
                    return_type = attr[2]
                    num_params = len(attr[4])
                    f.write(f"\t{name}\t{return_type}\t{num_params}\n")
        f.write(")\n\n")

        f.write(".labels(\n")
        for lbl, addr in label_table.items():
            if addr != 'undef':
                f.write(f"\t{lbl}\t{addr}\n")
        f.write(")\n\n")

        f.write(".code(\n")
        for lexeme, token_type in rpn_table:
            f.write(f"\t{lexeme}\t{token_type}\n")
        f.write(")\n")

    print(f"\nPostfix file generated successfully: {output_path}")