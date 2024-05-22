import xml.etree.ElementTree as ET
from typing import List, Callable
import os

from myanki import MyModel

import genanki


def node_str(node):
    return f'{node.tag} {node.attrib} Children: {len(node)} {[n.tag for n in node]}\n'


def check_contain_attr(node_attr: str, attrs: List) -> bool:
    for attr in attrs:
        if attr in node_attr:
            return True
    return False


def child_recursive(node: ET.Element, parent_node_data: List, callback: Callable):
     
    simple_text_children, complex_element_children = [], []

    for child in node:
        if child.tag in ['span', 'p', 'ul', 'ol', 'dt', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            simple_text_children.append(child)
        elif child.attrib and 'class' in child.attrib and check_contain_attr(child.attrib['class'], ['highlight-python3', 'highlight-pycon', 'doctest', 'describe', 'py method', 'py attribute', 'responsive-table__container', 'admonition']):
            complex_element_children.append(child)
    
    for child in simple_text_children + complex_element_children:
        node.remove(child)

    for child in node:
        this_node_data = ''
        if child.attrib and 'id' in child.attrib:
            this_node_data = child.attrib['id']
        child_recursive(child, parent_node_data + [this_node_data], callback)
    
    red_box_div = ET.Element('div')
    red_box_div.attrib['style'] = 'border-style: dotted; border-width: 5px; border-color: red;'
    red_box_div.text = f'=== {parent_node_data} ===\n'
    red_box_div.extend(simple_text_children)
    node.insert(0, red_box_div)
    callback(red_box_div)

    for child in complex_element_children:
        blue_box_div = ET.Element('div')
        blue_box_div.attrib['style'] = 'border-style: dotted; border-width: 5px; border-color: blue;'
        blue_box_div.text = f'=== {parent_node_data} ===\n'
        blue_box_div.append(child)
        node.append(blue_box_div)
        callback(blue_box_div)




def node_to_anki(nodes: List[ET.Element]):
    filename = 'Python Docs'
    my_model = MyModel(filename, fields=[{'name': 'Question'}, {'name': 'Answer'}, {
      'name': 'Media'}, {'name': 'TableOfContent'}])

    my_deck = genanki.Deck(deck_id=abs(hash(filename)) % (10 ** 10), name=filename)

    for i, n in enumerate(nodes):
        os.makedirs('out', exist_ok=True)
        ET.ElementTree(n).write(f'out/{i}.html', encoding='utf-8')
        
        with open(f'out/{i}.html', 'r', encoding='utf-8') as f:
            content = f.read()

            anki_note = genanki.Note(model=my_model, fields=[content, content, '', ''], tags='')
            my_deck.add_note(anki_note)

    anki_output = genanki.Package(my_deck)
    anki_output.write_to_file(filename+'.apkg')
    
    

if __name__ == '__main__':
    tree = ET.parse('tmp.html')

    out_nodes = []
    def callback(node):
        out_nodes.append(node)
    
    child_recursive(tree.getroot(), [], callback)

    node_to_anki(out_nodes)
    
    tree.write('out.html', encoding='utf-8')


