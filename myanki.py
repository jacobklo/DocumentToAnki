from __future__ import annotations
import genanki
import hashlib, os
from pathlib import Path
from typing import List, Tuple

from docx.package import Package
from docx.text.paragraph import Paragraph

from docx2tree import Node, PhotoNode, DocxToNode
from docx2tree import convert_paragraphs_to_tree


def docx_to_anki_notes(filename: str):
  f = open(filename+'.docx', 'rb')
  pp = Package.open(f)
  f.close()

  root = convert_paragraphs_to_tree(pp)

  my_model = MyModel(filename+' Model', fields=[{'name': 'Question'}, {'name': 'Answer'}, {
      'name': 'Media'}, {'name': 'TableOfContent'}], front_html=QUESTION, back_html=ANSWER, css=STYLE)

  notes = createAnkiNotes(root, my_model, filename)

  my_deck = genanki.Deck(deck_id=abs(hash(filename)) % (10 ** 10), name=filename)

  for n in notes:
    my_deck.add_note(n)

  img_path = Path(r'image').glob('**/*')
  images = ['image/'+x.name for x in img_path if x.is_file()]

  anki_output = genanki.Package(my_deck)
  anki_output.media_files = images
  anki_output.write_to_file(filename+'.apkg')


class MyModel(genanki.Model):

  def __init__(self, name: str, fields: List, front_html: str, back_html: str, css: str):
    hash_object = hashlib.sha1(name.encode('utf-8'))
    hex_dig = int(hash_object.hexdigest(), 16) % (10 ** 10)
    
    templates = [
      {
        'name': 'Card 1',
        'qfmt': front_html,
        'afmt': back_html,
      }
    ]
    super(MyModel, self).__init__(model_id=hex_dig, name=name, fields=fields, templates=templates, css=css)



def createAnkiNotes(root: Node, model: genanki.Model, filename: str) -> List[genanki.Note]:
  if not root: return []
  filename = filename.lower().replace(' ','_')
  allNotes = _create_node_to_notes(root, 0, [])
  results = []
  for n in allNotes:
    newNotes = genanki.Note(model=model, fields=[n.question, n.answer, n.media, n.tableOfContent], tags=n.tags+[filename])
    results += [newNotes]
  return results


def _create_node_to_notes(n: Node, curLevel: int, allPhotosFromParent: List[PhotoNode]) -> List[MyNote]:
  result = []
  # Check if it is one-off photo. It is one line of note that has a photo. it is identify with '®®0'
  if isinstance(n, PhotoNode) and n.showOnChildrenLevel == 0:
    question, answer, tableOfContent = NodeToAnki.getAnkiNoteFields(n)
    media = '<img src="' + n.imageName + '"><br>'
    tags = n.get_tags()
    result += [MyNote(question, answer, media, tableOfContent, tags)]
    return result

  # Check if there is a multi-line single Node, which is identify using '©©' and
  # Check if node is text paragraph
  if len(n.context) > 0 and DocxToNode.isNormalParagraph(n.context[0]) and '®®' not in n.context[0].text and isinstance(n.context, List):
    question, answer, tableOfContent = NodeToAnki.getAnkiNoteFields(n)
    tags = n.get_tags()
    media = ''
    # For all photos that Parent and grandparent and up contains, add into Anki note as well, because it may have info that need for that line/note
    for pic in allPhotosFromParent:
      # Right after ®®, there is an integer, ®®1 means show pic on lines/notes that is same level of this tree, ®®2 shows on this level and children nodes.
      if pic.level - curLevel < pic.showOnChildrenLevel:
        media += '<img src="' + pic.imageName + '"><br>'

    # create note
    result += [MyNote(question, answer, media, tableOfContent, tags)]

  new_all_photos_children = []
  # Append all photos of next children level here, so children level recursive call on each text node/note/line has all records of pic on that level.
  for c in n.children:
    if isinstance(c, PhotoNode) and c.showOnChildrenLevel > 0:
      new_all_photos_children.append(c)

  # recursive call each children, also appends this level pics, just in case they need to show on gran-children level
  for c in n.children:
    result += _create_node_to_notes( c, curLevel + 1, allPhotosFromParent + new_all_photos_children)

  return result



class NodeToAnki:
  @staticmethod
  def unicodeToHTMLEntities(text: str) -> str:
    """
    Replace space and nextline character to HTML entity
    """
    return text.replace(os.linesep, '<br>').replace('\t', '&ensp;')
  
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
  def getAnkiNoteFields(node: Node):
    question, answer = '', ''
    tableOfContent = NodeToAnki.unicodeToHTMLEntities(node.getBranchStr())
    # So Document can save a line into multiple context, this is to add them all. For example: "This is <bold>one</bold> line" has 3 contexts
    for p in node.context:
      question += NodeToAnki.convertParagraphToHtml(p, True) + '<br>'
      answer += NodeToAnki.convertParagraphToHtml(p, False) + '<br>'
    return (question, answer, tableOfContent)


class MyNote:
  def __init__(self, question, answer, media, tableOfContent, tags):
    self.question = question
    self.answer = answer
    self.media = media
    self.tableOfContent = tableOfContent
    self.tags = tags



QUESTION = '''
<div class="front">{{Path}}<br><br>{{Question}}</div>
'''


ANSWER = '''
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


STYLE = '''
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


if __name__ == "__main__":
  docx_to_anki_notes("Microsoft Word Documents to Anki converter demo")
