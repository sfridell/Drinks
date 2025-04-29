import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.properties import ListProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.dropdown import DropDown
from kivy.uix.recycleview import RecycleView
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.factory import Factory
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.uix.button import MDTextButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel

import re
import drinks
from functools import partial
from plyer import filechooser

if platform == 'android':
    from androidstorage4kivy import SharedStorage
    from androidstorage4kivy import Chooser

Builder.load_file('main.kv')

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

class NewDrinkPopup(Popup):
    def __init__(self, **kwargs):
        super(NewDrinkPopup, self).__init__()

    def add_spirit_selector(self):
        layout = self.ids.spirit_select
        selector = Factory.IngredientSelectPair('spirits')
        layout.add_widget(selector)

    def add_mixer_selector(self):
        layout = self.ids.mixer_select
        selector = Factory.IngredientSelectPair('mixers')
        layout.add_widget(selector)

    def add_steps_selector(self):
        layout = self.ids.steps_select
        selector = Factory.MutableSpinner()
        result = drinks.process_command(['steps', "list"])
        lines = result.getvalue().splitlines()
        selector.text = lines[0]
        selector.values = ['<new>'] + lines
        selector.values = selector.values[:10]
        layout.add_widget(selector)
        
class IngredientSelectPair(BoxLayout):
    selection_type = ObjectProperty()
    
    def __init__(self, selection_type, **kwargs):
        super(IngredientSelectPair, self).__init__()
        print(selection_type)
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
        self.drink_list.data = [{'text': line, 'on_press': partial(self.show_drink, line)} for line in lines]
        self.drink_list.refresh_from_data()

    def _refresh(self):
        result = drinks.process_command(['list'])
        lines = result.getvalue().splitlines()
        self.drink_list.data = [{'text': line, 'on_press': partial(self.show_drink, line)} for line in lines]
        self.drink_list.refresh_from_data()

    def show_drink(self, text):
        popup = Factory.DisplayDrinkPopup()
        name = self.name_re.match(text).group(1)
        result = drinks.process_command(["show", name])
        popup.details.text = result.getvalue()
        popup.open()

    def input_new_drink(self):
        popup = Factory.NewDrinkPopup()
        popup.open()
        
    def choose_json_file(self):
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
        
class DrinksApp(MDApp):

    def build(self):
        return HomeScreen()

if __name__ == '__main__':
    DrinksApp().run()

