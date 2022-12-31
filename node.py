from __future__ import annotations
from typing import List, Set
import os, re
from docx.text.paragraph import Paragraph

class Node:
  def __init__(self, parent: Node, context: List[Paragraph] ):
    self.context = context
    self.parent = parent
    self.level = 0 if parent is None else parent.level+1
    self.children = []

  def add(self, node: Node):
    self.children.append(node)

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
    Node.repr(root)
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

  def getBranchStr(self) -> str:
    """
    Return all the heading nodes as a string. From this node up to root Node.

    Example:
    Node.getBranchStr(grandChildrenNode)
    @return root\n
    -Heading1\n
    --Heading2
    """
    node = self
    result = ''
    while node.parent:
      node = node.parent
      if len(node.context) > 0:
        result = '- ' * node.level + node.context[0].text + os.linesep + result
      else:
        result = 'root ' + os.linesep + result
    return result


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
