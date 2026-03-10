import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.properties import ListProperty
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.dropdown import DropDown
from kivy.uix.recycleview import RecycleView
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image, CoreImage
from kivy.factory import Factory
from kivy.utils import platform
from kivy.graphics.svg import Svg
from kivy.graphics import PushMatrix, PopMatrix, Scale, Translate
from kivy.properties import StringProperty
from kivymd.app import MDApp
from kivymd.uix.button import MDTextButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel

import re
import drinks
import datetime
import json
from functools import partial
from plyer import filechooser


if platform == 'android':
    from androidstorage4kivy import SharedStorage
    from androidstorage4kivy import Chooser
    from android import autoclass
    Environment = autoclass('android.os.Environment')

class SvgWidget(BoxLayout):
    source = StringProperty('')
    
    def __init__(self, **kwargs):
        super(SvgWidget, self).__init__(**kwargs)
        self.bind(source=self.reload_svg, size=self.reload_svg, pos=self.reload_svg)
        
    def reload_svg(self, *args):
        self.canvas.after.clear()
        if self.source:
            svg = Svg(self.source)
            scale = min(self.width / svg.width, self.height / svg.height) if svg.width and svg.height else 1
            with self.canvas.after:
                PushMatrix()
                Scale(scale, scale, 1)
                Translate(self.x / scale, self.y / scale)
                Svg(self.source)
                PopMatrix()

Builder.load_file('main.kv')
def name_from_namespec(namespec):
    return namespec[0:namespec.index(':')]

def amount_from_namespec(namespec):
    return float(namespec[namespec.index(':')+1:])

class InfoPopup(Popup):
    def __init__(self, message):
        super(InfoPopup, self).__init__()
        self.title = message

class ConfirmDeletePopup(Popup):
    def __init__(self, parent_popup):
        super(ConfirmDeletePopup, self).__init__()
        self.parent_popup = parent_popup
        
class InputPopup(Popup):
    caller = ObjectProperty(None)

    def __init__(self, target=None, **kwargs):
        super(InputPopup, self).__init__()
        self.target = target
        
    def save_input(self, *args):
        self.target.values.append(self.input_text.text)
        self.target.text = self.input_text.text
        self.dismiss()

class MutableSpinner(Spinner):
    def __init__(self, **kwargs):
        super(MutableSpinner, self).__init__()
        self.text = '<new>'
        self.values = ['<new>']
        self.bind(text=self.on_value_select)

    def on_value_select(self, obj, text):
        if text == '<new>':
            popup = Factory.InputPopup(self)
            popup.open()
            
class DisplayDrinkPopup(Popup):
    def __init__(self, name, glass, volume, details):
        super(DisplayDrinkPopup, self).__init__()
        self.title = name.upper()
        self.name = name
        self.glass.source = f"./images/{glass}-glass.svg"
        self.ounces.text = f"{volume}oz"
        self.details.text = details

class NewDrinkPopup(Popup):
    def __init__(self, caller=None, edit_drink=None, **kwargs):
        super(NewDrinkPopup, self).__init__()
        self.edit = False
        self.spirits = []
        self.mixers = []
        self.steps = []
        self.caller = caller
        selector = self.ids.glass_input
        result = drinks.process_command(['glasses', 'list'])
        lines = result.getvalue().splitlines()
        selector.text = lines[0]
        selector.values = lines
        if edit_drink:
            self.edit = True
            self._populate_drink(edit_drink)

    def _populate_drink(self, drink):
        self.ids.name_input.text = drink["name"]
        for s in drink["spirits"]:
            self.add_spirit_selector()
            self.spirits[-1].ids.ingredient_input.text = name_from_namespec(s)
            self.spirits[-1].ids.amount_input.text = f'{amount_from_namespec(s)}oz'
        for m in drink["mixers"]:
            self.add_mixer_selector()
            self.mixers[-1].ids.ingredient_input.text = name_from_namespec(m)
            self.mixers[-1].ids.amount_input.text = f'{amount_from_namespec(m)}oz'
        for s in drink["steps"]:
            self.add_steps_selector()
            self.steps[-1].text = s
        self.ids.glass_input.text = drink["glass"]

    def add_spirit_selector(self):
        layout = self.ids.spirit_select
        self.spirits.append(Factory.IngredientSelectPair('spirits'))
        layout.add_widget(self.spirits[-1])

    def add_mixer_selector(self):
        layout = self.ids.mixer_select
        self.mixers.append(Factory.IngredientSelectPair('mixers'))
        layout.add_widget(self.mixers[-1])

    def add_steps_selector(self):
        layout = self.ids.steps_select
        selector = Factory.MutableSpinner()
        result = drinks.process_command(['steps', "list"])
        lines = result.getvalue().splitlines()
        selector.text = lines[0]
        selector.values = ['<new>'] + lines
        selector.values = selector.values[:10]
        self.steps.append(selector)
        layout.add_widget(self.steps[-1])

    def save_drink(self):
        self.caller.save_drink(self.edit,
                               self.ids.name_input.text,
                               self.mixers,
                               self.spirits,
                               self.steps,
                               self.ids.glass_input.text)
        self.dismiss()
        self.caller.show_drink(f"Name: {self.ids.name_input.text} Spirits")
        
