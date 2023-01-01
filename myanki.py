from __future__ import annotations
import genanki
import hashlib, os
from pathlib import Path
from typing import List, Tuple, Dict

from docx.package import Package, OpcPackage
from docx.text.paragraph import Paragraph
from docx.table import Table

from docx2tree import Node, PhotoNode, DocxToNode
from docx2tree import convertParagraphsToTree


def docxToAnkiNotes(filename: str):
  f = open(filename+'.docx', 'rb')
  pp = Package.open(f)
  f.close()

  root = convertParagraphsToTree(pp)

  my_model = MyModel(filename+' Model', fields=[{'name': 'Question'}, {'name': 'Answer'}, {
      'name': 'Media'}, {'name': 'TableOfContent'}])

  notes = NodeToAnki.createAnkiNotes(root, my_model, pp)

  my_deck = genanki.Deck(deck_id=abs(hash(filename)) % (10 ** 10), name=filename)

  for n in notes:
    my_deck.add_note(n)

  img_path = Path(r'image').glob('**/*')
  images = ['image/'+x.name for x in img_path if x.is_file()]

  anki_output = genanki.Package(my_deck)
  anki_output.media_files = images
  anki_output.write_to_file(filename+'.apkg')


class MyModel(genanki.Model):
  """
  Customize how all Anki Notes will look like in this Anki Model.

  Also, create a hash for this Model, for Anki app to track future Notes update.
  """
  DefaultFrontTemplate = '''
  <div class="front">{{Path}}<br><br>{{Question}}</div>
  '''

  DefaultBackTemplate = '''
  <div class="back">
  <table style="width:100%">
    <tr>
      <th>{{TableOfContent}}</th>
    </tr>
    <tr>
      <th>{{Answer}}</th>
    </tr>
    <tr>
      <th>{{Media}}</th>
    </tr>
  </table>
  </div>

  </div>
  '''

  DefaultStyle = '''
  .card {
  font-family: 'DejaVu Sans Mono';
  text-align: left;
  color: white;
  background-color: rgba(42, 129, 151,1);
  text-shadow: 0px 4px 3px rgba(0,0,0,0.4),
              0px 8px 13px rgba(0,0,0,0.1),
              0px 18px 23px rgba(0,0,0,0.1);
  }

  .front {
    font-size: 14px;
  }

  .back {
    font-size: 14px;
  }

  th {
      height:200px
      width:auto;/*maintain aspect ratio*/
      max-width:500px;
  }

  @font-face { font-family: DejaVu Sans Mono; src: url('_DejaVuSansMono.ttf'); }
  '''
  
  def __init__(self, name: str, fields: List, front_html=DefaultFrontTemplate, back_html=DefaultBackTemplate, css= DefaultStyle):
    hash_object = hashlib.sha1(name.encode('utf-8'))
    hex_dig = int(hash_object.hexdigest(), 16) % (10 ** 10)
    
    templates = [{
        'name': 'Card 1',
        'qfmt': front_html,
        'afmt': back_html,
      }]
    super(MyModel, self).__init__(model_id=hex_dig, name=name, fields=fields, templates=templates, css=css)


