
import xml.etree.ElementTree as ET
from typing import List, Callable
import io

from myanki import MyModel

import genanki


def get_parent_hierarchy(node: ET.Element, **kwargs) -> List[str]:
    '''
    For each parent node, get the id attribute and return as a string
    '''
    parent_nodes = kwargs.get('parent_nodes', [])
    attrs = []
    for n in parent_nodes:
        if 'id' in n.attrib and n.attrib["id"] not in attrs:
            attrs.append(n.attrib["id"])
    return attrs


def check_contain_attr(node_attr: str, attrs: List) -> bool:
    '''
    <div class="highlight-python3">
    
    result = check_contain_attr(child.attrib['class'], ['highlight-python3', 'highlight-pycon')
    print(result) # True
    '''
    return any(attr in node_attr for attr in attrs)



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
        



def node_to_anki(answers: List[str], table_of_contents: List[List[str]]):
    filename = 'PythonDocs'
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

    decks = {}
    for t in table_of_contents:
        deck_name = f'{filename}::{"::".join(t)}'
        decks[deck_name] = genanki.Deck(deck_id=abs(hash(deck_name)) % (10 ** 10), name=deck_name)

    for i, ans in enumerate(answers):
        # HACK: Force import JavaScript file as image media on each card, so Anki will actually import it to collection
        media = '<img src="seedrandom.js" style="display:none"><img src="handlePyDocs.js" style="display:none">'
        table_of_content_html = ''.join([f'<h4>{t}</h4>' for t in table_of_contents[i]])
        anki_note = genanki.Note(model=my_model, fields=[ans, answers[i], media, table_of_content_html], tags=['python-docs'])
        deck_name = f'{filename}::{"::".join(table_of_contents[i])}'
        decks[deck_name].add_note(anki_note)

    anki_output = genanki.Package(list(decks.values()))
    anki_output.media_files = ['seedrandom.js', 'handlePyDocs.js']
    anki_output.write_to_file(filename+'.apkg')
    
    

def find_substring(phrase: str, substring: str):
    index = phrase.find(substring)
    return phrase[index:] if index != -1 else None


def find_last_substring(phrase, substring):
    index = phrase.rfind(substring)
    return phrase[:index+len(substring)] if index != -1 else None


if __name__ == '__main__':
    with open('tmp.html', 'r', encoding='utf-8') as f:
        html_str = f.read()

        # Remove all the header and footer, only keep the main section
        html_str = find_substring(html_str, '<section ')
        html_str = find_last_substring(html_str, '</section>')

        with open('out.html', 'w', encoding='utf-8') as f:
            f.write(html_str)

    # tree = ET.parse('tmp.html')

    # answers: List[str] = []
    # table_of_contents: List[List[str]] = []
    # def callback(node, **kwargs):
    #     # draw_boundary(node, **kwargs)

    #     string_io = io.BytesIO()
    #     ET.ElementTree(node).write(string_io, encoding='utf-8')
    #     answers.append(string_io.getvalue().decode('utf-8'))
    #     string_io.close()
    
    #     content = get_parent_hierarchy(node, **kwargs)
    #     table_of_contents.append(content)
        
    
    # child_recursive(tree.getroot(), [], callback)

    # node_to_anki(answers, table_of_contents)
    
    # tree.write('out.html', encoding='utf-8')


