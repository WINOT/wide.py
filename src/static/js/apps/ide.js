DEFAULT_PUSH_INTERVAL = 2000; // ms

/* Central class that will interact will all other classes. */
function AppIDE(lastVersionZoneId, displayZoneId, pushInterval) {
  pushInterval = pushInterval || DEFAULT_PUSH_INTERVAL;

  // For closure
  var obj = this; 

  // Initialise Tree root.
  var tree = new ProjectTreeView(function(filepath){
    obj.showFile(filepath); // file was clicked
  });
  tree.initRoot("tree");

  // Handle ways of sending and receiving data from/to server
  var onopen = function(){ obj._ideState.init(); };
  var onclose = function(){ /* For future usage */ };
  var onreceive = function(opCode, jsonObj) {
    // hack
    if(opCode.startsWith("exec")){
      obj.execConsole.handleReceive(opCode, jsonObj);
    }
    else {
      obj.handleReceive(opCode, jsonObj);
    }
  };
  var requestHandler = new RequestHandler('ide', onreceive, onopen, onclose);

  // Execution console
  this.execConsole = new ProjectConsoleView(requestHandler,
                                           "console-window",
                                           "console-display",
                                           "console-input",
                                           "console-text-btn",
                                           "console-close-btn");

  // States
  // Create all to avoid recreation
  this._noFileState = new IdeNoFileState(this, requestHandler, tree);
  this._fileChangeState = new IdeFileChangeState(this, requestHandler, tree);
  this._editState = new IdeEditState(this, requestHandler, tree, pushInterval, 
    $("#" + lastVersionZoneId),
    $("#" + displayZoneId));
  
  // Initial state
  this._ideState = new IdeInitState(this, requestHandler, tree);

  // Debug
  $("#stateHelper").text("Waiting project tree from server");
};
AppIDE.prototype.close = function() {
  this._ideState.close();
};
AppIDE.prototype.showFile = function(filepath) {
  this._ideState.showFile(filepath);
};
AppIDE.prototype.handleReceive = function(opCode, jsonObj) {
  this._ideState.handleReceive(opCode, jsonObj);
};
AppIDE.prototype.handleInput = function() {
  this._ideState.handleInput();
};

// State transitions
AppIDE.prototype.waitForFileSelected = function() {
  // Debug
  $("#stateHelper").text("Waiting for a file to be selected");

  console.log("INFO", "IDE : Switch to NoFileState");
  this._ideState.leave();
  this._noFileState.init();
  this._ideState = this._noFileState;
};
AppIDE.prototype.waitForTargetFile = function(targetFilepath) {
  // Debug
  $("#stateHelper").text("Waiting for file '" +targetFilepath+ "' from server");

  console.log("INFO", "IDE : Switch to ChangeFileState ('" +targetFilepath+"')");
  this._ideState.leave();
  this._fileChangeState.init(targetFilepath);
  this._ideState = this._fileChangeState;
};
AppIDE.prototype.switchToEditFileState = function(targetFilepath, dumpObj, changeObjs) {
  // Debug
  $("#stateHelper").text("Editing file '" +targetFilepath+ "'");

  console.log("INFO", "IDE : Switch to EditFileState ('" +targetFilepath+"')");
  this._ideState.leave();
  this._editState.init(targetFilepath, dumpObj, changeObjs);
  this._ideState = this._editState;
};

AppIDE.prototype.export = function(path){
  this._ideState._rqh.download('export', createExport(path));
};

AppIDE.prototype.runCurrentFile = function(args){
  var currentFile = this._ideState.getCurrentFile();
  if(currentFile) {
    this.execConsole.start(currentFile, args);
  }
  else {
    var msg = "There is no file selected, unable to execute";
    console.log("WARNING", msg);
  }
};


/*  The initial state of the ide 
    No state should go back to this one */
