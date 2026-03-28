"""
Database for Drinks
"""
import drinksdb
import argparse
import sys
import io
import json

_db = None

def get_db():
    global _db
    if _db is None:
        _db = drinksdb.DrinksDB()
    return _db

def show_drink(output, db, drink, use_json, no_headers, fields):
    if use_json:
        json_drink = json.dumps(drink)
        print(json_drink, file=output)
    else:
        header = ""
        if not fields:
            fields = ['name', 'glass', 'ingredients', 'instructions']
        if 'name' in fields:
            if not no_headers:
                header = "Name:  "
            print(f"{header}{drink['name']}", file=output)
        if 'glass' in drink and 'glass' in fields:
            if not no_headers:
                header = "Glass:  "
            print(f"{header}{drink['glass']}", file=output)
        if 'ingredients' in fields:
            if not no_headers:
                print("Ingredients:", file=output)
                header = "  "
            for m in drink['mixers']:
                print(f"{header}{m}", file=output)
            for s in drink['spirits']:
                print(f"{header}{s}", file=output)
        if 'instructions' in fields:
            if not no_headers:
                print('Instructions:', file=output)
                header = "  "
            step_num = 1
            for s in drink['steps']:
                print(f'{header}{step_num}. {s}', file=output)
                step_num += 1
        if 'volume' in fields:
            if not no_headers:
                header = "Volume:  "
            volume = 0.0
            for m in drink['mixers']:
                v = db.amount_from_namespec(m)
                if v > 0.1:
                    volume = volume + v
            for s in drink['spirits']:
                v = db.amount_from_namespec(s)
                if v > 0.1:
                    volume = volume + v
            print(f"{header}{volume}", file=output)
        if 'calories' in fields:
            if not no_headers:
                header = "Calories:  "
            calories = 0.0
            for m in drink['mixers']:
                name = db.name_from_namespec(m)
                amount = db.amount_from_namespec(m)
                nutrition = db.get_mixer_nutrition(name)
                if nutrition and nutrition['calories_per_oz'] is not None:
                    calories = calories + (amount * nutrition['calories_per_oz'])
            for s in drink['spirits']:
                name = db.name_from_namespec(s)
                amount = db.amount_from_namespec(s)
                nutrition = db.get_spirit_nutrition(name)
                if nutrition and nutrition['calories_per_oz'] is not None:
                    calories = calories + (amount * nutrition['calories_per_oz'])
            print(f"{header}{calories:.1f}", file=output)
        if 'abv' in fields:
            if not no_headers:
                header = "ABV:  "
            total_alcohol = 0.0
            total_volume = 0.0
            for m in drink['mixers']:
                name = db.name_from_namespec(m)
                amount = db.amount_from_namespec(m)
                nutrition = db.get_mixer_nutrition(name)
                if nutrition and nutrition['abv'] is not None:
                    total_alcohol = total_alcohol + (amount * nutrition['abv'] / 100)
                total_volume = total_volume + amount
            for s in drink['spirits']:
                name = db.name_from_namespec(s)
                amount = db.amount_from_namespec(s)
                nutrition = db.get_spirit_nutrition(name)
                if nutrition and nutrition['abv'] is not None:
                    total_alcohol = total_alcohol + (amount * nutrition['abv'] / 100)
                total_volume = total_volume + amount
            if total_volume > 0:
                abv = (total_alcohol / total_volume) * 100
                print(f"{header}{abv:.1f}%", file=output)
            else:
                print(f"{header}N/A", file=output)
    
def show_drink_summary(output, drink):
    print(f"{drink['name']}\t({len(drink['spirits'])})Spirits\t({len(drink['mixers'])})Mixers", file=output)

