from __future__ import annotations
import os
from typing import List

from docx import Document
from docx.text.paragraph import Paragraph


class Node:
  def __init__(self, level: int, context: Paragraph, parent: Node):
    self.level = level
    self.context = context
    self.parent = parent
    self.children = []
  
  def add(self, node: Node):
    self.children.append(node)

  def __repr__(self):
    results = '- ' * self.level
    if self.context:
      results += self.context.text + os.linesep
    for c in self.children:
      results += repr(c)
    return results

  def get_branch_str(self):
    node = self
    result = '- ' * node.level + node.context.text
    while node.parent:
      node = node.parent
      result = '- ' * node.level + node.context.text + os.linesep + result
    return result
  
  def convert_paragraph_to_html(self, hide_bold: bool):
    result = ''
    for r in self.context.runs:
      if r.bold:
        result += '<b>' + ('_' * len(r.text) if hide_bold else r.text) + '</b>'
      elif r.italic:
        result += '<i>' + ('_' * len(r.text) if hide_bold else r.text) + '</i>'
      else:
        result += r.text
    return result

  def convert_to_anki_note(self):
    if (self.context.style.name.split()[0].lower() != 'normal'):
      return []
    if ':' in self.context.text:
      question = self.context.runs[0].text.split(':',1)[0] + ':'
    else:
      question = self.convert_paragraph_to_html_hide_bold(True)
    answer = self.convert_paragraph_to_html(False)
    return [question, answer]


def convert_paragraphs_to_tree(paragraphs: List[Paragraph]):
  root = Node(0, paragraphs[0], None)
  cur_parent = root
  cur_heading_level = 0

  for p in paragraphs:
    p_style = p.style.name.split()

    # normal paragraph, treat as same level as current level
    if p_style[0] == 'normal':
      new_node = Node(cur_parent.level+1, p, cur_parent)
      cur_parent.add(new_node)
    
    # new paragraph has lower(bigger) heading, so move parent node must be higher up, closer to root
    if p_style[0] == 'Heading' and int(p_style[1]) <= cur_heading_level:
      for _ in range(int(p_style[1]), cur_heading_level + 1):
        cur_parent = cur_parent.parent
    
    # This should go in either bigger heading, or smaller heading ( child node ). New node is created under current parent
    if p_style[0] == 'Heading':
      new_node = Node(cur_parent.level+1, p, cur_parent)
      cur_parent.add(new_node)
      cur_parent = new_node
      cur_heading_level = int(p_style[1])
  
  return root
