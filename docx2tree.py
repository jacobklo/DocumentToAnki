from __future__ import annotations
import os
from typing import List

from docx.text.paragraph import Paragraph


class Node:
  def __init__(self, level: int, context: List[Paragraph], parent: Node):
    self.level = level
    self.context = context
    self.parent = parent
    self.children = []
  

  def add(self, node: Node):
    self.children.append(node)
  

  def is_normal(self):
    return self.context and self.context[0] and self.context[0].style.name.split()[0].lower() == 'normal'


  def __repr__(self):
    results = '- ' * self.level
    if self.context and isinstance(self.context, List):
      results += self.context[0].text
      for i in range(1,len(self.context)):
        results += os.linesep + '- ' * self.level + '\t\t' + self.context[i].text
      results += os.linesep
    for c in self.children:
      results += repr(c)
    return results


  def get_branch_str(self) -> str:
    node = self.parent
    result = '- ' * node.level + node.context[0].text
    while node.parent:
      node = node.parent
      result = '- ' * node.level + node.context[0].text + os.linesep + result
    return result.replace(os.linesep, '<br>').replace('\t', '&ensp;')
  

  def convert_paragraph_to_html(self, paragraph: Paragraph, hide_bold: bool) -> str:
    result = ''
    for r in paragraph.runs:
      if r.bold:
        result += '<b>' + ('_' * len(r.text) if hide_bold else r.text) + '</b>'
      elif r.italic:
        result += '<i>' + ('_' * len(r.text) if hide_bold else r.text) + '</i>'
      else:
        result += r.text
    return result.replace(os.linesep, '<br>').replace('\t', '&ensp;')


  def convert_to_anki_note_field(self) -> List[str, str, str]:
    if not self.is_normal() or not self.context or not isinstance(self.context, List):
      return ['','','']
    question, answer = '', ''
    for p in self.context:
      question += self.convert_paragraph_to_html(p, True) + '<br>'
      answer += self.convert_paragraph_to_html(p, False) + '<br>'
    return [question, answer, self.get_branch_str()]


def convert_paragraphs_to_tree(paragraphs: List[Paragraph]) -> Node:
  root = Node(0, [paragraphs[0]], None)
  cur_parent = root
  cur_heading_level = 0

  # for loop does not work, https://stackoverflow.com/a/47532461
  i = 0
  while(i < len(paragraphs)):
    p_style = paragraphs[i].style.name.split()

    # Special
    if paragraphs[i].text[0:2] == '©©' and paragraphs[i].text[2].isnumeric():
      group_paragraphs = paragraphs[i:i+int(paragraphs[i].text[2])+1]
      new_node = Node(cur_parent.level+1, group_paragraphs, cur_parent)
      cur_parent.add(new_node)
      i += int(paragraphs[i].text[2]) + 1
      continue

    # normal paragraph, treat as same level as current level
    if p_style[0].lower() == 'normal':
      new_node = Node(cur_parent.level+1, [paragraphs[i]], cur_parent)
      cur_parent.add(new_node)
    
    # new paragraph has lower(bigger) heading, so move parent node must be higher up, closer to root
    if p_style[0].lower() == 'heading' and int(p_style[1]) <= cur_heading_level:
      for _ in range(int(p_style[1]), cur_heading_level + 1):
        cur_parent = cur_parent.parent
    
    # This should go in either bigger heading, or smaller heading ( child node ). New node is created under current parent
    if p_style[0].lower() == 'heading':
      new_node = Node(cur_parent.level+1, [paragraphs[i]], cur_parent)
      cur_parent.add(new_node)
      cur_parent = new_node
      cur_heading_level = int(p_style[1])
    
    i += 1
  
  return root
