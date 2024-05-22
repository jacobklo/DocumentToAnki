import xml.etree.ElementTree as ET


def node_str(node, depth):
    return f'  {" " * depth}  {node.tag} {node.attrib}\n'


def node_str2(node, depth):
    if node.tag == 'section':
        return f'{node.tag} {node.attrib} Children: {len(node)} {[n.tag for n in node]}\n'
    return ''


def check_contain_attr(node_attr_str, list_of_attr) -> bool:
    for attr in list_of_attr:
        if attr in node_attr_str:
            return True
    return False

def child_recursive(node: ET.Element, depth: int, callback) -> str:
    result = ''        
    
    if node.tag == 'section' and 'id' in node.attrib and node.attrib['id'] == 'built-in-types':
        print("built-in-types found")

    simple_text_children, complex_element_children = [], []
    for child in node:
        if child.tag in ['span', 'p', 'ul', 'ol', 'dt', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            simple_text_children.append(child)
        elif child.attrib and 'class' in child.attrib and check_contain_attr(child.attrib['class'], ['highlight-python3', 'highlight-pycon', 'doctest', 'describe', 'py method', 'py attribute', 'responsive-table__container', 'admonition']):
            complex_element_children.append(child)
    
    for child in simple_text_children + complex_element_children:
        node.remove(child)

    result += callback(node, depth)
      
    for child in node:
        result += child_recursive(child, depth + 1, callback)
    
    red_box_div = ET.Element('div')
    red_box_div.attrib['style'] = 'border-style: dashed; border-width: 5px; border-color: red;'
    red_box_div.extend(simple_text_children)
    node.insert(0, red_box_div)

    for child in complex_element_children:
        blue_box_div = ET.Element('div')
        blue_box_div.attrib['style'] = 'border-style: dashed; border-width: 5px; border-color: blue;'
        blue_box_div.append(child)
        node.append(blue_box_div)
    
    return result


if __name__ == '__main__':
    tree = ET.parse('tmp.html')

    out = child_recursive(tree.getroot(), 0, node_str2)

    with open('out.txt', 'w', encoding='utf-8') as f:
        f.write(out)
    
    tree.write('out.html', encoding='utf-8')


