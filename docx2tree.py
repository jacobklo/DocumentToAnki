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
  def __init__(self, level: int, image_name: str, image_index: int, show_on_children_level: int, context: List[Paragraph], parent: Node):
    super(PhotoNode, self).__init__(level, context, parent)
    self.imageName = image_name
    self.imageIndex = image_index
    self.showOnChildrenLevel = show_on_children_level

  def __repr__(self):
    results = '- ' * self.level
    if self.imageName:
      results += self.imageName + "ShowOnChildren : " + self.showOnChildrenLevel + os.linesep
    for c in self.children:
      results += repr(c)
    return results


def get_image_index(package: OpcPackage, imageName: str) -> int:
  document = package.main_document_part.document
  for i in range(len(document.paragraphs)):
    if i >= len(package.image_parts._image_parts):
      raise Exception('The Save function from Microsoft Word create a different image name for each image, please use Google Docs and export as .docx file only')
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
  """
  Convert a docx file package into internal Node tree structure
  
  Support features:
  1) Each line in Document is converted into a Node
  2) Combine multiple lines into 1 Node with "©©"
  3) Identify photos with "®®"

  Input: OpcPackage, which is the file structure of a docx file
  You can get a OpcPackage by following:
  
  f = open('Document.docx', 'rb')
  package = Package.open(f)
  f.close()

  
  Node parent/children structure is based on Headings in Document

  Example.docx contains:
  Heading1
  - word1
  - Heading2
  -- word2

  Node root => Heading1
  root.children[1] => word1
  root.children[2] => Heading2
  root.children[2].children[1] => word2
  """
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

    # ©©8 means combine the next 8 lines inside Document into only 1 text node, so only 1 Anki Note is created
    if paragraphs[i].text[0:2] == '©©' and paragraphs[i].text[2].isnumeric():
      group_paragraphs = paragraphs[i:i+int(paragraphs[i].text[2])+1]
      new_node = Node(cur_parent.level+1, group_paragraphs, cur_parent)
      cur_parent.add(new_node)
      i += int(paragraphs[i].text[2]) + 1
      continue
    
    # ®®1 means the very next line is a pics, and this pics is going to show on every notes created from each line of this heading level in this document
    # For example:
    # Heading 1
    # texttext1
    # ®®2
    # image1.png
    # - Heading 2
    # - texttext2
    # In this example, 2 Anki Notes is created, texttext1 and texttext2. Each note has image1.png in it.
    if paragraphs[i].text[0:2] == '®®' and paragraphs[i].text[2].isnumeric():
      imageInfo = [paragraphs[i]]
      show_on_children_level = int(paragraphs[i].text[2])
      i += 1
      image_name = get_image_name(paragraphs[i])
      image_index = get_image_index(package, image_name)
      new_node = PhotoNode(cur_parent.level+1, image_name, image_index, show_on_children_level, imageInfo, cur_parent)
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
