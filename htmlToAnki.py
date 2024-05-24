import copy
import xml.etree.ElementTree as ET
from typing import List, Callable
from html.parser import HTMLParser
import io, html

from myanki import MyModel

import genanki


class HTMLToText(HTMLParser):
  def __init__(self):
    super().__init__()
    self.text = []
    
  def handle_data(self, data):
    self.text.append(data)
  
  def handle_starttag(self, tag, attrs):
    if tag in {'br', 'p', 'div'}:
      self.text.append('\n')
  
  def handle_endtag(self, tag):
    if tag in {'p', 'div'}:
      self.text.append('\n')
  
  def get_text(self):
    return ''.join(self.text).strip()




def node_str(node):
    return f'{node.tag} {node.attrib} Children: {len(node)} {[n.tag for n in node]}\n'


def convert_html_to_text(node: ET.Element) -> str:
    parser = HTMLToText()
    string_io = io.BytesIO()
    ET.ElementTree(node).write(string_io, encoding='utf-8')
    html_str = string_io.getvalue().decode('utf-8')
    parser.feed(html_str)
    string_io.close()
    return html.unescape(parser.get_text())


def draw_boundary(node: ET.Element, **kwargs):
    '''
    Draw a red border around the node
    '''
    node.attrib['style'] = 'border-style: dotted; border-width: 5px; border-color: red;'
    

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



def remove_text_children(node: ET.Element) -> ET.Element:
    '''
    Remove all text children from the node
    '''
    out_node = copy.copy(node)
    for child in out_node:
        if child.tag in ['span', 'p', 'dd', 'div']:
            out_node.remove(child)
    return out_node


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

<script>
if (typeof hljs === "undefined") {
    var script = document.createElement('script');
    script.src = "_highlight.min.js";
    script.async = false;
    document.head.appendChild(script);
}

var script = document.createElement('script');
script.src = 'https://cdnjs.cloudflare.com/ajax/libs/seedrandom/3.0.5/seedrandom.min.js';
script.async = false;
document.head.appendChild(script);
document.head.removeChild(script);



function hideSomeText(node, prob, random_gen_func) { 
  
  node.childNodes.forEach(n => {
    
    if (n.nodeType === Node.TEXT_NODE) {
      let words = n.textContent.split(/\s+/);
      for (let i = 0; i < words.length; i++) {
        if (random_gen_func() > prob) {
          if (words[i].length > 0) {
            words[i] = words[i][0] + '_'.repeat(words[i].length - 1);
          }
        }
      }
      n.textContent = words.join(' ');
    } 
    
    else if (n.nodeType === Node.ELEMENT_NODE) {
      hideSomeText(n, prob, random_gen_func)
    }
  });

}


function update(prob) {
  let random_gen_func = new Math.seedrandom('hello.');

  let div = document.querySelector('.question');
  let clone2 = document.querySelector('.question-clone');

  div.innerHTML = clone2.innerHTML;
  hideSomeText(div, prob, random_gen_func);
  
  div.style.display = 'none';
  div.style.display = 'block';

  document.getElementById('sidebar-value').textContent = prob;
}

document.getElementById('prob-sidebar').addEventListener('input', function(event) {
  update(event.target.value);
});

setTimeout(() => {
  update(0.5);
}, 100);

</script>


<div class="front">
  {{TableOfContent}}
  <br>
  <input id="prob-sidebar" type="range" min="0" max="1" step="0.005" value="0.5" style="width: 100%;">
  <span id="sidebar-value"></span>
  <div class="question" style="display:none">
    {{Question}}
  </div>
  <div class="question-clone" style="display:none">
    {{Question}}
  </div>
</div>
'''
    my_model = MyModel(filename, css=css, front_html=front_html, fields=[{'name': 'Question'}, {'name': 'Answer'}, {'name': 'Media'}, {'name': 'TableOfContent'}])

    my_deck = genanki.Deck(deck_id=abs(hash(filename)) % (10 ** 10), name=filename)

    for i, q in enumerate(questions):
        
        anki_note = genanki.Note(model=my_model, fields=[q, answers[i], '', table_of_contents[i]], tags=['python-docs'])
        my_deck.add_note(anki_note)

    anki_output = genanki.Package(my_deck)
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