def get_args(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    parser_list = subparsers.add_parser('list')
    parser_list.add_argument("--terms", action="extend", nargs="*", type=str)
    
    parser_show = subparsers.add_parser('show')
    parser_show.add_argument('name')
    parser_show.add_argument("--json", action="store_true")
    parser_show.add_argument("--no_headers", action="store_true")
    parser_show.add_argument("--fields", action="extend", nargs="+", type=str)
    
    parser_new = subparsers.add_parser('new')
    parser_new.add_argument('name')
    parser_new.add_argument("--mixer", action="extend", nargs="+", type=str)
    parser_new.add_argument("--spirit", action="extend", nargs="+", type=str)
    parser_new.add_argument("--step", action="extend", nargs="+", type=str)
    parser_new.add_argument("--glass", type=str)

    parser_new = subparsers.add_parser('edit')
    parser_new.add_argument('name')
    parser_new.add_argument("--mixer", action="extend", nargs="+", type=str)
    parser_new.add_argument("--spirit", action="extend", nargs="+", type=str)
    parser_new.add_argument("--step", action="extend", nargs="+", type=str)
    parser_new.add_argument("--glass", type=str)
    
    parser_new = subparsers.add_parser('remove')
    parser_new.add_argument('name')

    parser_import = subparsers.add_parser('import')
    parser_import.add_argument('filename')

    parser_export = subparsers.add_parser('export')
    parser_export.add_argument('filename')
    
    parser_spirits = subparsers.add_parser('spirits')
    parser_spirits_commands = parser_spirits.add_subparsers(dest='spirits_command')
    parser_spirits_list = parser_spirits_commands.add_parser('list')
    parser_spirits_list.add_argument("--nutrition", action="store_true")
    parser_spirits_set = parser_spirits_commands.add_parser('set')
    parser_spirits_set.add_argument('name')
    parser_spirits_set.add_argument("--calories", type=float)
    parser_spirits_set.add_argument("--abv", type=float)

    parser_mixers = subparsers.add_parser('mixers')
    parser_mixers_commands = parser_mixers.add_subparsers(dest='mixers_command')
    parser_mixers_list = parser_mixers_commands.add_parser('list')
    parser_mixers_list.add_argument("--nutrition", action="store_true")
    parser_mixers_set = parser_mixers_commands.add_parser('set')
    parser_mixers_set.add_argument('name')
    parser_mixers_set.add_argument("--calories", type=float)
    parser_mixers_set.add_argument("--abv", type=float)

    parser_steps = subparsers.add_parser('steps')
    parser_steps_commands = parser_steps.add_subparsers(dest='steps_command')
    parser_steps_list = parser_steps_commands.add_parser('list')

    parser_glasses = subparsers.add_parser('glasses')
    parser_glasses_commands = parser_glasses.add_subparsers(dest='glasses_command')
    parser_glasses_list = parser_glasses_commands.add_parser('list')

    return parser.parse_args(argv)


# Main program -- if invoked from command line, otherwise, an entry point for UI
def process_command(argv = sys.argv[1:]):
    args = get_args(argv)
    db = get_db()
    output = io.StringIO()
    
    if args.command == 'new':
        new_drink = { 'name' : args.name,
                      'mixers' : args.mixer,
                      'spirits' : args.spirit,
                      'steps' : args.step,
                      'glass' : args.glass }
        db.new_drink(new_drink)
    elif args.command == 'edit':
        new_drink = { 'name' : args.name,
                      'mixers' : args.mixer,
                      'spirits' : args.spirit,
                      'steps' : args.step,
                      'glass' : args.glass }
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
            show_drink(output, db, drink, args.json, args.no_headers, args.fields)
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
                if args.nutrition:
                    nutrition = db.get_spirit_nutrition(s)
                    if nutrition and nutrition['calories_per_oz'] is not None and nutrition['abv'] is not None:
                        print(f"{s}\t{nutrition['calories_per_oz']} cal/oz\t{nutrition['abv']}% ABV", file=output)
                    else:
                        print(f"{s}\t--\t--", file=output)
                else:
                    print(s, file=output)
        elif args.spirits_command == 'set':
            db.set_spirit_nutrition(args.name, args.calories, args.abv)
            print(f"Updated {args.name}: {args.calories} cal/oz, {args.abv}% ABV", file=output)
    elif args.command == 'mixers':
        if args.mixers_command == 'list':
            mixers = db.list_mixers()
            for s in mixers:
                if args.nutrition:
                    nutrition = db.get_mixer_nutrition(s)
                    if nutrition and nutrition['calories_per_oz'] is not None and nutrition['abv'] is not None:
                        print(f"{s}\t{nutrition['calories_per_oz']} cal/oz\t{nutrition['abv']}% ABV", file=output)
                    else:
                        print(f"{s}\t--\t--", file=output)
                else:
                    print(s, file=output)
        elif args.mixers_command == 'set':
            db.set_mixer_nutrition(args.name, args.calories, args.abv)
            print(f"Updated {args.name}: {args.calories} cal/oz, {args.abv}% ABV", file=output)
    elif args.command == 'steps':
        if args.steps_command == 'list':
            steps = db.list_steps()
            for s in steps:
                print(s, file=output)
    elif args.command == 'glasses':
        if args.glasses_command == 'list':
            glasses = db.list_glasses()
            for g in glasses:
                print(g, file=output)
                
    return output

if __name__ == '__main__':
    print(process_command().getvalue())

