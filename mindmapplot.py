from __future__ import annotations
from typing import List

class Node():
  def __init__(self, name: str, level=0):
    self.name = name
    self.y = 0
    self.level = level
    self.children = []
  
  def add(self, new_node: Node):
    new_node.level = self.level+1
    self.children.append(new_node)
  
  def __repr__(self):
    results = '-'*self.level + ' ' + self.name + ' y: ' + str(self.y)
    #for c in self.children:
    #  results += repr(c)
    return results


root = Node('root', 0)
for i in range(1,5,1):
  ni = Node(str(i), 1)
  for j in range(1,4,1):
    nj = Node(str(i)+' '+str(j), 2)
    for k in range(1,3,1):
      nk = Node(str(i)+' '+str(j)+' '+str(k), 3)
      nj.add(nk)
    ni.add(nj)
  root.add(ni)


def _get_list_of_nodes(n: Node, list_of_nodes: List[Node]):
  lst = [n]
  for c in n.children:
    lst += _get_list_of_nodes(c, [])
  return list_of_nodes + lst


def calc_y(list_of_nodes: List[Node]):
  # find max level
  maxLevel = 0
  for n in list_of_nodes:
    if n.level > maxLevel:
      maxLevel = n.level
  
  # update the most bottom level of nodes first
  maxLevelNodes = []
  for n in list_of_nodes:
    if n.level == maxLevel:
      maxLevelNodes += [n]
  
  for i in range(len(maxLevelNodes)):
    maxLevelNodes[i].y = 0 if i <= 0 else maxLevelNodes[i-1].y + 1
  
  # from max level to root
  for i in range(maxLevel-1,-1,-1):
    # for each node from list_of_nodes
    for j in range(len(list_of_nodes)):
      # check if current level
      if list_of_nodes[j].level == i:
        list_of_nodes[j].y = list_of_nodes[j].children[0].y



list_of_nodes = _get_list_of_nodes(root, [])
calc_y(list_of_nodes)
