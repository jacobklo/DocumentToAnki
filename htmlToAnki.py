
import xml.etree.ElementTree as ET
from typing import List, Callable
import io

from myanki import MyModel

import genanki


def get_parent_hierarchy(node: ET.Element, **kwargs) -> str:
    '''
    For each parent node, get the id attribute and return as a string
    '''
    parent_nodes = kwargs.get('parent_nodes', [])
    attr_id = []
    for n in parent_nodes:
        if 'id' in n.attrib:
            attr_id.append(f'<h4>{n.attrib["id"]}</h4>')
    return ''.join(attr_id)


def check_contain_attr(node_attr: str, attrs: List) -> bool:
    '''
    <div class="highlight-python3">
    
    result = check_contain_attr(child.attrib['class'], ['highlight-python3', 'highlight-pycon')
    print(result) # True
    '''
    for attr in attrs:
        if attr in node_attr:
            return True
    return False



def child_recursive(node: ET.Element, parent_node_data: List, callback: Callable):
     
    simple_text_children, complex_element_children = [], []

    for child in node:
        # Group elements that are simple text together
        if child.tag in ['span', 'p', 'ul', 'ol', 'dt', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            simple_text_children.append(child)  
        
        # These elements will just stay as its, do not recursively go into them
        elif child.attrib and 'class' in child.attrib and check_contain_attr(child.attrib['class'], ['highlight-python3', 'highlight-pycon', 'doctest', 'describe', 'py method', 'py attribute', 'responsive-table__container', 'admonition']):
            complex_element_children.append(child)
    
    # Remowe the processed children to add a wrapper div for each
    for child in simple_text_children + complex_element_children:
        node.remove(child)

    # Recursively go into each child
    for child in node:
        child_recursive(child, parent_node_data + [child], callback)

    # Group all simple text elements together, callback will process only that wrapper div, but also have all parents nodes
    group_div = ET.Element('div')
    group_div.attrib['class'] = 'custom-group'
    group_div.extend(simple_text_children)
    callback(group_div, parent_nodes=parent_node_data + [node])
    node.insert(0, group_div)
    

    for child in complex_element_children:
        group_div = ET.Element('div')
        group_div.attrib['class'] = 'custom-group'
        group_div.append(child)
        callback(group_div, parent_nodes=parent_node_data + [node])
        node.append(group_div)
        



def node_to_anki(questions: List[str], answers: List[str], table_of_contents: List[str]):
    filename = 'Python Docs'
    css = open('pydoctheme.css').read()
    front_html =  '''
<!-- HACK: Dynamically load JavaScript files, as Anki does not support static load -->
<script>
var script2 = document.createElement('script');
script2.src = 'handlePyDocs.js';
script2.async = false;
document.head.appendChild(script2);
document.head.removeChild(script2);

setTimeout(() => update(0.8), 50);
</script>

<div class="front">
  {{TableOfContent}}

  <input id="prob-sidebar" type="range" min="0" max="1" step="0.005" value="0.8" style="width: 100%;">
  <span id="prob-value"></span>
  <input id="seed-sidebar" type="range" min="0" max="1" step="0.05" value="0.5" style="width: 100%;">
  <span id="seed-value"></span>

  <!-- Question will be dynamically loaded by update() -->
  <div class="question" style="display:none"></div>

  <!-- Clone the original question data, as each update() will modify and hide some text in <div question> -->
  <div class="question-clone" style="display:none">
    {{Question}}
  </div>
</div>
'''
    back_html = '''
<div class="back">
  {{TableOfContent}}
  {{Answer}}
  {{Media}}
</div>
'''
    my_model = MyModel(filename, css=css, front_html=front_html, back_html=back_html, fields=[{'name': 'Question'}, {'name': 'Answer'}, {'name': 'Media'}, {'name': 'TableOfContent'}])

    my_deck = genanki.Deck(deck_id=abs(hash(filename)) % (10 ** 10), name=filename)

    for i, q in enumerate(questions):
        # HACK: Force import JavaScript file as image media on each card, so Anki will actually import it to collection
        media = '<img src="seedrandom.js" style="display:none"><img src="handlePyDocs.js" style="display:none">'
        anki_note = genanki.Note(model=my_model, fields=[q, answers[i], media, table_of_contents[i]], tags=['python-docs'])
        my_deck.add_note(anki_note)

    anki_output = genanki.Package(my_deck)
    anki_output.media_files = ['seedrandom.js', 'handlePyDocs.js']
    anki_output.write_to_file(filename+'.apkg')
    
    

if __name__ == '__main__':
    tree = ET.parse('tmp.html')

    out_question, out_answer, out_table_of_content = [], [], []
    def callback(node, **kwargs):
        # draw_boundary(node, **kwargs)

        string_io = io.BytesIO()
        ET.ElementTree(node).write(string_io, encoding='utf-8')
        out_answer.append(string_io.getvalue().decode('utf-8'))
        string_io.close()
    
        content = get_parent_hierarchy(node, **kwargs)
        out_table_of_content.append(content)
        
    
    child_recursive(tree.getroot(), [], callback)

    node_to_anki(out_answer, out_answer, out_table_of_content)
    
    tree.write('out.html', encoding='utf-8')


