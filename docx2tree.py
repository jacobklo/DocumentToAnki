from __future__ import annotations
import os
import io
import shutil
import re
from typing import List
from PIL import Image

from docx.text.paragraph import Paragraph
from docx.package import OpcPackage

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


  def convert_to_anki_note_field(self) -> List[str, str, str, str]:
    if not self.is_normal() or not self.context or not isinstance(self.context, List):
      return None
    question, answer = '', ''
    for p in self.context:
      question += self.convert_paragraph_to_html(p, True) + '<br>'
      answer += self.convert_paragraph_to_html(p, False) + '<br>'
    return [question, answer, '', self.get_branch_str()]


class PhotoNode(Node):
  def __init__(self, level: int, image_name: str, image_index: int, parent: Node):
    super(PhotoNode, self).__init__(level, [], parent)
    self.imageName = image_name
    self.imageIndex = image_index
  
  def convert_to_anki_note_field(self) -> List[str, str, str, str]:
    question, answer = ' ', ' '
    media = '<img src="' + self.imageName + '">'
    return [question, answer, media, self.get_branch_str()]

  def __repr__(self):
    results = '- ' * self.level
    if self.imageName:
      results += self.imageName + os.linesep
    for c in self.children:
      results += repr(c)
    return results


def get_image_index(package: OpcPackage, imageName: str) -> int:
  document = package.main_document_part.document
  for i in range(len(document.paragraphs)):
    if imageName in package.image_parts._image_parts[i].partname:
      return i
  return -1


def get_image_name(paragraph: Paragraph ):
  if not paragraph.runs:
    return ""
  cur_xml = paragraph.runs[0].element.xml
  regex_match = re.search("image[0-9]*.png", cur_xml)
  if regex_match:
    return regex_match.group(0)
  return ""


def convert_paragraphs_to_tree(package: OpcPackage) -> Node:
  # reset image directory first
  shutil.rmtree('image', ignore_errors=True)
  os.mkdir('image')
  
  paragraphs = package.main_document_part.document.paragraphs
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
      
    if paragraphs[i].text[0:2] == '®®' and paragraphs[i].text[2].isnumeric():
      i += 1
      image_name = get_image_name(paragraphs[i])
      image_index = get_image_index(package, image_name)
      new_node = PhotoNode(cur_parent.level+1, image_name, image_index, cur_parent)
      cur_parent.add(new_node)

      img_binary = package.image_parts._image_parts[image_index].blob
      image = Image.open(io.BytesIO(img_binary))
      image.save('image/'+image_name)

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
