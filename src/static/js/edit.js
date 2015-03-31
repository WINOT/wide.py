// Central point of interractions
ideApplication = null;
tree = null;
chatApplication = null;

// Requests
RETRY_CONNECT_TIMEOUT = 2000; // ms

// Initialize content when ready
$(document).ready(init);
$(window).on("beforeunload", terminate);

function init() {

  // Application Chat
  chatApplication = new AppChat("chat-display", "chat-user-text-input", "chat-user-text-btn");

  // Application IDE
  ideApplication = new AppIDE('editorLastVersion', 'editorDisplay');
}

function terminate(){
  if(chatApplication)
    chatApplication.close();
  if(ideApplication)
    ideApplication.close();
}

// Menu -> Project -> Export
function menuProjectExport(){
  ideApplication.export("/");
}

// Menu -> Execution -> Run
function menuProjectRun(){
  var args = $("#exec-args-input").val(); // Get args
  $("#exec-args-input").val("");          // Clear
  $('#exec-args-window').modal('hide');   // Close modal
  ideApplication.runCurrentFile(args);
}

// TEST_ONLY
function test_f(){
  var chtml = $('#mydiv').html();
  var ctext = $('#mydiv').text();
  alert(chtml);
  alert(ctext);
}

function addNewTextAt(){
  var content = $('#addText').val();
  var at = parseInt($('#addAt').val());
  var modA = createAddModif(content, at);
  ideApplication.notifySoft(createModifGroup([modA], "fileName", 0));
}

function removeTextAt() {
  var count = parseInt($('#rmCountText').val());
  var at = parseInt($('#rmAt').val());
  var modA = createRemoveModif(count, at);
  ideApplication.notifySoft(createModifGroup([modA], "fileName", 0));
}

function test_ajax() {
  var modObject = createModif("abc", 0);
  var modifObject = createModifGroup([modObject], "fileName", 0);
  ideApplication._requestHandler.post("save", modifObject, function(){
    console.log("Success reveived comm");
    ideApplication._changeMemory.clear();
  });
}

function test_AddNode() {
  var nodeName = $('#textNode').val();
  tree.addNode(nodeName);
}

function test_RemoveNode() {
  var nodeName = $('#textNode').val();
  tree.removeNode(nodeName);
}

function test_ManyAddNode() {
  tree.addNode('file-toto');
  tree.addNode('dir-toto/');

  tree.addNode('/d/');
  tree.addNode('d/sub-toto-file');
  tree.addNode('d/sub-toto-dir/');
}
