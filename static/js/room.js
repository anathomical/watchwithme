_xSocket = {
	socket : "",
	chat_window : "",
	open : function(socket_uri) {
		_xSocket.chat_window = document.getElementById('chat-window');
		_xSocket.socket = new WebSocket(socket_uri);
		_xSocket.socket.onopen = function() { 
			console.log("Opened socket.  Sending auth info.");
			_xSocket.socket.send({
				'type': 'LOGIN',
				'email': $.cookie('user_email'),
				'token', $.cookie('user_token'),
			});
		};
		_xSocket.socket.onmessage = _xSocket.handle_message;
		_xSocket.socket.onclose = function() { console.log("Closed socket."); };
	},
	handle_message : function(evt) {
		var data = json.parse(evt.data);
		if (data.type == 'CHAT') {
			_xSocket.show_message(data.user, 'TIMESTAMP', data.message);
		}
	},
	show_message : function(user, timestamp, message) {
		var display_message = user + ':' + message;
		_xSocket.chat_window.innerHTML += '<p>'+display_message+'</p>';
		_xSocket.chat_window.scrollTop = _xSocket.chat_window.scrollHeight;
	},
}
_xVideo = {
	element : "",
	init : function() {
		_xVideo.video = $('#video-player');
		_xVideo.video.on('play',  function(evt) {
			console.log('playing');
		});
		_xVideo.video.on('pause', function(evt) {
			console.log('pausing');
		});
	}
}
$(document).ready( function() {
	_xSocket.open("ws://50.19.239.129:9000/room/198abde28aed/socket");
	$("#socket_form").on('submit', function() {
		var input_element = $('#socket_input');
		_xSocket.socket.send({
			'type': 'CHAT',
			'message': input_element.val()),
		});
		input_element.val('');
		return false;
	});
	$('#close_socket').on('click', function() {
		_xSocket.socket.close();
	});
	_xVideo.init();
});
