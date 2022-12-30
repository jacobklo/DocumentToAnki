
import os
import io
import shutil
import re
import warnings

from PIL import Image

from docx.text.paragraph import Paragraph
from docx.package import Package, OpcPackage

from node import Node, PhotoNode


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
  regex_match = re.search("image[0-9]*.[a-zA-Z]+", cur_xml)
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
  root = Node(0, [], None)
  cur_parent = root
  cur_heading_level = 0

  # for loop does not work, https://stackoverflow.com/a/47532461
  i = 0
  while(i < len(paragraphs)):
    p_style = paragraphs[i].style.name.split()

    # ©©8 means combine the next 8 lines inside Document into only 1 text node, so only 1 Anki Note is created
    if paragraphs[i].text[0:2] == '©©' and paragraphs[i].text[2].isnumeric():
      howManyLinesToSkip = int(paragraphs[i].text.split()[0].replace('©©', ''))
      group_paragraphs = paragraphs[i:i+howManyLinesToSkip+1]
      new_node = Node(cur_parent.level+1, group_paragraphs, cur_parent)
      cur_parent.add(new_node)
      i += howManyLinesToSkip + 1
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
      if not image_name:
        warnings.warn("Cannot process image : " + imageInfo[0].text)
        continue

      image_index = get_image_index(package, image_name)
      new_node = PhotoNode(cur_parent.level+1, image_name, image_index, show_on_children_level, imageInfo, cur_parent)
      cur_parent.add(new_node)

      img_binary = package.image_parts._image_parts[image_index].blob
      image = Image.open(io.BytesIO(img_binary))
      image.save('image/'+image_name)

    # normal paragraph, treat as same level as current level, check if this line is not empty
    if p_style[0].lower() == 'normal' and paragraphs[i].text.replace(' ','').replace('\n',''):
      new_node = Node(cur_parent.level+1, [paragraphs[i]], cur_parent)
      cur_parent.add(new_node)

    # If the heading line is actually empty, then skip to next one
    if not paragraphs[i].text.replace(' ', '').replace('\t', '').replace('\n', ''):
      i += 1
      continue
    
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

if __name__ == "__main__":
  f = open('Microsoft Word Documents to Anki converter demo.docx', 'rb')
  pp = Package.open(f)
  f.close()

  root = convert_paragraphs_to_tree(pp)
  print(Node.repr(root))