function IdeInitState(ide, rqh, tree){
  this._ide = ide;
  this._rqh = rqh;
  this._tree = tree;

  this._tree_success = function() { console.log("Tree request received successfully"); };
  this._tree_error = function() { console.log("Tree request failed"); };
}
IdeInitState.prototype.init = function(){
  // Request project tree and load TreeView content
  // Display a msg for user to wait ??
  this._rqh.get("tree", {}, this._tree_success, this._tree_error);
};
IdeInitState.prototype.leave = function(){};
IdeInitState.prototype.close = function(){ this._rqh.close(); };
IdeInitState.prototype.showFile = function(targetFilepath){};
IdeInitState.prototype.handleReceive = function(opCode, jsonObj) {
  if(opCode == OPCODE_IDE_TREE) {
    for(var i = 0; i < jsonObj.nodes.length; ++i){
      this._tree.addNode(jsonObj.nodes[i].node, jsonObj.nodes[i].isDir);
    }
    // Change state
    this._ide.waitForFileSelected();
  }
  else {
    console.log("WARNING", "IdeInitState received opCode '" + opCode + "'");
  }
};
IdeInitState.prototype.handleInput = function(){};
IdeInitState.prototype.getCurrentFile = function(){ return null; };


/* There is no active page to edit */
function IdeNoFileState(ide, rqh, tree){
  this._ide = ide;
  this._rqh = rqh;
  this._tree = tree;
}
IdeNoFileState.prototype.init = function(){};
IdeNoFileState.prototype.leave = function(){};
IdeNoFileState.prototype.close = function(){ this._rqh.close(); };
IdeNoFileState.prototype.showFile = function(targetFilepath){
  this._ide.waitForTargetFile(targetFilepath);
};
IdeNoFileState.prototype.handleReceive = function(opCode, jsonObj) {
  var msg = "IdeNoFileState only expects file clicks.";
  msg += "Received opcode '" + opCode + "' with data :";
  console.log("WARNING", msg, jsonObj);
};
IdeNoFileState.prototype.handleInput = function(){};
IdeNoFileState.prototype.getCurrentFile = function(){ return null; };


/* User requested to change file */
function IdeFileChangeState(ide, rqh, tree){
  this._ide = ide;
  this._rqh = rqh;
  this._tree = tree;

  this._targetFilepath = undefined;
  this._changesBuffer = undefined;

  this._open_success = function() { console.log("Open request received successfully"); };
  this._open_error = function() { console.log("Open request failed"); };
}
IdeFileChangeState.prototype.init = function(targetFilepath){
  this._targetFilepath = targetFilepath;
  this._changesBuffer = [];
  // Do request
  this._rqh.post("open", createOpen(targetFilepath), this._open_success, this._open_error);
};
IdeFileChangeState.prototype.leave = function(){};
IdeFileChangeState.prototype.close = function(){ this._rqh.close(); };
IdeFileChangeState.prototype.showFile = function(targetFilepath){
  var msg = "Already in transfer for '" + this._targetFilepath + "'. ";
  msg += "Cannot transfer to '" + targetFilepath + "'";
  console.log("WARNING", msg);
};
IdeFileChangeState.prototype.handleReceive = function(opCode, jsonObj) {
  if(opCode == OPCODE_IDE_SAVE) {
    // Changes can arrive early since notifications can be done
    // right after being registered... Buffer for a delayed apply
    if(jsonObj.file == this._targetFilepath) {
      this._changesBuffer.push(jsonObj);
    }
    else {
      var msg = "IdeFileChangeState discarding changes for '" + jsonObj.file + "'";
      console.log(msg);
    }
  }
  else if(opCode == OPCODE_IDE_DUMP) {
    if(jsonObj.file == this._targetFilepath) {
      // Received waiting change
      this._ide.switchToEditFileState(this._targetFilepath, jsonObj, this._changesBuffer);
    }
    else {
      var msg = "IdeFileChangeState discarding dump for '" + jsonObj.file + "'";
      console.log(msg);
    }
  }
  else {
    var msg = "IdeFileChangeState only expects /save and /dump.";
    msg += "Received opcode '" + opCode + "' with data :";
    console.log("WARNING", msg, jsonObj);
  }
};
IdeFileChangeState.prototype.handleInput = function(){};
IdeFileChangeState.prototype.getCurrentFile = function(){ return null; };


