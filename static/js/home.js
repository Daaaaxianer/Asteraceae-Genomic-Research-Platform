function treedes() {
  alert('①Same assembly, different annotations\n'+
          '②Same variety, different assemblies\n③Same species, different varieties\n'+
          '④Same genus, different species\n'+
          '⑤Same tribe, different genuses\n'+
          '⑥Outgroup');
}


/*display*/
function display(id){
  var traget=document.getElementById(id);
  if(traget.style.display=="none"){
    traget.style.display="";
  }else{
    traget.style.display="none";
  }
  
  if(document.getElementById('show_tree_button').value=="Show genome table and tree"){
    document.getElementById('show_tree_button').value = "Hide genome table and tree";
    document.getElementById('show_tree_button').innerHTML = "Hide genome table and tree";
  }else{
    document.getElementById('show_tree_button').value = "Show genome table and tree";
    document.getElementById('show_tree_button').innerHTML = "Show genome table and tree";
  }
}

