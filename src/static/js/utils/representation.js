// Modification types
CHANGE_RM_TYPE = -1;
CHANGE_ADD_TYPE = 1;
// Opcode for response type on WS
OPCODE_IDE_TREE = "tree";
OPCODE_IDE_SAVE = "save";
OPCODE_IDE_DUMP = "dump";
OPCODE_IDE_OPEN = "open";
OPCODE_IDE_CLOSE = "close";
OPCODE_EXEC_OUTPUT = "execoutput";
OPCODE_EXEC_END = "execended";

// used for /ide/save
function createModifGroup(changes, file, vers) { return { file: file, vers: vers, changes: changes}; }
function createAddModif(content, pos) { return { content: content, pos: pos, type: CHANGE_ADD_TYPE}; }
function createRemoveModif(count, pos) { return { count: count, pos: pos, type: CHANGE_RM_TYPE}; }

// used for /ide/open
function createOpen(filename) { return { file: filename}; }
// used for /ide/close
function createClose(filename) { return { file: filename}; }
// used for /ide/dump
function createDump(filename) { return { filename: filename}; }
// used for /ide/export
function createExport(directory) { return { path: directory}; }

// used for /chat/send
function createChatMessage(msg) { return { message: msg}; }

// used for /ide/execstart
function createProcessInit(filename, arguments) { return {file: filename, args: arguments}; }
// used for /ide/execinput
function createProcessInput(arguments) { return {data: arguments}; }
// used for /ide/execkill
function createProcessTermination() { return {}; }


function ObjectAddChange(pos, content, author){
  this._pos = pos;
  this._content = content;
  this._author = author; // From server only
}
ObjectAddChange.prototype.size = function(){
  return this._content.length;
};
ObjectAddChange.prototype.applyOnText = function(text){
  return text.insert(this._content, this._pos);
};
ObjectAddChange.prototype.applyOnPos = function(pos){
  if(!this._author){
    pos += (this._pos <= pos ? this.size() : 0);
  }
  return pos;
};
ObjectAddChange.prototype.updatePos = function(modObject){
  if(!this._author){
    this._pos = modObject.applyOnPos(this._pos);
  }
};
ObjectAddChange.prototype.serialize = function(){
  return createAddModif(this._content, this._pos);
};

function ObjectRemoveChange(pos, count, author){
  this._pos = pos;
  this._count = count;
  this._author = author; // From server only
}
ObjectRemoveChange.prototype.size = function(){
  return this._count;
};
ObjectRemoveChange.prototype.applyOnText = function(text){
  return text.cutFrom(this._pos, this._count);
};
ObjectRemoveChange.prototype.applyOnPos = function(pos){
  if(!this._author){
    pos -= (this._pos <= pos ? this.size() : 0);
  }
  return pos;
};
ObjectRemoveChange.prototype.updatePos = function(modObject){
  if(!this._author){
    this._pos = modObject.applyOnPos(this._pos);
  }
};
ObjectRemoveChange.prototype.serialize = function(){
  return createRemoveModif(this._count, this._pos);
};


function ObjectChangeFactory(changeObjJSON){
  return changeObjJSON.type == CHANGE_ADD_TYPE ?
    new ObjectAddChange(changeObjJSON.pos, changeObjJSON.content,
                        changeObjJSON.author):
    new ObjectRemoveChange(changeObjJSON.pos, changeObjJSON.count,
                           changeObjJSON.author);
}

function serializeObjectChangeList(changesList){
  var serialized = [];
  for(var i = 0; i < changesList.length; ++i){
    serialized.push(changesList[i].serialize());
  }
  return serialized;
}