/* There is an active page to edit */
function IdeEditState(ide, rqh, tree, pushInterval, nodeLastVersion, nodeDisplay){
  this._ide = ide;
  this._rqh = rqh;
  this._tree = tree;

  // For closure
  var obj = this;

  // Benchmarks
  this._debugStopWatchLap = new StopWatch();
  this._debugStopWatchLap.hide();

  // Create classes
  this._changeMemory = new LocalChanges();
  this._lastVersion = new LastVersionZone(nodeLastVersion);
  this._displayZone = new DisplayZone(nodeDisplay, function(){
    obj.handleInput();
  });

  // Send frequency 
  this._pushInterval = pushInterval;
  this._pushIntervalHandle = null;

  // Diff lib to compare two texts
  this._difftool = new diff_match_patch();

  // Currently opened file
  this._currentFile = "";
  this._currentFileRevision = 0;

  // Function to push changes to server
  var obj = this;
  this._pushChanges = function() {
    // try push
    var changes = obj._changeMemory.get();
    if(changes.length == 0) 
      return;

    // Clear changes to avoid resending
    obj._changeMemory.clear();

    // Save and send, delete sent changes on success
    var modifObject = createModifGroup(changes, obj._currentFile, obj._currentFileRevision);
    //console.log("Current bundle id is ", currentBundleID, modifObject);
    obj._debugStopWatchLap.start(); // debug
    obj._rqh.put("save", modifObject, function(){
      // Will I delete new input ??
    }, function(){}, false);
  };
}
IdeEditState.prototype.init = function(targetFilepath, dumpObj, changeObjs){
  // Initialize base text
  this._currentFile = targetFilepath;
  this._handleReceiveDump(dumpObj);
  // Update base text with buffered changes
  for(var i = 0; i < changeObjs.length; ++i) {
    this._handleReceiveSave(changeObjs[i]);
  }
  // Interval to send changes to server
  this._pushIntervalHandle = setInterval(this._pushChanges,
                                         this._pushInterval);

  // debug
  this._debugStopWatchLap.show();
};
IdeEditState.prototype.leave = function(){
  // Avoid sending other packages
  clearInterval(this._pushIntervalHandle);
  // Make sure no changes are left behind
  this._pushChanges();
  // Unregister to file ... call /close
  this._rqh.put("close", createClose(this._currentFile));

  // debug
  this._debugStopWatchLap.hide();
};
IdeEditState.prototype.close = function(){
  this._rqh.put("close", createClose(this._currentFile));
  this._rqh.close(); 
};
IdeEditState.prototype.handleReceive = function(opCode, jsonObj){
  this._debugStopWatchLap.stop();
  if(opCode == OPCODE_IDE_SAVE || opCode == 0) {
    // opCode is textEdit
    if(jsonObj.file == this._currentFile) {
      this._handleReceiveSave(jsonObj);
    }
    else {
      var msg = "IdeEditState received update for '" + jsonObj.file;
      msg += "' when current file is '" + this._currentFile + "'";
      console.log(msg);
    }
  }
  else if(opCode == OPCODE_IDE_DUMP) { 
    this._handleReceiveDump(jsonObj);
  }
  else {
    var msg = "IdeEditState only expects /save and /dump.";
    msg += "Received opcode '" + opCode + "' with data :";
    console.log("WARNING", msg, jsonObj);
  }
};
IdeEditState.prototype._handleReceiveDump = function(dumpObj){
  this._notifyForce(createAddModif(dumpObj.content, 0));
  this._currentFileRevision = dumpObj.vers;
};
IdeEditState.prototype._handleReceiveSave = function(saveObj){
  var modifications = [];
  for(var i = 0; i < saveObj.changes.length; ++i){
    modifications.push(ObjectChangeFactory(saveObj.changes[i]));
  }
  // Update
  this._notifySoft(modifications);
  this._currentFileRevision = saveObj.vers;
};
IdeEditState.prototype.handleInput = function(){
  // Get old value, compare and store new
  // $(this) corresponds to nodeDisplay
  var oldText = this._displayZone.getLastVersion();
  var newText = this._displayZone.getText();
  this._displayZone.saveVersion(newText);

  // https://code.google.com/p/google-diff-match-patch/wiki/API
  // A diff is a pair (type, text) where type is 1 for addition,
  // 0  for 'no-change' and -1 for substraction
  var diff = this._difftool.diff_main(oldText, newText);
  // Since this function is triggered after one change,
  // which corresponds to a maximum of two diff elements,
  // position needs to be computed over iteration
  // -- Add text : 1 diff add element
  // -- Remove text : 1 diff remove element
  // -- Highlight text and add text : 1 diff add element and 1 diff remove element 
  var at = 0;
  for(var i = 0; i < diff.length; ++i){
    switch(diff[i][0]) {
      case -1:
        this._changeMemory.removeChange(at, diff[i][1].length);
        break;
      case 1:
        this._changeMemory.addChange(at, diff[i][1]);
        // no break on purpose
      case 0:     
        at += diff[i][1].length;
        break;
    }
  }
};
IdeEditState.prototype.showFile = function(targetFilepath) {
  if(targetFilepath != this._currentFile){
    // Change file and state
    this._ide.waitForTargetFile(targetFilepath);
  }
  else {
    var msg = "File change request for '" + targetFilepath + "'.";
    msg += "Already active, not changing";
    console.log("INFO", msg);
  }
};
// Does not receive a group of modifications since
// every zone will be overriden. One delta is enough
IdeEditState.prototype._notifyForce = function(initialDelta) {
  this._lastVersion.put(initialDelta.content);
  this._changeMemory.clear();
  this._displayZone.forceUpdate([initialDelta.content, initialDelta.content.length]); 
};
IdeEditState.prototype._notifySoft = function(modifications) {
  this._changeMemory.update(modifications);
  this._lastVersion.update(modifications);

  var cursor_pos = this._displayZone.getCursorPos();
  this._displayZone.forceUpdate(this._combineText(cursor_pos));
};
IdeEditState.prototype._combineText = function(cursor_pos) {
  var base = this._lastVersion.get();
  var modifs = this._changeMemory.getUnserialized();
  for(var i = 0; i < modifs.length; ++i) {
    base = modifs[i].applyOnText(base);
    cursor_pos = modifs[i].applyOnPos(cursor_pos);
  }
  return [base, cursor_pos];
};
IdeEditState.prototype.getCurrentFile = function(){ return this._currentFile; };






// Debug
function StopWatch(){
  var obj = this; // Closure
  this._node = $("<div>");
  this._node_list = $("<ol>");
  this._node.append($("<h2>").append("StopWatchLap"))
            .append(this._node_list)
            .append($("<button>").click(function(){obj._node_list.empty();})
                                 .text("Clear"));
  $("#editorLastVersion").parent().append(this._node);
  this._startTime = [];
}
StopWatch.prototype.start = function(){
  this._startTime.push(performance.now());
  ++this._startedCount;
};
StopWatch.prototype.stop = function(){
  var end = performance.now();
  this._displayLaps(this._startTime, end);
  this._startTime = [];
};
StopWatch.prototype.hide = function(){
  this._node.hide();
};
StopWatch.prototype.show = function(){
  this._node.show();
};
StopWatch.prototype._displayLaps = function(startsArray, end){
  for(var i = 0; i < startsArray.length; ++i){
    var lapTimeMS = end - startsArray[i];
    this._node_list.append(
      $("<li>").append(
        lapTimeMS + "ms (start is : '"+startsArray[i]+"' and end is '"+end+"')"
      )
    );
  }
};