class NodeToAnki:
  @staticmethod
  def unicodeToHTMLEntities(text: str) -> str:
    """
    Replace space and nextline character to HTML entity
    """
    return text.replace(os.linesep, '<br>').replace('\t', '&ensp;&ensp;').replace(' ', '&ensp;')
  
  @staticmethod
  def convertParagraphToHtml(para: Paragraph, hideBold: bool) -> str:
    """
    Convert Node text to HTML format, where Anki can read.

    :para:: python-docx Paragraph. Like a sentence
    :hideBold:: If true, all the bold/italic text will all turn into _
    """
    result = ''
    if not DocxToNode.isNormalParagraph(para) or DocxToNode.isEmptyParagraph(para):
      return ''
    for r in para.runs:
      if r.bold:
        result += '<b>' + ('_' * len(r.text) if hideBold else r.text) + '</b>'
      elif r.italic:
        result += '<i>' + ('_' * len(r.text) if hideBold else r.text) + '</i>'
      else:
        result += r.text
    return result

  @staticmethod
  def getAnkiNoteFields(node: Node) -> Tuple[str, str, str]:
    """
    Convert Node object into Anki note fields, for Anki note card
    """
    question, answer = '', ''
    tableOfContent = NodeToAnki.unicodeToHTMLEntities(node.getBranchStr())
    # So Document can save a line into multiple context, this is to add them all. 
    # For example: "This is <bold>one</bold> line" has 3 contexts
    for p in node.context:
      question += NodeToAnki.convertParagraphToHtml(p, True) + '<br>'
      answer += NodeToAnki.convertParagraphToHtml(p, False) + '<br>'
    return (question, answer, tableOfContent)
  
  @classmethod
  def createAnkiNotes(cls, root: Node, model: genanki.Model, package: OpcPackage) -> List[genanki.Note]:
    """
    From root Node, convert all nodes into Anki note cards
    """
    if not root: return []
    allCodeBlocks = DocxToNode.getAllTables(package)
    allNotes = cls._createAnkiNotesRecursive(root, 0, [], allCodeBlocks)
    results = []
    for n in allNotes:
      newNotes = genanki.Note(model=model, fields=[n.question, n.answer, n.media, n.tableOfContent], tags=n.tags)
      results += [newNotes]
    return results

  @classmethod
  def _createAnkiNotesRecursive(cls, n: Node, curLevel: int, allPhotosFromParent: List[PhotoNode], allCodeBlocks: Dict[str, Table]) -> List[MyNote]:
    """
    Helper function, to create Anki note cards, from Node object, recursively

    Parameters
    ----------
    :n:: the current node going to be handled
    :curLevel:: keep track of what level this node current at in this tree. root=0, root.children=1...
    :allPhotosFromParent:: some photos are meant to shown for all node in this level

    @return list of all MyNote object, from this node, and all children, grand-children...

    This is basically a Breadth-first search algorithm
    """
    result = []
    # Check if it is one-off photo. It is one line of note that has a photo. it is identify with '®®0'
    if isinstance(n, PhotoNode) and n.showOnChildrenLevel == 0:
      question, answer, tableOfContent = NodeToAnki.getAnkiNoteFields(n)
      media = '<img src="' + n.imageName + '"><br>'
      tags = n.getAllParent()
      result += [MyNote(question, answer, media, tableOfContent, tags)]
      return result
    
    # Check if it is a code block, which is identify with ¨¨, follow by a 1x1 table. 
    # code is inside the table
    if len(n.context) > 0 and '¨¨' in n.context[0].text:
      question = NodeToAnki.unicodeToHTMLEntities(allCodeBlocks[n.context[0].text])
      answer = NodeToAnki.unicodeToHTMLEntities(allCodeBlocks[n.context[0].text])
      tableOfContent = NodeToAnki.unicodeToHTMLEntities(n.getBranchStr())
      tags = n.getAllParent()
      result += [MyNote(question, answer, '', tableOfContent, tags)]
      return result

    # Check if there is a multi-line single Node, which is identify using '©©' and
    # Check if node is text paragraph
    if len(n.context) > 0 and DocxToNode.isNormalParagraph(n.context[0]) \
      and '®®' not in n.context[0].text and isinstance(n.context, List):
      question, answer, tableOfContent = NodeToAnki.getAnkiNoteFields(n)
      tags = n.getAllParent()
      media = ''
      # For all photos that Parent and grandparent and up contains, add into Anki note as well
      # , because it may have info that need for that line/note
      for pic in allPhotosFromParent:
        # Right after ®®, there is an integer, ®®1 means show pic on lines/notes that is same level of this tree
        # , ®®2 shows on this level and children nodes.
        if pic.level - curLevel < pic.showOnChildrenLevel:
          media += '<img src="' + pic.imageName + '"><br>'

      # create note
      result += [MyNote(question, answer, media, tableOfContent, tags)]

    new_all_photos_children = []
    # Append all photos of next children level here, so children level recursive call on each text node/note/line 
    # has all records of pic on that level.
    for c in n.children:
      if isinstance(c, PhotoNode) and c.showOnChildrenLevel > 0:
        new_all_photos_children.append(c)

    # recursive call each children, also appends this level pics, just in case they need to show on gran-children level
    for c in n.children:
      result += cls._createAnkiNotesRecursive( c, curLevel + 1, allPhotosFromParent + new_all_photos_children, allCodeBlocks)

    return result

    

class MyNote:
  """
  A Data structure for Anki Note cards
  """
  def __init__(self, question, answer, media, tableOfContent, tags):
    self.question = question
    self.answer = answer
    self.media = media
    self.tableOfContent = tableOfContent
    self.tags = tags


if __name__ == "__main__":
  docxToAnkiNotes("Microsoft Word Documents to Anki converter demo")
