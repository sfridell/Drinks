"""
Database for Drinks
"""
import drinksdb
import argparse
import sys
import io

def show_drink(output, drink):
    print(f"-----{drink['name']}----", file=output)
    print("Ingredients:", file=output)
    for m in drink['mixers']:
        print(m, file=output)
    for s in drink['spirits']:
        print(s, file=output)
    print('Instructions:', file=output)
    step_num = 1
    for s in drink['steps']:
        print(f'{step_num}. {s}', file=output)
        step_num += 1

def show_drink_summary(output, drink):
    print(f"Name: {drink['name']} Spirits({len(drink['spirits'])}) Mixers({len(drink['mixers'])})", file=output)

def get_args(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    parser_list = subparsers.add_parser('list')
    parser_list.add_argument("--terms", action="extend", nargs="*", type=str)
    
    parser_show = subparsers.add_parser('show')
    parser_show.add_argument('name')
    
    parser_new = subparsers.add_parser('new')
    parser_new.add_argument('name')
    parser_new.add_argument("--mixer", action="extend", nargs="+", type=str)
    parser_new.add_argument("--spirit", action="extend", nargs="+", type=str)
    parser_new.add_argument("--step", action="extend", nargs="+", type=str)

    parser_new = subparsers.add_parser('edit')
    parser_new.add_argument('name')
    parser_new.add_argument("--mixer", action="extend", nargs="+", type=str)
    parser_new.add_argument("--spirit", action="extend", nargs="+", type=str)
    parser_new.add_argument("--step", action="extend", nargs="+", type=str)

    parser_new = subparsers.add_parser('remove')
    parser_new.add_argument('name')

    parser_import = subparsers.add_parser('import')
    parser_import.add_argument('filename')

    parser_export = subparsers.add_parser('export')
    parser_export.add_argument('filename')
    
    parser_spirits = subparsers.add_parser('spirits')
    parser_spirits_commands = parser_spirits.add_subparsers(dest='spirits_command')
    parser_spirits_list = parser_spirits_commands.add_parser('list')

    parser_mixers = subparsers.add_parser('mixers')
    parser_mixers_commands = parser_mixers.add_subparsers(dest='mixers_command')
    parser_mixers_list = parser_mixers_commands.add_parser('list')

    parser_steps = subparsers.add_parser('steps')
    parser_steps_commands = parser_steps.add_subparsers(dest='steps_command')
    parser_steps_list = parser_steps_commands.add_parser('list')

    return parser.parse_args(argv)


# Main program -- if invoked from command line, otherwise, an entry point for UI
def process_command(argv = sys.argv[1:]):
    args = get_args(argv)
    db = drinksdb.DrinksDB()
    output = io.StringIO()
    
    if args.command == 'new':
        new_drink = { 'name' : args.name,
                      'mixers' : args.mixer,
                      'spirits' : args.spirit,
                      'steps' : args.step }
        db.new_drink(new_drink)
    elif args.command == 'edit':
        new_drink = { 'name' : args.name,
                      'mixers' : args.mixer,
                      'spirits' : args.spirit,
                      'steps' : args.step }
        db.update_drink(new_drink)
    elif args.command == 'list':
        drinks = db.find_drinks(args.terms if args.terms else [])
        for d in drinks:
            show_drink_summary(output, d)
    elif args.command == 'show':
        drink = db.get_drink_by_name(args.name)
        if not drink:
            print('Not found.', file=output)
        else:
            show_drink(output, drink)
    elif args.command == 'remove':
        db.remove_drink_by_name(args.name)
    elif args.command == 'import':
        db.import_drinks_from_file(args.filename)
    elif args.command == 'export':
        db.export_drinks_to_file(args.filename)
    elif args.command == 'spirits':
        if args.spirits_command == 'list':
            spirits = db.list_spirits()
            for s in spirits:
                print(s, file=output)
    elif args.command == 'mixers':
        if args.mixers_command == 'list':
            mixers = db.list_mixers()
            for s in mixers:
                print(s, file=output)
    elif args.command == 'steps':
        if args.steps_command == 'list':
            steps = db.list_steps()
            for s in steps:
                print(s, file=output)
                
    return output

if __name__ == '__main__':
    print(process_command().getvalue())

