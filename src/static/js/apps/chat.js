/* Class to encapsulate all communication and view of the 
instant chat of the project */
function AppChat(displayId, userInputId, userSendBtnId) {
  this.DEFAULT_LOCAL_USERNAME = 'Me';
  this.DEFAULT_MEMBER_USERNAME = 'Member';

  // Declare to avoid alway combining strings
  this.URL_CONNECT = window.location.origin + '/chat/connect';
  this.URL_DISCONNECT = window.location.origin + '/chat/disconnect';
  this.URL_SEND = window.location.origin + '/chat/send';

  this._logDisplayNode = $("#"+displayId);
  this._userInputNode = $("#"+userInputId);
  this._userSendBtnNode = $("#"+userSendBtnId);

  // Bind events
  var obj = this; // For closure
  this._userInputNode.keyup(function (e) { if (e.which == 13)  obj._send(); });
  this._userSendBtnNode.click(function(e){ obj._send(); });

  var receiveFn = function(opCode, jsonObj){
    // Check if opCode means new member to chat

    // opCode is chat message
    obj.addProjectMemberMessage(jsonObj.message, jsonObj.author, jsonObj.timestamp);
  };

  var onopen = function(){ obj._rqh.put(obj.URL_CONNECT, {}); };
  var onclose = function(){ obj._rqh.put(obj.URL_DISCONNECT, {}); };
  this._rqh = new RequestHandler('chat', receiveFn, onopen, onclose);
}
AppChat.prototype.close = function(){
  this._rqh.close();
};
AppChat.prototype._send = function(){
  var msg = this._userInputNode.val().trim();
  if(msg) {
    this._rqh.put(this.URL_SEND, createChatMessage(msg), function(){}, function(e){
      alert(e); 
    });
    this._userInputNode.val(''); // Clear
  }
};
AppChat.prototype.addUserMessage = function(text, name, time){
  this._logDisplayNode.append(
    $('<li>').attr("class", "chat-message-element clearfix").append(
      $('<div>').attr("class", "chat-message-header").append(
        $('<strong>').attr("class", "primary-font").append(
          htmlEncode(name)
        )
      ).append(
        $('<small>').attr("class", "text-muted pull-right").append(
          $('<span>').attr("class", "glyphicon glyphicon-time")
        ).append(
          htmlEncode(time)
        )
      )
    ).append(
      $('<div>').attr("class", "chat-message-body").append(
        htmlEncode(text)
      )
    )
  );

  // Make sure to see last message
  this._lowerScrollView();
};

AppChat.prototype.addProjectMemberMessage = function(text, name, time){
  this._logDisplayNode.append(
    $('<li>').attr("class", "chat-message-element clearfix").append(
      $('<div>').attr("class", "chat-message-header").append(
        $('<small>').attr("class", "text-muted").append(
          $('<span>').attr("class", "glyphicon glyphicon-time")
        ).append(
          htmlEncode(time)
        )
      ).append(
        $('<strong>').attr("class", "primary-font pull-right").append(
          htmlEncode(name)
        )
      )
    ).append(
      $('<div>').attr("class", "chat-message-body").append(
        htmlEncode(text)
      )
    )
  );

  // Make sure to see last message
  this._lowerScrollView();
};
AppChat.prototype._lowerScrollView = function() {
  var parent = this._logDisplayNode.parent();
  parent.scrollTop(parent[0].scrollHeight);
};
