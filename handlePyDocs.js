
var script = document.createElement('script');
script.src = 'seedrandom.js';
script.async = false;
document.head.appendChild(script);
document.head.removeChild(script);



function hideSomeText(node, prob, random_gen_func) { 
  
  node.childNodes.forEach(n => {
    
    if (n.nodeType === Node.TEXT_NODE) {
      let words = n.textContent.split(/\s+/);
      for (let i = 0; i < words.length; i++) {
        if (random_gen_func() > prob) {
          if (words[i].length > 0) {
            words[i] = words[i][0] + '_'.repeat(words[i].length - 1);
          }
        }
      }
      n.textContent = words.join(' ');
    } 
    
    else if (n.nodeType === Node.ELEMENT_NODE) {
      hideSomeText(n, prob, random_gen_func)
    }
  });

}


function update(prob) {
  let random_gen_func = new Math.seedrandom('hello.');

  let div = document.querySelector('.question');
  let clone2 = document.querySelector('.question-clone');
  
  div.innerHTML = clone2.innerHTML;
  hideSomeText(div, prob, random_gen_func);
  
  div.style.display = 'none';
  div.style.display = 'block';

  document.getElementById('sidebar-value').textContent = prob;
}

document.getElementById('prob-sidebar').addEventListener('input', function(event) {
  update(event.target.value);
});
