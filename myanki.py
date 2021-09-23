
import genanki
import hashlib
from typing import List
from docx2tree import Node, PhotoNode

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



def create_anki_notes_from_node(root: Node, model: genanki.Model, current_level = 0, all_photos_from_parent=[]) -> List[genanki.Note]:
  if not root: return []

  result = []

  if root.is_normal() and root.context and isinstance(root.context, List):
    question, answer = '', ''
    branch = root.get_branch_str()
    for p in root.context:
      question += root.convert_paragraph_to_html(p, True) + '<br>'
      answer += root.convert_paragraph_to_html(p, False) + '<br>'
      
    media = ''
    for pic in all_photos_from_parent:
      if pic.level - current_level < pic.showOnChildrenLevel:
        media += '<img src="' + pic.imageName + '"><br>'

    my_note = genanki.Note(
      model=model,
      fields=[question, answer, media, branch])
    result += [my_note]

  new_all_photos_children = []
  for c in root.children:
    if isinstance(c, PhotoNode):
      new_all_photos_children.append(c)

  for c in root.children:
    result += create_anki_notes_from_node(c, model, current_level + 1, all_photos_from_parent + new_all_photos_children)

  return result


QUESTION = '''
<div class="front">{{Question}}</div>
'''


ANSWER = '''
<div class="back">
<table style="width:100%">
  <tr>
    <th>{{Media}}</th>
  </tr>
  <tr>
    <th>{{Answer}}</th>
  </tr>
  <tr>
    <th>{{Path}}</th>
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

