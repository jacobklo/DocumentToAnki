from __future__ import annotations
from typing import List, Set
import os
import re
from docx.text.paragraph import Paragraph

class Node:
  def __init__(self, parent: Node, context: List[Paragraph] ):
    self.context = context
    self.parent = parent
    self.level = 0 if parent is None else parent.level+1
    self.children = []
  

  def add(self, node: Node):
    self.children.append(node)
  

  def is_normal(self):
    return self.context is not None and len(self.context) > 0 and self.context[0].style.name.split()[0].lower() == 'normal'


  def __repr__(self):
    """
    Show the content of this node

    This node represent a sentence in the docx document.
    It is called a paragraph in python-docx.

    It will only show first 20 characters of that sentence.

    Example:

    In Example.docx:
    ```
    Title
    One sentence will result in 1 Anki note.
    ```

    repr(root)
    >>> UNKNOWN NODE
    repr(paragraph1)
    >>> Title
    repr(paragraph2)
    >>> One sentence will re

    """

    if self.context and isinstance(self.context, List):
      return self.context[0].text[0:20]
    return 'UNKNOWN NODE'


  @staticmethod
  def repr(node: Node):
    """
    Show all content in this node, and all children nodes recursively

    Example:
    repr(root)
    >>> UNKNOWN NODE
    - One sentence will re
    - This is shown in Ank
    - Heading1
    - - ©©2 List in 1 Anki's
    - - image2.png  ShowOnChildren : 0
    - - Heading2
    - - - There is a tree stru
    - - - Tree structure group
    - - - image1.png  ShowOnChildren : 1
    """

    results = '- ' * node.level + repr(node) + os.linesep
    for c in node.children:
      results += Node.repr(c)
    return results


  def get_tags(self) -> List[str]:
    if not self.parent or len(self.context) <= 0: return Set()
    node = self.parent
    results = []
    while node:
      if (len(node.context) > 0):
        tag = re.sub('[^A-Z]+', '_', node.context[0].text, 0, re.I).lower()
        results += [tag]
      node = node.parent
    return results


  def get_branch_str(self) -> str:
    node = self.parent
    print(self)
    result = '- ' #* node.level + node.context[0].text
    while node.parent:
      node = node.parent
      if len(node.context) > 0:
        result = '- ' * node.level + node.context[0].text + os.linesep + result
      else:
        result = 'root ' + os.linesep + result
    return result.replace(os.linesep, '<br>').replace('\t', '&ensp;')
  

  def convert_paragraph_to_html(self, paragraph: Paragraph, hide_bold: bool) -> str:
    result = ''
    if not self.is_normal() or not paragraph.text.replace(' ', ''):
      return ''
    for r in paragraph.runs:
      if r.bold:
        result += '<b>' + ('_' * len(r.text) if hide_bold else r.text) + '</b>'
      elif r.italic:
        result += '<i>' + ('_' * len(r.text) if hide_bold else r.text) + '</i>'
      else:
        result += r.text
    return result.replace(os.linesep, '<br>').replace('\t', '&ensp;')


class PhotoNode(Node):
  def __init__(self, parent: Node, image_name: str, image_index: int, show_on_children_level: int, context: List[Paragraph]):
    super(PhotoNode, self).__init__(parent, context)
    self.imageName = image_name
    self.imageIndex = image_index
    self.showOnChildrenLevel = show_on_children_level

  def __repr__(self):
    if self.imageName:
      return self.imageName + "  ShowOnChildren : " + str(self.showOnChildrenLevel)
    return ''
