import xml.etree.ElementTree as ET
from typing import List, Callable
import io

from myanki import MyModel

import genanki


def node_str(node):
    return f'{node.tag} {node.attrib} Children: {len(node)} {[n.tag for n in node]}\n'


def get_node_header(node: ET.Element) -> ET.Element:
    for child in node:
        if child.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return child
    return None


def draw_boundary(node: ET.Element, **kwargs):
    parent_nodes = kwargs.get('parent_nodes', [])
    node.attrib['style'] = 'border-style: dotted; border-width: 5px; border-color: red;'
    node.text = f'=== {parent_nodes} ===\n'


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
        child_recursive(child, parent_node_data + [get_node_header(child)], callback)

    red_box_div = ET.Element('div')
    red_box_div.extend(simple_text_children)
    callback(red_box_div, parent_nodes=parent_node_data + [node])
    node.insert(0, red_box_div)
    

    for child in complex_element_children:
        blue_box_div = ET.Element('div')
        callback(blue_box_div, parent_nodes=parent_node_data + [node])
        blue_box_div.append(child)
        node.append(blue_box_div)
        




def node_to_anki(nodes: List[ET.Element]):
    filename = 'Python Docs'
    css = open('pydoctheme.css').read()
    my_model = MyModel(filename, css=css, fields=[{'name': 'Question'}, {'name': 'Answer'}, {
      'name': 'Media'}, {'name': 'TableOfContent'}])

    my_deck = genanki.Deck(deck_id=abs(hash(filename)) % (10 ** 10), name=filename)

    for i, n in enumerate(nodes):
        string_io = io.BytesIO()
        ET.ElementTree(n).write(string_io, encoding='utf-8')
        
        content = string_io.getvalue().decode('utf-8')

        anki_note = genanki.Note(model=my_model, fields=[content, content, '', ''], tags='')
        my_deck.add_note(anki_note)

        string_io.close()

    anki_output = genanki.Package(my_deck)
    anki_output.write_to_file(filename+'.apkg')
    
    

if __name__ == '__main__':
    tree = ET.parse('tmp.html')

    out_nodes = []
    def callback(node, **kwargs):
        draw_boundary(node, **kwargs)
        out_nodes.append(node)
    
    child_recursive(tree.getroot(), [], callback)

    node_to_anki(out_nodes)
    
    tree.write('out.html', encoding='utf-8')


