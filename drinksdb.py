import sqlite3
import os
import json
import plyer

NUTRITION_FILE = 'ingredients_nutrition.json'

class DrinksDB:
    def __init__(self):
        dbpath = './drinks.db'
        self._con = sqlite3.connect(dbpath)
        self._cur = self._con.cursor()
        self._cur.execute("CREATE TABLE IF NOT EXISTS drinks(id INTEGER PRIMARY KEY AUTOINCREMENT, recipe)")
        self._cur.execute("CREATE TABLE IF NOT EXISTS spirits(spirit TEXT PRIMARY KEY, calories_per_oz REAL, abv REAL)")
        self._cur.execute("CREATE TABLE IF NOT EXISTS mixers(mixer TEXT PRIMARY KEY, calories_per_oz REAL, abv REAL)")
        self._cur.execute("CREATE TABLE IF NOT EXISTS steps(step TEXT PRIMARY KEY)")
        self._cur.execute("CREATE TABLE IF NOT EXISTS glasses(glass TEXT PRIMARY KEY)")
        try:
            self._cur.execute("ALTER TABLE spirits ADD COLUMN calories_per_oz REAL")
        except:
            pass
        try:
            self._cur.execute("ALTER TABLE spirits ADD COLUMN abv REAL")
        except:
            pass
        try:
            self._cur.execute("ALTER TABLE mixers ADD COLUMN calories_per_oz REAL")
        except:
            pass
        try:
            self._cur.execute("ALTER TABLE mixers ADD COLUMN abv REAL")
        except:
            pass
        query = "INSERT OR IGNORE INTO glasses (glass) VALUES (?)"
        self._cur.execute(query, ('coupe',))
        self._cur.execute(query, ('rocks',))
        self._cur.execute(query, ('wine',))
        self._cur.execute(query, ('hiball',))
        self._con.commit()
        self._populate_nutrition_if_needed()
        
    def _populate_nutrition_if_needed(self):
        spirits = self.list_spirits()
        mixers = self.list_mixers()
        needs_population = False
        
        if not spirits and not mixers:
            needs_population = True
        else:
            for s in spirits:
                nutrition = self.get_spirit_nutrition(s)
                if not nutrition or nutrition['calories_per_oz'] is None:
                    needs_population = True
                    break
            if not needs_population:
                for m in mixers:
                    nutrition = self.get_mixer_nutrition(m)
                    if not nutrition or nutrition['calories_per_oz'] is None:
                        needs_population = True
                        break
        
        if needs_population and os.path.exists(NUTRITION_FILE):
            with open(NUTRITION_FILE) as f:
                data = json.load(f)
            for spirit, values in data.get('spirits', {}).items():
                self.set_spirit_nutrition(spirit, values['calories_per_oz'], values['abv'])
            for mixer, values in data.get('mixers', {}).items():
                self.set_mixer_nutrition(mixer, values['calories_per_oz'], values['abv'])
        
    def name_from_namespec(self, namespec):
        return namespec[0:namespec.index(':')]

    def amount_from_namespec(self, namespec):
        return float(namespec[namespec.index(':')+1:])
    
    def new_drink(self, drink):
        print(f'trying to add drink {drink["name"]}')
        if self.get_drink_by_name(drink['name']):
            print('Drink exists')
            return
        if not "glass" in drink:
            drink["glass"] = 'coupe'
        serialized_drink = json.dumps(drink)
        print('serialized drink: %s' % serialized_drink)
        for s in drink["spirits"]:
            self._cur.execute(f"INSERT OR IGNORE INTO spirits (spirit, calories_per_oz, abv) VALUES (\'{self.name_from_namespec(s)}\', NULL, NULL)")
        for m in drink["mixers"]:
            self._cur.execute(f"INSERT OR IGNORE INTO mixers (mixer, calories_per_oz, abv) VALUES (\'{self.name_from_namespec(m)}\', NULL, NULL)")
        for s in drink["steps"]:
            self._cur.execute(f"INSERT OR IGNORE INTO steps VALUES (\'{s}\')")
        res = self._cur.execute(f"SELECT * FROM glasses WHERE glass = \'{drink['glass']}\'")
        row = res.fetchall()
        if not row:
            raise Exception('No such glass')
        self._cur.execute(f"INSERT OR IGNORE INTO drinks VALUES (null, \'{serialized_drink}\')")
        self._con.commit()

    def update_drink(self, new_drink):
        print(f'trying to update drink {new_drink["name"]}')
        drink = self.get_drink_by_name(new_drink['name'])
        if not drink:
            print('Drink does not exist')
            return
        if new_drink["spirits"]:
            drink["spirits"] = new_drink["spirits"]
        if new_drink["mixers"]:
            drink["mixers"] = new_drink["mixers"]
        if new_drink["steps"]:
            drink["steps"] = new_drink["steps"]
        if new_drink["glass"]:
            drink["glass"] = new_drink["glass"]
        if not "glass" in drink:
            drink["glass"] = 'coupe'
        for s in drink["spirits"]:
            self._cur.execute(f"INSERT OR IGNORE INTO spirits (spirit, calories_per_oz, abv) VALUES (\'{self.name_from_namespec(s)}\', NULL, NULL)")
        for m in drink["mixers"]:
            self._cur.execute(f"INSERT OR IGNORE INTO mixers (mixer, calories_per_oz, abv) VALUES (\'{self.name_from_namespec(m)}\', NULL, NULL)")
        for s in drink["steps"]:
            self._cur.execute(f"INSERT OR IGNORE INTO steps VALUES (\'{s}\')")
        res = self._cur.execute(f"SELECT * FROM glasses WHERE glass = \"{drink['glass']}\"")
        row = res.fetchall()
        if not row:
            raise Exception('No such glass')
        self.remove_drink_by_name(drink["name"])
        serialized_drink = json.dumps(drink)
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
            data = json.load(f)    
        for d in data.get('drinks', []):
            self.new_drink(d)
        for s in data.get('spirits', []):
            if 'name' in s and s.get('calories_per_oz') is not None and s.get('abv') is not None:
                self.set_spirit_nutrition(s['name'], s['calories_per_oz'], s['abv'])
        for m in data.get('mixers', []):
            if 'name' in m and m.get('calories_per_oz') is not None and m.get('abv') is not None:
                self.set_mixer_nutrition(m['name'], m['calories_per_oz'], m['abv'])

    def export_drinks_to_file(self, filename):
        output = { 
            'drinks' : self.find_drinks(),
            'spirits': [],
            'mixers': []
        }
        for s in self.list_spirits():
            nutrition = self.get_spirit_nutrition(s)
            output['spirits'].append({
                'name': s,
                'calories_per_oz': nutrition['calories_per_oz'] if nutrition else None,
                'abv': nutrition['abv'] if nutrition else None
            })
        for m in self.list_mixers():
            nutrition = self.get_mixer_nutrition(m)
            output['mixers'].append({
                'name': m,
                'calories_per_oz': nutrition['calories_per_oz'] if nutrition else None,
                'abv': nutrition['abv'] if nutrition else None
            })
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

    def set_spirit_nutrition(self, spirit, calories_per_oz, abv):
        self._cur.execute(f"INSERT OR REPLACE INTO spirits (spirit, calories_per_oz, abv) VALUES (\'{spirit}\', {calories_per_oz}, {abv})")
        self._con.commit()

    def set_mixer_nutrition(self, mixer, calories_per_oz, abv):
        self._cur.execute(f"INSERT OR REPLACE INTO mixers (mixer, calories_per_oz, abv) VALUES (\'{mixer}\', {calories_per_oz}, {abv})")
        self._con.commit()

    def get_spirit_nutrition(self, spirit):
        res = self._cur.execute(f"SELECT calories_per_oz, abv FROM spirits WHERE spirit = \'{spirit}\'")
        row = res.fetchone()
        if row:
            return {'calories_per_oz': row[0], 'abv': row[1]}
        return None

    def get_mixer_nutrition(self, mixer):
        res = self._cur.execute(f"SELECT calories_per_oz, abv FROM mixers WHERE mixer = \'{mixer}\'")
        row = res.fetchone()
        if row:
            return {'calories_per_oz': row[0], 'abv': row[1]}
        return None

    def list_steps(self):
        res = self._cur.execute(f"SELECT * FROM steps")
        steps = res.fetchall()
        return [ s[0] for s in steps ]

    def list_glasses(self):
        res = self._cur.execute(f"SELECT * FROM glasses")
        glasses = res.fetchall()
        return [ g[0] for g in glasses ]

