from __future__ import annotations
import os
import io
import shutil
import re
import warnings

from typing import List

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
  
  paragraphs = DocxToNode.getAllParagraphs(package)
  root = Node(0, [], None)
  curParent = root
  cur_heading_level = 0

  # for loop does not work, https://stackoverflow.com/a/47532461
  i = 0
  while(i < len(paragraphs)):
    p_style = DocxToNode.getParagraphStyle(paragraphs[i]).split()
    
    if p_style[0] != 'heading':
      newNode = None
      if DocxToNode.lengthOfBulletList(paragraphs[i]) > 0:
        howManyLinesToSkip = DocxToNode.lengthOfBulletList(paragraphs[i])
        group_paragraphs = paragraphs[i:i+howManyLinesToSkip+1]
        newNode = Node(curParent.level+1, group_paragraphs, curParent)
        curParent.add(newNode)
        i += howManyLinesToSkip + 1
        continue
      
      elif DocxToNode.isPicture(paragraphs[i]):
        newNode = DocxToNode.createPhotoNote(paragraphs[i], paragraphs[i+1], package, curParent)
        curParent.add(newNode)
        # increment i here 1 more than normal, because a PhotoNode paragraph takes 2 paragraphs
        i += 1

      # normal paragraph, treat as same level as current level, check if this line is not empty
      elif DocxToNode.isNormalParagraph(paragraphs[i]) and not DocxToNode.isEmptyParagraph(paragraphs[i]):
        newNode = Node(curParent.level+1, [paragraphs[i]], curParent)
        curParent.add(newNode)

      # If the heading line is actually empty, then skip to next one
      else:#if DocxToNode.isEmptyParagraph(paragraphs[i]):
        i += 1
        continue
    
    elif p_style[0] == 'heading':
    
      # new paragraph has lower(bigger) heading, so move parent node must be higher up, closer to root
      if int(p_style[1]) <= cur_heading_level:
        for _ in range(int(p_style[1]), cur_heading_level + 1):
          curParent = curParent.parent
      
      # This should go in either bigger heading, or smaller heading ( child node ).
      # New node is created under current parent
      new_node = Node(curParent.level+1, [paragraphs[i]], curParent)
      curParent.add(new_node)
      curParent = new_node
      cur_heading_level = int(p_style[1])
    
    i += 1
  
  return root

class DocxToNode:
  
  @staticmethod
  def getAllParagraphs(docx_package: OpcPackage) -> List[Paragraph]:
    """
    Convert from python-docx->Package into list of sentences ( python-docx called paragraph )

    Docx documents is stored in XML format.
    Paragraph is basically infos inside <w:p> tags

    ```xml
    <w:p>
      ...
				<w:pStyle w:val="Title"/>
			...
		</w:p>
		<w:p>
			...
				<w:t xml:space="preserve">One sentence will result in </w:t>
			...
				<w:t xml:space="preserve">1</w:t>
			...
				<w:t xml:space="preserve"> Anki note.</w:t>
			...
		</w:p>
    ...
    ```

    You can open a docx document, by 
    1) convert .docx to .zip, and unzip
    2) open document.xwl in text editor

    """
    return docx_package.main_document_part.document.paragraphs
  
  @staticmethod
  def getParagraphStyle(para: Paragraph) -> str:
    """
    This return what this sentence ( paragraph )'s hierarchy

    Example:
    title
    heading 1
    heading 2
    normal

    """
    return para.style.name.lower()
  
  @staticmethod
  def isEmptyParagraph(para: Paragraph) -> bool:
    """
    Check for empty sentence ( paragraph ) in docx file
    """
    return not para.text.replace(' ', '').replace('\t', '').replace('\n', '')
  
  @classmethod
  def isNormalParagraph(cls, para: Paragraph) -> bool:
    """
    Check if this sentence ( paragraph ) is normal, not a heading
    """
    return cls.getParagraphStyle(para) == 'normal'

  @staticmethod
  def lengthOfBulletList(para: Paragraph) -> int:
    """
    Check if User want to group multiple paragraphs into 1 Node.

    ©©8 means combine the next 8 lines inside Document into only 1 text node,
     so only 1 Anki Note is created

    Example:
    ```text
    ©©2 List in 1 Anki’s note:
      1) ©©2 means the next 2 lines to be included in 1 note
      2) So this line will be included too
    ```
    All of these will show in 1 Anki note only
    
    """
    if para.text[0:2] == '©©' and para.text[2].isnumeric():
      # return number of lines this list has, indicate after ©©
      return int(para.text.split()[0].replace('©©', ''))
    return -1
  
  @staticmethod
  def isPicture(para: Paragraph) -> bool:
    """
    We define a ®®0 paragraph, the next one is a picture

    There are currently no way to detect a picture in a paragraph automatically.
    So, User must specify ®® on the previous line/paragraph inside the docx document
    
    Also, the digit means do you want to show the picture in 1 Anki note, or multeple

    ®®0 means treat the picture as 1 note
    ®®1 means the very next line is a pics, and this pics is going to show on every notes \
      created from each line of this heading level in this document
    
    For example:
    Heading 1
    texttext1
    ®®2
    image1.png
    - Heading 2
    - texttext2
    In this example, 2 Anki Notes is created, texttext1 and texttext2. 
    Each note has image1.png in it.

    """
    return para.text[0:2] == '®®' and para.text[2].isnumeric()
  
  @staticmethod
  def createPhotoNote(paraRR: Paragraph, nextPara: Paragraph, package: OpcPackage, curParent: Node) -> PhotoNode:
    """
    Create a PhotoNode, based on 2 paragraphs
    
    We define a ®®0 paragraph, the next one is a picture.

    Check the docstring on isPicture()

    show_on_children_level: 0 means only show this pic on 1 Anki Note
    , 1 means shows on this level's notes
    , 2 means this level and next children,s level
    """
    imageInfo = [paraRR]
    show_on_children_level = int(paraRR.text[2])

    image_name = get_image_name(nextPara)
    if not image_name:
      warnings.warn("Cannot process image : " + imageInfo[0].text)
      return None

    image_index = get_image_index(package, image_name)

    img_binary = package.image_parts._image_parts[image_index].blob
    image = Image.open(io.BytesIO(img_binary))
    image.save('image/'+image_name)

    return PhotoNode(curParent.level+1, image_name, image_index, show_on_children_level, imageInfo, curParent)




if __name__ == "__main__":
  f = open('Microsoft Word Documents to Anki converter demo.docx', 'rb')
  pp = Package.open(f)
  f.close()

  root = convert_paragraphs_to_tree(pp)
  print(Node.repr(root))
