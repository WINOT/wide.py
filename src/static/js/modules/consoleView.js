
function ProjectConsoleView(rqh, consoleWindow, displayId, inputId, sendBtnId, closeBtnId){
  this._rqh = rqh; 

  this._openTag = $("<a>").attr('href', "#"+consoleWindow)[0];
  this._closeTag = $("<a>").attr('href', "#"+closeBtnId)[0];

  this._displayNode = $("#"+displayId);
  this._inputNode = $("#"+inputId);
  this._sendBtnNode = $("#"+sendBtnId);

  // Bind events for text submit
  var obj = this; // For closure
  this._inputNode.keyup(function (e) { if (e.which == 13)  obj._send(); });
  this._sendBtnNode.click(function(e){ obj._send(); });

  // Bind event for closing console
  var onclose = function(){ obj._close(); };
  $("#"+closeBtnId).click(onclose);

  // Initial state
  this._hide();
}

ProjectConsoleView.prototype.handleReceive = function(opCode, jsonObj){
  if(opCode == OPCODE_EXEC_OUTPUT){
    this._handleReceiveExecOutput(jsonObj);
  }
  else if(opCode == OPCODE_EXEC_END) {
    this._handleReceiveExecEnded(jsonObj);
  }
  else {
    var msg = "ProjectConsoleView only expects /execended and /execoutput.";
    msg += "Received opcode '" + opCode + "' with data :";
    console.log("WARNING", msg, jsonObj);
  }
};

ProjectConsoleView.prototype._handleReceiveExecOutput = function(outputObj){
  this.addOutput(outputObj.output);
};
ProjectConsoleView.prototype._handleReceiveExecEnded = function(endedObj){
  alert("Program ended");
  this._displayNode.empty();
  this._hide();
};

ProjectConsoleView.prototype.addOutput = function(text){
  this._displayNode.append(
    $('<li>').attr("class", "output-element").append(
      htmlEncode(text)
    )
  );
  this._lowerScrollView();
};

ProjectConsoleView.prototype.start = function(filename, args){
  this._rqh.put("execstart", createProcessInit(filename, args));
  this._show();
};
ProjectConsoleView.prototype._close = function(){
  this._rqh.put("execkill", createProcessTermination());
  this._displayNode.empty();
  this._hide();
};
ProjectConsoleView.prototype._send = function(){
  var textInput = this._inputNode.val().trim();
  if(textInput) {
    this._inputNode.val(""); // Clear
    // To make sure the shortcut does not remove the enter stoke
    this.addOutput(textInput);
    this._rqh.put("execinput", createProcessInput(textInput+"\n"));
  }
};
ProjectConsoleView.prototype._lowerScrollView = function() {
  var parent = this._displayNode.parent();
  parent.scrollTop(parent[0].scrollHeight);
};
ProjectConsoleView.prototype._show = function(){ this._openTag.click(); };
ProjectConsoleView.prototype._hide = function(){ this._closeTag.click(); };