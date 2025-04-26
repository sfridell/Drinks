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
    
Builder.load_string('''
<InputPopup>
    title: ""
    input_text: input_text
    size_hint : 0.9, 0.2

    BoxLayout:
        orientation: "vertical"
        height: "40dp"

        TextInput:
            id: input_text
            multiline: False
            hint_text: "enter text"

        Button:
            text: "close"
            on_release: root.save_input()

<IngredientSelectPair>
    orientation: "horizontal"
    
    Spinner:
        id: amount_input
        text: "1.0oz"
        values: [ "0.25oz", "0.5oz", "0.75oz", "1.0oz", "1.25oz", "1.5oz" ]
    Spinner:
        id: ingredient_input
        text: "new"
        values: [ "new" ]

<NewDrinkPopup>
    title: "Add a drink"
    separator_height: 0
    auto_dismiss: False
    size_hint: 0.8, 0.8
    pos_hint: {"x":0.1, "y":0.1}

    BoxLayout:
        orientation: "vertical"
        size: root.width, root.height

        MDTextField:
            mode: "fill"
            hint_text: "Drink name"
            max_text_length: 30

        BoxLayout:
            id: spirit_select
            orientation: "vertical"

            BoxLayout:
                orientation: "horizontal"

                MDLabel:
                    color: "white"
                    text: "choose spirits and amounts"
                MDIconButton:
                    icon: "plus"
                    theme_icon_color: "Custom"
                    icon_color: "white"
                    on_release: root.add_spirit_selector()

        BoxLayout:
            id: mixer_select
            orientation: "vertical"

            BoxLayout:
                orientation: "horizontal"

                MDLabel:
                    color: "white"
                    text: "choose mixers and amounts"
                MDIconButton:
                    icon: "plus"
                    theme_icon_color: "Custom"
                    icon_color: "white"
                    on_release: root.add_mixer_selector()

        Button:
            text: "close"
            size_hint: 1.0, 0.2
            on_release: root.dismiss()


<DisplayDrinkPopup@Popup>
    title: ""
    separator_height: 0
    auto_dismiss: False
    size_hint: 0.8, 0.8
    pos_hint: {"x":0.1, "y":0.1}
    details: drink_details

    BoxLayout:
        orientation: "vertical"
        size: root.width, root.height

        Label:
            id: drink_details
            text: ""

        Button:
            size_hint: 0.4, 0.1
            pos_hint: {"x":0.3, "y":0.9}
            text: "close"
            on_release: root.dismiss()
        
<HomeScreen>:
    id: home_screen
    orientation: "vertical"
    filter: filter_input
    drink_list: drink_list_view
    padding: 10
    spacing: 10

    BoxLayout:
        size_hint_y: None
        height: "40dp"
 
        Label:
            text: "filter"
        TextInput:
            id: filter_input
            hint_text: "enter keywords"
            multiline: False
            on_text_validate: root.run_filter()

    RecycleView:
        id: drink_list_view
        viewclass: 'Button'
        RecycleBoxLayout:
            default_size: None, dp(56)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'

    Button:
        size_hint: 0.4, 0.1
        pos_hint: {"x":0.3, "y":0.9}
        text: "new drink"
        on_release: root.input_new_drink()

    Button:
        size_hint: 0.4, 0.1
        pos_hint: {"x":0.3, "y":0.9}
        text: "refresh db"
        on_release: root.choose_json_file()
''')

class InputPopup(Popup):
    caller = ObjectProperty(None)

    def __init__(self, caller=None, **kwargs):
        super(InputPopup, self).__init__()
        self.caller = caller
        
    def save_input(self, *args):
        self.caller.values.append(self.input_text.text)
        self.caller.selected_values.append(self.input_text.text)
        self.dismiss()

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

        
class IngredientSelectPair(BoxLayout):
    selection_type = ObjectProperty()
    
    def __init__(self, selection_type, **kwargs):
        super(IngredientSelectPair, self).__init__()
        print(selection_type)
        self.selection_type = selection_type
        result = drinks.process_command([self.selection_type, "list"])
        lines = result.getvalue().splitlines()
        self.ids.ingredient_input.text = lines[0]
        self.ids.ingredient_input.values = lines
            
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

