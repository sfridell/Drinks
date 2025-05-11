import sqlite3
import os
import json
import plyer

class DrinksDB:
    def __init__(self):
        dbpath = './drinks.db'
        self._con = sqlite3.connect(dbpath)
        self._cur = self._con.cursor()
        self._cur.execute("CREATE TABLE IF NOT EXISTS drinks(id INTEGER PRIMARY KEY AUTOINCREMENT, recipe)")
        self._cur.execute("CREATE TABLE IF NOT EXISTS spirits(spirit TEXT PRIMARY KEY)")
        self._cur.execute("CREATE TABLE IF NOT EXISTS mixers(mixer TEXT PRIMARY KEY)")
        self._cur.execute("CREATE TABLE IF NOT EXISTS steps(step TEXT PRIMARY KEY)")
        
    def _name_from_namespec(self, namespec):
        return namespec[0:namespec.index(':')]
        
    def new_drink(self, drink):
        print(f'trying to add drink {drink["name"]}')
        if self.get_drink_by_name(drink['name']):
            print('Drink exists')
            return
        serialized_drink = json.dumps(drink)
        print('serialized drink: %s' % serialized_drink)
        for s in drink["spirits"]:
            self._cur.execute(f"INSERT OR IGNORE INTO spirits VALUES (\'{self._name_from_namespec(s)}\')")
        for m in drink["mixers"]:
            self._cur.execute(f"INSERT OR IGNORE INTO mixers VALUES (\'{self._name_from_namespec(m)}\')")
        for s in drink["steps"]:
            self._cur.execute(f"INSERT OR IGNORE INTO steps VALUES (\'{s}\')")
        self._cur.execute(f"INSERT OR IGNORE INTO drinks VALUES (null, \'{serialized_drink}\')")
        self._con.commit()
        
    def find_drinks(self, terms=[]):
        where_clause = 'WHERE TRUE'
        for t in terms:
            where_clause += f" AND instr(recipe, '{t}') > 0"
        res = self._cur.execute(f"SELECT * FROM drinks {where_clause}")
        drinks = res.fetchall()
        return [ json.loads(d[1]) for d in drinks ]

    def get_drink_by_name(self, name):
        res = self._cur.execute(f"SELECT * FROM drinks WHERE json_extract(recipe, \'$.name\') = \'{name}\'")
        row = res.fetchall()
        if not row:
            return None
        drink = row[0][1]
        return json.loads(drink)

    def remove_drink_by_name(self, name):
        res = self._cur.execute(f"DELETE FROM drinks WHERE json_extract(recipe, \'$.name\') = \'{name}\'")
        self._con.commit()
        
    def import_drinks_from_file(self, filename):
        with open(filename) as f:
            drinks = json.load(f)    
        for d in drinks['drinks']:
            self.new_drink(d)

    def export_drinks_to_file(self, filename):
        output = { 'drinks' : self.find_drinks() }
        with open(filename, "w") as f:
            json.dump(output, f, indent=5)
        
    def list_spirits(self):
        res = self._cur.execute(f"SELECT * FROM spirits")
        spirits = res.fetchall()
        return [ s[0] for s in spirits ]

    def list_mixers(self):
        res = self._cur.execute(f"SELECT * FROM mixers")
        mixers = res.fetchall()
        return [ m[0] for m in mixers ]

    def list_steps(self):
        res = self._cur.execute(f"SELECT * FROM steps")
        steps = res.fetchall()
        return [ s[0] for s in steps ]