class IngredientSelectPair(BoxLayout):
    selection_type = ObjectProperty()
    
    def __init__(self, selection_type, **kwargs):
        super(IngredientSelectPair, self).__init__()
        self.selection_type = selection_type
        result = drinks.process_command([self.selection_type, "list"])
        lines = result.getvalue().splitlines()
        self.ids.ingredient_input.text = lines[0]
        self.ids.ingredient_input.values = self.ids.ingredient_input.values + lines

class HomeScreen(BoxLayout):
    drink_list = ObjectProperty()
    name_re = re.compile('Name: (.*) Spirits')
    
    def __init__(self, **kwargs):
        super(HomeScreen, self).__init__(**kwargs)
        self._refresh()

    def run_filter(self):
        filter_args = self.filter.text.split()
        result = drinks.process_command(["list", "--terms"] + filter_args)
        lines = result.getvalue().splitlines()
        lines = [ l.split('\t')[0] for l in lines ]
        lines = sorted(lines)
        self.drink_list.data = [{'text': line, 'on_press': partial(self.show_drink, line)} for line in lines]
        self.drink_list.refresh_from_data()

    def _refresh(self):
        result = drinks.process_command(['list'])
        lines = result.getvalue().splitlines()
        lines = [ l.split('\t')[0] for l in lines ]
        lines = sorted(lines)
        self.drink_list.data = [{'text': line, 'on_press': partial(self.show_drink, line), } for line in lines]
        self.drink_list.refresh_from_data()

    def show_drink(self, text):
        name = text
        glass = drinks.process_command(["show", name, "--no_headers", "--fields", "glass"]).getvalue().rstrip()
        volume = drinks.process_command(["show", name, "--no_headers", "--fields", "volume"]).getvalue().rstrip()
        details = drinks.process_command(["show", name, "--fields", "ingredients", "instructions"]).getvalue().rstrip()
        popup = Factory.DisplayDrinkPopup(name, glass, volume, details)
        popup.open()

    def input_new_drink(self):
        popup = Factory.NewDrinkPopup(caller=self)
        popup.open()

    def edit_drink(self, name, drink_popup):
        drink = json.loads(drinks.process_command(["show", name, "--json"]).getvalue())
        popup = Factory.NewDrinkPopup(caller=self, edit_drink=drink)
        popup.open()
        drink_popup.dismiss()
        
    def save_drink(self, edit, name, mixers, spirits, steps, glass):
        if edit:
            command = ['edit']
        else:
            command = [ "new" ]
        # name
        command = command + [ name ]
        # get mixers
        command = command + [ "--mixer" ]
        for mixer in mixers:
            command = command + [ f"{mixer.ids.ingredient_input.text}:{mixer.ids.amount_input.text[:-2]}" ]
        # get spirits
        command = command + [ "--spirit" ]
        for spirit in spirits:
            command = command + [ f"{spirit.ids.ingredient_input.text}:{spirit.ids.amount_input.text[:-2]}" ]
        # get steps
        command = command + [ "--step" ]
        for step in steps:
            command = command + [ f"{step.text}" ]
        # get glass
        command = command + [ "--glass", glass ]
        drinks.process_command(command)
        self._refresh()

    def delete_drink_complete(self, confirm_popup, display_popup):
        drinks.process_command([ "remove", display_popup.title ])
        confirm_popup.dismiss()
        display_popup.dismiss()
        self._refresh()
        
    def delete_drink_confirm(self, name, display_popup):
        popup = Factory.ConfirmDeletePopup(display_popup)
        popup.title = f"Really delete drink {name}?"
        popup.open()
        
    def choose_json_import_file(self):
        if platform == 'android':
            Chooser(self.import_from_json).choose_content()
        else:
            filechooser.open_file(on_selection=self.import_from_json)
            
    def import_from_json(self, selection):        
        if platform == 'android':
            filename = SharedStorage().copy_from_shared(selection[0])
        else:
            filename = selection[0]
        result = drinks.process_command(["import", filename])
        self._refresh()

    def export_to_json(self):
        filename = "./drinksdb.backup-" + str(datetime.datetime.now()) + ".json"
        drinks.process_command(["export", filename])
        if platform == 'android':
            uri = SharedStorage().copy_to_shared(filename, collection=Environment.DIRECTORY_DOWNLOADS)
            print("copied file " + filename + " to URI: " + str(uri))
        popup = Factory.InfoPopup("DB exported to file: " + filename)
        popup.open()
        
class DrinksApp(MDApp):

    def build(self):
        return HomeScreen()

if __name__ == '__main__':
    DrinksApp().run()

